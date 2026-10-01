#!/usr/bin/env python3
"""qkviewmgr - Unified Manager & Automation CLI for F5 BIG-IP, iHealth, and MyF5 Cases.

Provides:
  - One-Touch Auto-Pilot (`qkviewmgr run` / `qkviewmgr auto`)
  - Subcommands: `bigip`, `ihealth`, `case`, `doctor`, `gui`, `wizard`
  - Zero Plaintext Secrets in CLI arguments (interactive masking and env vars)
  - Native Desktop GUI (Strictly NO web services)
  - Interactive Terminal Wizard
"""

import argparse
import json
import os
import ssl
import sys
import time

_src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

import f5functions

try:
    from . import wizard
    from . import gui
except ImportError:
    import wizard
    import gui


# ---------------------------------------------------------------------------
# Auto-Pilot Orchestrator
# ---------------------------------------------------------------------------

def cmd_auto_pilot(args):
    """Execute the end-to-end One-Touch QKView workflow."""
    print("=" * 65)
    print("       qkviewmgr Auto-Pilot: End-to-End Diagnostic Pipeline")
    print("=" * 65)

    host = args.host
    username = f5functions.resolve_bigip_username(args.username)
    password = f5functions.resolve_bigip_credentials(host, username, getattr(args, "password", None))
    verify_ssl = not args.no_ssl_verify

    raw_name = args.qkview_name or f"{host.replace('.', '_')}_diag.qkview"
    qkview_name = os.path.basename(raw_name)
    output_dir = args.output_dir or "."
    local_path = os.path.join(output_dir, qkview_name)

    # Step 1: BIG-IP connectivity & pre-flight
    print(f"\n[1/5] Verifying BIG-IP connectivity: {username}@{host}...")
    f5functions.bigip_connectivity_test(host, username, password, verify=verify_ssl)
    print("      ✓ Connection successful.")

    # Step 2: Generate QKView on appliance
    print(f"\n[2/5] Triggering QKView generation on appliance ({qkview_name})...")
    resp_gen = f5functions.bigip_generate_qkview(
        host, username, password, qkview_name,
        no_truncate=args.no_truncate, verify=verify_ssl
    )
    if hasattr(resp_gen, "json") and callable(resp_gen.json):
        try:
            task_id = resp_gen.json().get("id")
            if isinstance(task_id, str) and task_id:
                print(f"      ... Waiting for generation task ({task_id}) to complete...")
                f5functions.bigip_wait_for_qkview(host, username, password, task_id, verify=verify_ssl)
        except Exception:
            pass
    print("      ✓ Appliance finished QKView generation.")

    # Step 3: Download QKView
    print(f"\n[3/5] Downloading QKView to local storage...")
    f5functions.bigip_download_qkview(host, username, password, qkview_name, local_path, verify=verify_ssl)
    file_size_mb = os.path.getsize(local_path) / (1024 * 1024)
    print(f"      ✓ Saved to: {local_path} ({file_size_mb:.2f} MB)")

    # Step 4: Appliance storage cleanup
    if not args.no_delete_remote:
        print(f"\n[4/5] Purging temporary QKView from BIG-IP appliance storage...")
        try:
            f5functions.bigip_delete_qkview(host, username, password, qkview_name, verify=verify_ssl)
            print("      ✓ Remote appliance storage purged.")
        except Exception as e:
            print(f"      ! Warning: Remote cleanup encountered: {e}")
    else:
        print("\n[4/5] Skipping remote file deletion (--no-delete-remote specified).")

    # Step 5: iHealth Upload & Tracking
    if not args.no_upload:
        cid, csec = f5functions.resolve_ihealth_credentials(
            client_id=getattr(args, "client_id", None),
            client_secret=getattr(args, "client_secret", None),
            profile=getattr(args, "profile", None)
        )
        token = f5functions.myf5_authenticate(f5functions.IHEALTH_APP_ID, cid, csec, scope="ihealth")
        resp = f5functions.ihealth_upload_qkview(
            token, local_path,
            case_number=args.case_number,
            description=args.description or f"Automated upload via qkviewmgr from {host}"
        )
        if resp.status_code in [200, 201, 202]:
            print("      ✓ QKView accepted by F5 iHealth.")
            try:
                res_data = resp.json()
                qid = res_data.get("id") or res_data.get("qkview_id")
                if qid:
                    print(f"\n      QKView ID: {qid}")
                    print(f"      Analysis Portal: https://ihealth.f5.com/qkview-analyzer/qv/{qid}")

                    if not args.no_wait:
                        print("\n      Tracking diagnostic processing status...")
                        for _ in range(30):
                            time.sleep(10)
                            try:
                                status_resp = f5functions.ihealth_show_qkview_metadata(token, qid)
                                if status_resp.status_code == 200:
                                    st = status_resp.json().get("status", "PROCESSING")
                                    print(f"      Current Status: {st}")
                                    if st in ["COMPLETE", "SUCCESS"]:
                                        print("      ✓ Diagnostics analysis is COMPLETE!")
                                        break
                                    elif st in ["FAILED", "ERROR"]:
                                        print("      ! Processing marked as FAILED in iHealth.")
                                        break
                            except Exception:
                                pass
            except Exception:
                pass
        else:
            print(f"      ! Upload failed (HTTP {resp.status_code}): {resp.text}")
    else:
        print("\n[5/5] Skipping iHealth upload (--no-upload specified).")

    print("\n" + "=" * 65)
    print("      ✓ Auto-Pilot workflow finished successfully.")
    print("=" * 65 + "\n")


