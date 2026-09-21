"""Interactive terminal wizard for F5 BIG-IP and iHealth/MyF5 support operations.

Designed for SSH jump boxes and headless environments where no GUI is available.
Zero dependencies beyond Python standard library and f5functions.
"""

import getpass
import os
import sys
import time

try:
    from . import f5functions
except ImportError:
    import f5functions


def _prompt(prompt_text, default=None, secret=False):
    """Prompt the user for input with optional default and masking."""
    display = f"{prompt_text} [{default}]: " if default is not None else f"{prompt_text}: "
    if secret:
        val = getpass.getpass(display).strip()
    else:
        val = input(display).strip()
    return val if val else default


def run_auto_wizard():
    """Interactive wizard for One-Touch QKView Auto-Pilot."""
    print("\n=======================================================")
    print("   QKView Auto-Pilot: BIG-IP -> iHealth One-Touch")
    print("=======================================================")

    host = _prompt("BIG-IP Hostname or IP", default=os.getenv("BIGIP_HOST", ""))
    if not host:
        print("Error: BIG-IP host is required.")
        return

    username = _prompt("BIG-IP Username", default=os.getenv("BIGIP_USERNAME") or os.getenv("BIGIP_USER", "admin"))
    password = _prompt("BIG-IP Password", default=os.getenv("BIGIP_PASSWORD"), secret=True)
    if not password:
        print("Error: Password is required.")
        return

    ssl_verify_choice = _prompt("Verify BIG-IP SSL Certificate? (y/n)", default="n").lower()
    ssl_verify = ssl_verify_choice in ["y", "yes"]

    qkview_name = _prompt("QKView Filename", default=f"{host}_diag.qkview")
    case_num = _prompt("Support Case Number (optional, press Enter to skip)", default=None)
    desc = _prompt("iHealth Upload Description", default="Automated diagnostics via qkviewmgr")

    print("\nStarting Auto-Pilot Workflow...")
    print(f"1. Connecting to BIG-IP {host}...")

    # Test connectivity
    f5functions.bigip_connectivity_test(host, username, password, verify=ssl_verify)
    print("✓ BIG-IP connection verified.")

    # Generate
    print(f"2. Generating QKView '{qkview_name}' on appliance...")
    f5functions.bigip_generate_qkview(host, username, password, qkview_name, verify=ssl_verify)
    print("✓ QKView generated on appliance.")

    # Download
    print(f"3. Downloading QKView to local storage...")
    local_path = os.path.join(".", qkview_name)
    f5functions.bigip_download_qkview(host, username, password, qkview_name, local_path, verify=ssl_verify)
    print(f"✓ Download complete: {local_path} ({os.path.getsize(local_path):,} bytes)")

    # Delete remote
    del_remote = _prompt("Delete QKView from BIG-IP appliance storage to save disk space? (y/n)", default="y").lower()
    if del_remote in ["y", "yes"]:
        print("4. Purging QKView from BIG-IP storage...")
        f5functions.bigip_delete_qkview(host, username, password, qkview_name, verify=ssl_verify)
        print("✓ Remote storage purged.")

    # iHealth Upload
    do_upload = _prompt("Upload QKView to F5 iHealth? (y/n)", default="y").lower()
    if do_upload in ["y", "yes"]:
        print("5. Resolving iHealth credentials...")
        client_id, client_secret = f5functions.resolve_ihealth_credentials()
        print("✓ Authenticating to F5 Identity Services...")
        token = f5functions.myf5_authenticate(f5functions.IHEALTH_APP_ID, client_id, client_secret, scope='ihealth')
        print(f"6. Streaming {qkview_name} to F5 iHealth over TLS 1.3...")
        resp = f5functions.ihealth_upload_qkview(token, local_path, case_number=case_num, description=desc)
        if resp.status_code in [200, 201, 202]:
            print(f"✓ Upload successful!")
            try:
                res_data = resp.json()
                qkview_id = res_data.get("id") or res_data.get("qkview_id")
                if qkview_id:
                    print(f"   QKView ID: {qkview_id}")
                    print(f"   Analysis URL: https://ihealth.f5.com/qkview-analyzer/qv/{qkview_id}")
            except Exception:
                pass
        else:
            print(f"Upload failed: HTTP {resp.status_code}: {resp.text}")

    print("\n✓ Auto-Pilot workflow finished successfully!\n")