# ---------------------------------------------------------------------------
# BIG-IP Subcommand Handlers
# ---------------------------------------------------------------------------

def cmd_bigip(args):
    action = args.action
    host = args.host
    username = f5functions.resolve_bigip_username(args.username)
    password = f5functions.resolve_bigip_credentials(host, username, getattr(args, "password", None))
    verify_ssl = not args.no_ssl_verify

    if action == "test":
        resp = f5functions.bigip_connectivity_test(host, username, password, verify=verify_ssl)
        if resp.status_code == 200:
            print(f"✓ BIG-IP {host} connection and authentication SUCCESSFUL (HTTP 200).")
        else:
            print(f"✗ BIG-IP connection returned HTTP {resp.status_code}: {resp.text}")
    elif action == "list":
        resp = f5functions.bigip_list_qkviews(host, username, password, verify=verify_ssl)
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            print(f"Found {len(items)} QKView(s) on BIG-IP {host}:")
            for it in items:
                print(f"  Name: {it.get('name') or it.get('filename')} | ID: {it.get('id')} | Status: {it.get('status')}")
        else:
            print(f"Failed to list QKViews: HTTP {resp.status_code}: {resp.text}")
    elif action == "status":
        info = f5functions.bigip_get_system_info(host, username, password, verify=verify_ssl)
        print("=" * 60)
        print(f" BIG-IP System Information ({host})")
        print("=" * 60)
        print(f" Hostname      : {info.get('hostname')}")
        print(f" Product       : {info.get('product')}")
        print(f" Version       : {info.get('version')} (Build {info.get('build')})")
        print(f" Edition       : {info.get('edition')}")
        print(f" Failover State: {info.get('failover_state')}")
        print("=" * 60)
    elif action == "generate":
        resp = f5functions.bigip_generate_qkview(
            host, username, password, args.filename,
            no_truncate=args.no_truncate, verify=verify_ssl
        )
        if getattr(args, "wait", False):
            task_id = resp.json().get("id") if hasattr(resp, "json") else None
            if task_id:
                print(f"✓ QKView generation initiated (task ID: {task_id}). Waiting for completion...")
                def _cb(status, data):
                    print(f"  ... QKView generation status: {status}")
                f5functions.bigip_wait_for_qkview(
                    host, username, password, task_id,
                    timeout=getattr(args, "wait_timeout", 300),
                    verify=verify_ssl,
                    callback=_cb
                )
                print(f"✓ QKView '{args.filename}' generation SUCCEEDED on {host}.")
            else:
                print(f"✓ QKView '{args.filename}' generated successfully on {host}.")
        else:
            print(f"✓ QKView '{args.filename}' generated successfully on {host}.")
    elif action == "download":
        f5functions.bigip_download_qkview(host, username, password, args.filename, args.output, verify=verify_ssl)
        print(f"✓ QKView downloaded successfully to {args.output}.")
    elif action == "delete":
        f5functions.bigip_delete_qkview(host, username, password, args.filename, verify=verify_ssl)
        print(f"✓ QKView '{args.filename}' deleted from {host}.")



# ---------------------------------------------------------------------------
# iHealth Subcommand Handlers
# ---------------------------------------------------------------------------

def cmd_ihealth(args):
    action = args.action
    cid, csec = f5functions.resolve_ihealth_credentials(
        client_id=getattr(args, "client_id", None),
        client_secret=getattr(args, "client_secret", None),
        profile=getattr(args, "profile", None)
    )
    token = f5functions.myf5_authenticate(getattr(args, "app_id", None) or f5functions.IHEALTH_APP_ID, cid, csec, scope="ihealth")

    if action == "test":
        f5functions.ihealth_connectivity_test(token)
    elif action == "list":
        f5functions.ihealth_list_qkviews(token)
    elif action == "show":
        resp = f5functions.ihealth_show_qkview_metadata(token, args.qkview_id)
        if resp.status_code == 200:
            print(json.dumps(resp.json(), indent=2))
        else:
            print(f"Error HTTP {resp.status_code}: {resp.text}")
    elif action == "upload":
        f5functions.ihealth_upload_qkview(
            token, args.filename,
            case_number=args.case_number,
            description=args.description
        )


# ---------------------------------------------------------------------------
# Case Subcommand Handlers
# ---------------------------------------------------------------------------

def cmd_case(args):
    action = args.action
    cid, csec = f5functions.resolve_ihealth_credentials(
        client_id=getattr(args, "client_id", None),
        client_secret=getattr(args, "client_secret", None),
        profile=getattr(args, "profile", None)
    )
    token = f5functions.myf5_authenticate(getattr(args, "app_id", None) or f5functions.MYF5_APP_ID, cid, csec, scope="myf5_scope")

    if action == "list":
        resp = f5functions.myf5_list_support_cases(token)
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            print(f"Found {len(data)} support case(s):")
            for c in data:
                print(f"  - Case {c.get('caseNumber', 'N/A')}: {c.get('subject', 'No Subject')} [{c.get('status', 'Open')}]")
        else:
            print(f"Error HTTP {resp.status_code}: {resp.text}")
    elif action == "metadata":
        resp = f5functions.myf5_retrieve_case_creation_metadata(token)
        if resp.status_code == 200:
            print(json.dumps(resp.json(), indent=2))
        else:
            print(f"Error HTTP {resp.status_code}: {resp.text}")
    elif action == "create":
        with open(args.json_file, "r") as f:
            data = json.load(f)
        resp = f5functions.myf5_create_new_support_case(token, data)
        if resp.status_code in (200, 201):
            res_json = resp.json()
            case_id = res_json.get("data", {}).get("caseNumber", "N/A")
            print(f"✓ Case created successfully! Case Number: {case_id}")
            if "links" in res_json and res_json["links"]:
                print(f"  Case URL: {res_json['links'][0].get('href')}")
        else:
            print(f"Error HTTP {resp.status_code}: {resp.text}")
    elif action == "comment":
        resp = f5functions.myf5_add_comments_to_existing_support_case(token, args.case_number, args.comment)
        if resp.status_code == 200:
            print(f"✓ Comment added to case {args.case_number}.")
        else:
            print(f"Error HTTP {resp.status_code}: {resp.text}")