def run_doctor_wizard():
    """Run environment health check and diagnostics."""
    print("\n=======================================================")
    print("   QKViewMgr System Doctor: Environment Diagnostics")
    print("=======================================================")

    print(f"Python Runtime: {sys.version.split()[0]} ({sys.executable})")
    print(f"TLS Library: {f5functions.ssl.OPENSSL_VERSION}")

    # Check credentials
    print("\n--- Credential Stores ---")
    creds_file = os.path.expanduser("~/.ihealth_credentials")
    if os.path.isfile(creds_file):
        print(f"✓ Found credentials file: {creds_file}")
    else:
        print(f"ℹ No ~/.ihealth_credentials file found (can be set for passwordless operation)")

    env_client_id = os.getenv("F5_CLIENT_ID") or os.getenv("IHEALTH_CLIENT_ID")
    if env_client_id:
        print(f"✓ Found F5_CLIENT_ID in environment")
    else:
        print("ℹ F5_CLIENT_ID not set in environment")

    env_bigip_user = os.getenv("BIGIP_USERNAME") or os.getenv("BIGIP_USER") or os.getenv("F5_USERNAME")
    if env_bigip_user:
        print(f"✓ Found BIGIP_USERNAME in environment ({env_bigip_user})")
    else:
        print("ℹ BIGIP_USERNAME not set in environment (default: admin)")

    env_bigip_pw = os.getenv("BIGIP_PASSWORD") or os.getenv("F5_PASSWORD")
    if env_bigip_pw:
        print("✓ Found BIGIP_PASSWORD in environment")
    else:
        print("ℹ BIGIP_PASSWORD not set in environment (will prompt interactively)")


    # Check network reachability
    print("\n--- Network & TLS Endpoint Reachability ---")
    endpoints = [
        ("F5 Identity (Legacy Okta)", f"https://{f5functions.OKTA_IDENTITY_FQDN}"),
        ("F5 Identity (Auth0)", f"https://{f5functions.AUTH0_IDENTITY_FQDN}"),
        ("F5 iHealth API (Primary)", f"https://{f5functions.IHEALTH_API_FQDN}"),
        ("F5 iHealth API (Fallback)", f"https://{f5functions.IHEALTH_FALLBACK_API_FQDN}"),
        ("MyF5 Support API", f"https://{f5functions.MYF5_API_FQDN}"),
    ]

    session = f5functions.get_secure_session(verify=True)
    for name, url in endpoints:
        try:
            r = session.get(url, timeout=5, allow_redirects=False)
            print(f"✓ {name}: Reachable (HTTP {r.status_code})")
        except Exception as e:
            print(f"✗ {name}: Failed ({e})")

    print("\n--- Diagnostics Complete ---\n")


def main_menu():
    """Main interactive terminal wizard loop."""
    while True:
        print("\n=======================================================")
        print("          QKViewMgr Interactive Terminal Wizard        ")
        print("=======================================================")
        print("1. One-Touch Auto-Pilot (Generate -> Download -> Upload)")
        print("2. BIG-IP Connectivity Test")
        print("3. iHealth: List Existing QKViews")
        print("4. iHealth: Upload Local QKView File")
        print("5. System Doctor & Network Diagnostics")
        print("6. Exit")
        choice = input("\nSelect an option [1-6]: ").strip()

        if choice == "1":
            run_auto_wizard()
        elif choice == "2":
            host = _prompt("BIG-IP Hostname or IP")
            if host:
                user = _prompt("BIG-IP Username", default="admin")
                pw = _prompt("BIG-IP Password", secret=True)
                no_ssl = _prompt("Disable SSL Verification? (y/n)", default="y").lower() in ["y", "yes"]
                f5functions.bigip_connectivity_test(host, user, pw, verify=not no_ssl)
        elif choice == "3":
            try:
                cid, csec = f5functions.resolve_ihealth_credentials()
                token = f5functions.myf5_authenticate(f5functions.IHEALTH_APP_ID, cid, csec, scope="ihealth")
                f5functions.ihealth_list_qkviews(token)
            except Exception as e:
                print(f"Error: {e}")
        elif choice == "4":
            local_file = _prompt("Path to local .qkview file")
            if local_file and os.path.isfile(local_file):
                case = _prompt("Support Case Number (optional)")
                desc = _prompt("Upload Description", default="Uploaded via qkviewmgr wizard")
                cid, csec = f5functions.resolve_ihealth_credentials()
                token = f5functions.myf5_authenticate(f5functions.IHEALTH_APP_ID, cid, csec, scope="ihealth")
                f5functions.ihealth_upload_qkview(token, local_file, case_number=case, description=desc)
            else:
                print(f"File not found: {local_file}")
        elif choice == "5":
            run_doctor_wizard()
        elif choice in ["6", "q", "exit", "quit"]:
            print("Exiting QKViewMgr Wizard. Goodbye!")
            break
        else:
            print("Invalid selection, please try again.")


if __name__ == "__main__":
    main_menu()