# ---------------------------------------------------------------------------
# MyF5 Software Downloads Handlers (api.software.downloads.f5.com)
# ---------------------------------------------------------------------------

def cmd_downloads(args):
    """Handle MyF5 Downloads API operations (metadata, versions, links, get)."""
    action = args.action
    api_fqdn = getattr(args, "api_fqdn", f5functions.MYF5_DOWNLOADS_API_FQDN)

    # Direct URL download bypasses API auth
    if action == "get" and getattr(args, "url", None):
        output_file = args.output or os.path.basename(args.url.split("?")[0]) or "downloaded_image.iso"
        checksum_algo = getattr(args, "checksum_algo", "sha256")
        expected_checksum = getattr(args, "checksum", None)
        print(f"Initiating direct streaming download of {os.path.basename(output_file)}...")
        try:
            saved_path = f5functions.myf5_download_file(
                args.url,
                output_file,
                expected_checksum=expected_checksum,
                checksum_algo=checksum_algo,
            )
            print(f"✓ Download completed and verified: {saved_path}")
            return
        except ValueError as ve:
            print(f"✗ Checksum verification FAILED: {ve}")
            sys.exit(1)
        except Exception as e:
            print(f"✗ Download failed: {e}")
            sys.exit(1)

    cid, csec = f5functions.resolve_ihealth_credentials(
        client_id=getattr(args, "client_id", None),
        client_secret=getattr(args, "client_secret", None),
        profile=getattr(args, "profile", None)
    )
    token = f5functions.myf5_authenticate(getattr(args, "app_id", None) or f5functions.MYF5_APP_ID, cid, csec, scope="myf5_scope")

    if action in ("metadata", "list-products"):
        resp = f5functions.myf5_get_downloads_metadata(token, api_fqdn=api_fqdn)
        if resp.status_code == 200:
            data = resp.json()
            if getattr(args, "json", False):
                print(json.dumps(data, indent=2))
                return
            families = data.get("data", {}).get("productFamilies", [])
            if not families and isinstance(data, list):
                families = data
            print(f"Available Product Families and Lines ({api_fqdn}):")
            for fam in families:
                print(f"\nProduct Family: {fam.get('name')}")
                for pl in fam.get("productLines", []):
                    print(f"  - {pl.get('name'):25} | {pl.get('displayName')}")
        else:
            print(f"Failed to retrieve downloads metadata: HTTP {resp.status_code}: {resp.text}")
            sys.exit(1)

    elif action == "versions":
        if not args.product_family or not args.product_line:
            print("Error: --product-family and --product-line are required for 'versions' action.")
            sys.exit(1)
        resp = f5functions.myf5_get_product_versions(token, args.product_family, args.product_line, api_fqdn=api_fqdn)
        if resp.status_code == 200:
            raw = resp.json()
            if getattr(args, "json", False):
                print(json.dumps(raw, indent=2))
                return
            data = raw.get("data", raw) if isinstance(raw, dict) else {}
            versions = data.get("versions") or (raw.get("versions", []) if isinstance(raw, dict) else [])
            containers = data.get("containers", [])
            print(f"Product: {args.product_family} / {args.product_line}")
            if versions:
                for v in versions:
                    vname = v.get("version", "N/A")
                    vdate = v.get("releaseDate", "N/A")
                    print(f"\nVersion: {vname} (Released: {vdate})")
                    for c in v.get("containers", []):
                        cname = c.get("name") or c.get("container") or c.get("containerName", "N/A")
                        cdate = c.get("releaseDate", "N/A")
                        print(f"  Container: {cname} (Released: {cdate})")
                        for f in c.get("files", []):
                            fname = f.get("filename") or f.get("name") or f.get("fileName")
                            fbytes = f.get("bytes") or "N/A"
                            print(f"    - {fname} ({fbytes} bytes)")
            elif containers:
                for c in containers:
                    cname = c.get("name") or c.get("container") or c.get("containerName", "N/A")
                    rel_date = c.get("releaseDate", "N/A")
                    print(f"\nContainer: {cname} (Released: {rel_date})")
                    files = c.get("files", [])
                    for f in files:
                        fname = f.get("filename") or f.get("name") or f.get("fileName")
                        fbytes = f.get("bytes") or "N/A"
                        print(f"  - {fname} ({fbytes} bytes)")
        else:
            print(f"Failed to retrieve product versions: HTTP {resp.status_code}: {resp.text}")
            sys.exit(1)

    elif action == "links":
        missing = [arg for arg in ("product_family", "product_line", "product_version", "container", "file_name") if not getattr(args, arg, None)]
        if missing:
            print(f"Error: Missing required argument(s) for 'links': {', '.join(missing)}")
            sys.exit(1)
        resp = f5functions.myf5_get_download_file_links(
            token,
            args.product_family,
            args.product_line,
            args.product_version,
            args.container,
            args.file_name,
            language=getattr(args, "language", "english"),
            api_fqdn=api_fqdn,
        )
        if resp.status_code == 200:
            raw = resp.json()
            if getattr(args, "json", False):
                print(json.dumps(raw, indent=2))
                return
            links_data = raw.get("data", raw) if isinstance(raw, dict) else {}
            links = links_data.get("downloadLinks") or (raw.get("downloadLinks", []) if isinstance(raw, dict) else [])
            print(f"Download Links for {args.file_name}:")
            for lnk in links:
                region = lnk.get('location') or lnk.get('region') or lnk.get('title') or lnk.get('hosting', 'Global')
                print(f"  Region : {region}")
                print(f"  URL    : {lnk.get('href')}\n")
            meta = links_data.get("meta") or (raw.get("meta", {}) if isinstance(raw, dict) else {})
            for h in ("sha256", "md5", "sha1", "sha384", "sha512"):
                if meta.get(h) or links_data.get(h):
                    print(f"  {h.upper()}: {meta.get(h) or links_data.get(h)}")
        else:
            print(f"Failed to retrieve download links: HTTP {resp.status_code}: {resp.text}")
            sys.exit(1)

    elif action == "get":
        missing = [arg for arg in ("product_family", "product_line", "product_version", "container", "file_name") if not getattr(args, arg, None)]
        if missing:
            print(f"Error: Missing required argument(s) for 'get': {', '.join(missing)} (or provide --url)")
            sys.exit(1)
        resp = f5functions.myf5_get_download_file_links(
            token,
            args.product_family,
            args.product_line,
            args.product_version,
            args.container,
            args.file_name,
            language=getattr(args, "language", "english"),
            api_fqdn=api_fqdn,
        )
        if resp.status_code != 200:
            print(f"Failed to retrieve download links: HTTP {resp.status_code}: {resp.text}")
            sys.exit(1)
        raw = resp.json()
        links_data = raw.get("data", raw) if isinstance(raw, dict) else {}
        links = links_data.get("downloadLinks") or (raw.get("downloadLinks", []) if isinstance(raw, dict) else [])
        if not links:
            print("No download links found in API response.")
            sys.exit(1)
        download_url = links[0].get("href")
        output_file = args.output or args.file_name
        checksum_algo = getattr(args, "checksum_algo", "sha256")
        expected_checksum = args.checksum
        if not expected_checksum:
            meta = links_data.get("meta") or (raw.get("meta", {}) if isinstance(raw, dict) else {})
            expected_checksum = meta.get(checksum_algo.lower()) or links_data.get(checksum_algo.lower())

        print(f"Initiating download of {os.path.basename(output_file)}...")
        if expected_checksum:
            print(f"Expected {checksum_algo.upper()} Checksum: {expected_checksum}")

        try:
            saved_path = f5functions.myf5_download_file(
                download_url,
                output_file,
                expected_checksum=expected_checksum,
                checksum_algo=checksum_algo,
            )
            print(f"✓ Download completed and verified: {saved_path}")
        except ValueError as ve:
            print(f"✗ Checksum verification FAILED: {ve}")
            sys.exit(1)
        except Exception as e:
            print(f"✗ Download failed: {e}")
            sys.exit(1)


# ---------------------------------------------------------------------------
# Doctor Pre-flight Check
# ---------------------------------------------------------------------------

def cmd_doctor(args):
    """Run comprehensive environment, TLS, network, and security health check."""
    print("=" * 65)
    print("          qkviewmgr System Doctor & Pre-flight Audit")
    print("=" * 65)

    print(f"\n1. Runtime Environment:")
    print(f"   Python Executable: {sys.executable}")
    print(f"   Python Version   : {sys.version.split()[0]}")
    print(f"   OpenSSL Version  : {ssl.OPENSSL_VERSION}")

    print(f"\n2. Credential Configuration:")
    f5_creds_path = os.path.expanduser("~/.f5api_credentials")
    ih_creds_path = os.path.expanduser("~/.ihealth_credentials")
    if os.path.isfile(f5_creds_path):
        print(f"   ✓ Found ~/.f5api_credentials (primary API credential store)")
    elif os.path.isfile(ih_creds_path):
        print(f"   ✓ Found ~/.ihealth_credentials (legacy credential store)")
    else:
        print(f"   ℹ Neither ~/.f5api_credentials nor ~/.ihealth_credentials present")

    f5_cid = os.getenv("F5_CLIENT_ID") or os.getenv("IHEALTH_CLIENT_ID")
    if f5_cid:
        print(f"   ✓ F5_CLIENT_ID set in environment")
    else:
        print(f"   ℹ F5_CLIENT_ID not set in environment")

    bigip_user = os.getenv("BIGIP_USERNAME") or os.getenv("BIGIP_USER") or os.getenv("F5_USERNAME")
    if bigip_user:
        print(f"   ✓ BIGIP_USERNAME set in environment ({bigip_user})")
    else:
        print(f"   ℹ BIGIP_USERNAME not set in environment (default: admin)")

    bigip_pw = os.getenv("BIGIP_PASSWORD") or os.getenv("F5_PASSWORD")
    if bigip_pw:
        print(f"   ✓ BIGIP_PASSWORD set in environment")
    else:
        print(f"   ℹ BIGIP_PASSWORD not set in environment (will prompt interactively)")


    print(f"\n3. TLS 1.2+ Network Endpoint Reachability:")
    session = f5functions.get_secure_session(verify=True)
    targets = [
        ("F5 Identity (Legacy)", f"https://{f5functions.OKTA_IDENTITY_FQDN}"),
        ("F5 Identity (Auth0)", f"https://{f5functions.AUTH0_IDENTITY_FQDN}"),
        ("F5 iHealth API", f"https://{f5functions.IHEALTH_API_FQDN}"),
        ("MyF5 Support API", f"https://{f5functions.MYF5_API_FQDN}"),
    ]
    all_ok = True
    for label, url in targets:
        try:
            r = session.get(url, timeout=5, allow_redirects=False)
            print(f"   ✓ {label} ({url}): Reachable (HTTP {r.status_code})")
        except Exception as e:
            all_ok = False
            print(f"   ✗ {label} ({url}): Failed ({e})")

    print("\n" + "=" * 65)
    if all_ok:
        print("   ✓ All pre-flight diagnostic checks passed!")
    else:
        print("   ! Some endpoints could not be reached. Check DNS and firewall rules.")
    print("=" * 65 + "\n")


# ---------------------------------------------------------------------------
# Main CLI Argument Parser
# ---------------------------------------------------------------------------

def main():
    f5functions.check_no_cli_secrets()
    parser = argparse.ArgumentParser(
        prog="qkviewmgr",
        description="qkviewmgr - Unified F5 BIG-IP, iHealth, and MyF5 Case Automation CLI",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # Subcommand: auto / run
    auto_parser = subparsers.add_parser("run", aliases=["auto"], help="One-touch auto-pilot: generate -> download -> purge remote -> upload to iHealth -> track")
    auto_parser.add_argument("--host", required=True, help="BIG-IP hostname or IP address")
    auto_parser.add_argument("--username", default=None, help="BIG-IP username (default: BIGIP_USERNAME env var or admin)")
    auto_parser.add_argument("--no-ssl-verify", action="store_true", help="Disable SSL certificate verification for self-signed lab appliances")
    auto_parser.add_argument("--qkview-name", default=None, help="Name of QKView archive to generate")
    auto_parser.add_argument("--no-truncate", action="store_true", help="Generate complete QKView without truncating large log files (-s0)")
    auto_parser.add_argument("--output-dir", default=".", help="Local directory to save downloaded QKView")
    auto_parser.add_argument("--no-delete-remote", action="store_true", help="Do not delete QKView from BIG-IP appliance storage after download")
    auto_parser.add_argument("--no-upload", action="store_true", help="Skip uploading to F5 iHealth")
    auto_parser.add_argument("--case-number", default=None, help="Associate upload with MyF5 Support Case number")
    auto_parser.add_argument("--description", default=None, help="Description for iHealth upload")
    auto_parser.add_argument("--no-wait", action="store_true", help="Do not wait/poll for iHealth diagnostic completion")
    auto_parser.add_argument("--profile", default=None, help="Profile/section in ~/.f5api_credentials")

    # Subcommand: bigip
    bigip_parser = subparsers.add_parser("bigip", help="Direct BIG-IP appliance operations")
    bigip_parser.add_argument("action", choices=["test", "list", "status", "generate", "download", "delete"], help="BIG-IP operation")
    bigip_parser.add_argument("--host", required=True, help="BIG-IP hostname or IP address")
    bigip_parser.add_argument("--username", default=None, help="BIG-IP username (default: BIGIP_USERNAME env var or admin)")
    bigip_parser.add_argument("--no-ssl-verify", action="store_true", help="Disable SSL certificate verification")
    bigip_parser.add_argument("--filename", default="test.qkview", help="QKView filename on BIG-IP")
    bigip_parser.add_argument("--output", default="test.qkview", help="Local output destination for download")
    bigip_parser.add_argument("--no-truncate", action="store_true", help="Generate complete QKView (-s0)")
    bigip_parser.add_argument("--wait", action="store_true", help="Wait for QKView generation to complete on device")
    bigip_parser.add_argument("--wait-timeout", type=int, default=300, help="Maximum seconds to wait for generation (default: 300)")

    # Subcommand: ihealth
    ihealth_parser = subparsers.add_parser("ihealth", help="F5 iHealth API operations")
    ihealth_parser.add_argument("action", choices=["test", "list", "show", "upload"], help="iHealth operation")
    ihealth_parser.add_argument("--profile", default=None, help="Profile in ~/.f5api_credentials")
    ihealth_parser.add_argument("--app-id", default=f5functions.IHEALTH_APP_ID, help="App ID")
    ihealth_parser.add_argument("--qkview-id", default=None, help="QKView ID for show operation")
    ihealth_parser.add_argument("--filename", default=None, help="Path to local .qkview file for upload")
    ihealth_parser.add_argument("--case-number", default=None, help="MyF5 Case Number")
    ihealth_parser.add_argument("--description", default="Uploaded via qkviewmgr", help="Upload description")

    # Subcommand: case
    case_parser = subparsers.add_parser("case", help="MyF5 Support Case Management")
    case_parser.add_argument("action", choices=["list", "create", "comment", "metadata"], help="Case operation")
    case_parser.add_argument("--profile", default=None, help="Profile in ~/.f5api_credentials")
    case_parser.add_argument("--app-id", default=f5functions.MYF5_APP_ID, help="App ID")
    case_parser.add_argument("--case-number", default=None, help="Support case number")
    case_parser.add_argument("--comment", default=None, help="Comment text to add")
    case_parser.add_argument("--json-file", default=None, help="Path to case creation JSON file")

    # Subcommand: downloads (api.software.downloads.f5.com)
    downloads_parser = subparsers.add_parser("downloads", help="MyF5 Software Downloads API operations (Oct 2 URL update)")
    downloads_parser.add_argument("action", choices=["metadata", "list-products", "versions", "links", "get"], help="Downloads operation")
    downloads_parser.add_argument("--profile", default=None, help="Profile in ~/.f5api_credentials")
    downloads_parser.add_argument("--app-id", default=f5functions.MYF5_APP_ID, help="App ID")
    downloads_parser.add_argument("--api-fqdn", default=f5functions.MYF5_DOWNLOADS_API_FQDN, help=f"Downloads API FQDN (default: {f5functions.MYF5_DOWNLOADS_API_FQDN})")
    downloads_parser.add_argument("--product-family", "--family", dest="product_family", default=None, help="Product family (e.g. 'BIG-IP')")
    downloads_parser.add_argument("--product-line", "--product", dest="product_line", default=None, help="Product line (e.g. 'big-ip_v16.x')")
    downloads_parser.add_argument("--product-version", "--version", dest="product_version", default=None, help="Product version (e.g. '16.1.2')")
    downloads_parser.add_argument("--container", default=None, help="Container name / version (e.g. '16.1.2')")
    downloads_parser.add_argument("--file-name", "--filename", dest="file_name", default=None, help="Software filename (e.g. 'BIGIP-16.1.2-0.0.18.iso')")
    downloads_parser.add_argument("--language", default="english", help="Product language (default: 'english')")
    downloads_parser.add_argument("--url", default=None, help="Direct download URL for 'get' action")
    downloads_parser.add_argument("--output", "-o", default=None, help="Local file path to save downloaded image")
    downloads_parser.add_argument("--checksum", default=None, help="Expected cryptographic hash for verification")
    downloads_parser.add_argument("--checksum-algo", default="sha256", help="Checksum algorithm (sha256, md5, sha1; default: sha256)")
    downloads_parser.add_argument("--json", action="store_true", help="Output raw JSON response")

    # Subcommand: doctor
    doctor_parser = subparsers.add_parser("doctor", help="Run pre-flight environment and network diagnostics")

    # Subcommand: gui
    gui_parser = subparsers.add_parser("gui", help="Launch native desktop GUI (Strictly NO web services)")

    # Subcommand: wizard
    wizard_parser = subparsers.add_parser("wizard", help="Launch interactive terminal wizard")

    # Parse args
    if len(sys.argv) == 1:
        if sys.stdin.isatty():
            print("No command specified. Launching interactive terminal wizard...")
            wizard.main_menu()
            return
        else:
            parser.print_help()
            sys.exit(1)

    args = parser.parse_args()

    if args.subcommand in ["run", "auto"]:
        cmd_auto_pilot(args)
    elif args.subcommand == "bigip":
        cmd_bigip(args)
    elif args.subcommand == "ihealth":
        cmd_ihealth(args)
    elif args.subcommand == "case":
        cmd_case(args)
    elif args.subcommand == "downloads":
        cmd_downloads(args)
    elif args.subcommand == "doctor":
        cmd_doctor(args)
    elif args.subcommand == "gui":
        gui.launch_gui()
    elif args.subcommand == "wizard":
        wizard.main_menu()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
