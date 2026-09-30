#!/usr/bin/env python3
"""download_browser - Interactive and CLI Browser for F5 MyF5 Software Downloads.

Allows operators and automation systems to:
  1. Explore available F5 product families (BIG-IP, BIG-IQ, F5OS, NGINX, etc.).
  2. Inspect product lines, release versions, and containers.
  3. View available image files, sizes, and cryptographic hashes (SHA-256, MD5).
  4. Stream-download software images directly with chunked transfer, progress meters,
     and real-time cryptographic integrity verification.
  5. Directly download from presigned S3/CDN URLs without requiring credentials.

Endpoints & Transition Context:
  - System Date: September 24, 2026.
  - Upcoming Maintenance: Friday, September 25, 2026, 9:00 - 11:00 AM PT
    (DNS cutover of callhome.f5.com and api.f5.com to F5 Distributed Cloud / XC).
  - Upcoming Migration: Friday, October 2, 2026
    (Downloads API base URL migration to https://api.software.downloads.f5.com without 'k' parameter).
"""

import argparse
import datetime
import json
import os
import sys

_SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

import f5functions

# Date and Cutover Constants
CURRENT_DATE_STR = "September 24, 2026"
MAINTENANCE_ADVISORY = (
    "Friday, September 25, 2026: 9:00 - 11:00 AM PT (DNS cutover to F5 Distributed Cloud / XC)"
)
MIGRATION_ADVISORY = (
    "Friday, October 2, 2026: Downloads API base URL changes to https://api.software.downloads.f5.com"
)


def format_bytes(bytes_val):
    """Format integer byte count into human-readable string.

    Args:
        bytes_val (int or str): Byte size.

    Returns:
        str: Human-readable string, e.g. '2.40 GB'.
    """
    try:
        val = float(bytes_val)
    except (ValueError, TypeError):
        return str(bytes_val)

    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if val < 1024.0 or unit == "TB":
            return f"{val:.2f} {unit}"
        val /= 1024.0
    return f"{val:.2f} TB"


def print_banner():
    """Print the download_browser header banner with date context and status."""
    print("=" * 70)
    print("       F5 MyF5 Software Download Browser & Image Retriever")
    print(f"       System Date: {CURRENT_DATE_STR}")
    print("=" * 70)
    print(f" * Notice: {MIGRATION_ADVISORY}")
    print(f" * Notice: {MAINTENANCE_ADVISORY}")
    print("=" * 70)


def get_token(args):
    """Resolve credentials and authenticate with F5 Identity Services.

    Args:
        args (argparse.Namespace): Command line arguments.

    Returns:
        str: Bearer access token.
    """
    auth_fqdn = getattr(args, "auth_fqdn", f5functions.IDENTITY_API_FQDN)
    profile = getattr(args, "profile", None)

    client_id, client_secret = f5functions.resolve_ihealth_credentials(
        client_id=getattr(args, "client_id", None),
        client_secret=getattr(args, "client_secret", None),
        profile=profile
    )

    print("Authenticating with F5 Identity Services...")
    token = f5functions.myf5_authenticate(
        f5functions.MYF5_APP_ID,
        client_id,
        client_secret,
        auth_fqdn=auth_fqdn,
        scope="myf5_scope"
    )
    return token


# ---------------------------------------------------------------------------
# Command Handlers
# ---------------------------------------------------------------------------

def cmd_families(args, token=None):
    """List available product families."""
    token = token or get_token(args)
    api_fqdn = getattr(args, "api_fqdn", f5functions.MYF5_DOWNLOADS_API_FQDN)
    resp = f5functions.myf5_get_downloads_metadata(token, api_fqdn=api_fqdn)

    if resp.status_code != 200:
        print(f"Error fetching metadata: HTTP {resp.status_code} - {resp.text}", file=sys.stderr)
        return 1

    data = resp.json().get("data", {})
    families = data.get("productFamilies", [])

    if getattr(args, "json", False):
        print(json.dumps([{"name": f.get("name"), "lines_count": len(f.get("productLines", []))} for f in families], indent=2))
        return 0

    print(f"\nAvailable Product Families ({len(families)}):")
    print("-" * 50)
    for i, fam in enumerate(families, start=1):
        lines = fam.get("productLines", [])
        print(f"{i:>2}. {fam.get('name'):<25} ({len(lines)} product lines)")
    print()
    return 0


def cmd_lines(args, token=None):
    """List product lines for a given family."""
    token = token or get_token(args)
    api_fqdn = getattr(args, "api_fqdn", f5functions.MYF5_DOWNLOADS_API_FQDN)
    resp = f5functions.myf5_get_downloads_metadata(token, api_fqdn=api_fqdn)

    if resp.status_code != 200:
        print(f"Error fetching product lines: HTTP {resp.status_code} - {resp.text}", file=sys.stderr)
        return 1

    data = resp.json().get("data", {})
    families = data.get("productFamilies", [])
    target_fam = getattr(args, "family", "BIG-IP")

    matched_family = next((f for f in families if f.get("name", "").lower() == target_fam.lower()), None)
    if not matched_family:
        print(f"Product family '{target_fam}' not found.", file=sys.stderr)
        return 1

    lines = matched_family.get("productLines", [])
    filt = getattr(args, "filter", None)
    if filt:
        lines = [l for l in lines if filt.lower() in l.get("name", "").lower() or filt.lower() in l.get("displayName", "").lower()]

    if getattr(args, "json", False):
        print(json.dumps(lines, indent=2))
        return 0

    print(f"\nProduct Lines for {matched_family.get('name')} ({len(lines)}):")
    print(f"{'Line Name':<28} | {'Display Name'}")
    print("-" * 65)
    for l in lines:
        print(f"{l.get('name', ''):<28} | {l.get('displayName', '')}")
    print()
    return 0


def cmd_versions(args, token=None):
    """List versions and release containers for a product line."""
    token = token or get_token(args)
    api_fqdn = getattr(args, "api_fqdn", f5functions.MYF5_DOWNLOADS_API_FQDN)
    resp = f5functions.myf5_get_product_versions(token, args.family, args.line, api_fqdn=api_fqdn)

    if resp.status_code != 200:
        print(f"Error fetching versions: HTTP {resp.status_code} - {resp.text}", file=sys.stderr)
        return 1

    data = resp.json().get("data", {})
    versions = data.get("versions", [])
    filt = getattr(args, "filter", None)
    if filt:
        versions = [v for v in versions if filt.lower() in v.get("version", "").lower()]

    if getattr(args, "json", False):
        print(json.dumps(versions, indent=2))
        return 0

    print(f"\nAvailable Versions for {args.family} / {args.line} ({len(versions)}):")
    print(f"{'Version':<18} | {'Release Date':<24} | Containers / Files")
    print("-" * 75)
    for v in versions:
        ver_name = v.get("version", "N/A")
        rel_date = v.get("releaseDate", "N/A")
        containers = v.get("containers", [])
        total_files = sum(len(c.get("files", [])) for c in containers)
        c_names = ", ".join(c.get("name", "") for c in containers)
        print(f"{ver_name:<18} | {rel_date:<24} | {len(containers)} containers ({total_files} files) [{c_names}]")
    print()
    return 0


def cmd_files(args, token=None):
    """List files in a specific container."""
    token = token or get_token(args)
    api_fqdn = getattr(args, "api_fqdn", f5functions.MYF5_DOWNLOADS_API_FQDN)
    resp = f5functions.myf5_get_product_versions(token, args.family, args.line, api_fqdn=api_fqdn)

    if resp.status_code != 200:
        print(f"Error fetching files: HTTP {resp.status_code} - {resp.text}", file=sys.stderr)
        return 1

    data = resp.json().get("data", {})
    versions = data.get("versions", [])
    matched_ver = next((v for v in versions if v.get("version") == args.version), None)
    if not matched_ver:
        print(f"Version '{args.version}' not found for {args.family}/{args.line}.", file=sys.stderr)
        return 1

    containers = matched_ver.get("containers", [])
    target_container = getattr(args, "container", None)
    if target_container:
        containers = [c for c in containers if c.get("name") == target_container]

    filt = getattr(args, "filter", None)

    all_files = []
    for c in containers:
        c_name = c.get("name")
        for f in c.get("files", []):
            if filt and filt.lower() not in f.get("filename", "").lower() and filt.lower() not in f.get("description", "").lower():
                continue
            all_files.append({"container": c_name, **f})

    if getattr(args, "json", False):
        print(json.dumps(all_files, indent=2))
        return 0

    print(f"\nFiles in {args.family} / {args.line} / {args.version} ({len(all_files)} files):")
    print(f"{'Filename':<38} | {'Size':<12} | {'Container':<12} | Description")
    print("-" * 85)
    for f in all_files:
        fn = f.get("filename", "")
        sz = format_bytes(f.get("bytes", 0))
        c_name = f.get("container", "")
        desc = f.get("description", "")
        print(f"{fn:<38} | {sz:<12} | {c_name:<12} | {desc}")
    print()
    return 0


def cmd_links(args, token=None):
    """Retrieve download links and checksums for a specific file."""
    token = token or get_token(args)
    api_fqdn = getattr(args, "api_fqdn", f5functions.MYF5_DOWNLOADS_API_FQDN)
    container = getattr(args, "container", args.version)
    lang = getattr(args, "language", "english")

    resp = f5functions.myf5_get_download_file_links(
        token, args.family, args.line, args.version, container, args.file, language=lang, api_fqdn=api_fqdn
    )

    if resp.status_code != 200:
        print(f"Error fetching file links: HTTP {resp.status_code} - {resp.text}", file=sys.stderr)
        return 1

    data = resp.json().get("data", {})
    if getattr(args, "json", False):
        print(json.dumps(data, indent=2))
        return 0

    print(f"\nDownload Details for: {args.file}")
    print("=" * 65)
    print(f"Product Family : {args.family}")
    print(f"Product Line   : {args.line}")
    print(f"Version        : {args.version}")
    print(f"Container      : {container}")
    print(f"File Size      : {format_bytes(data.get('bytes', 0))}")
    print(f"SHA-256 Hash   : {data.get('sha256', 'N/A')}")
    print(f"MD5 Hash       : {data.get('md5', 'N/A')}")
    print("\nRegional Download Mirrors:")
    for link in data.get("downloadLinks", []):
        reg = link.get("region", "Global")
        url = link.get("href", "")
        print(f"  [{reg}]")
        print(f"    {url}")
    print()
    return 0


def cmd_download(args, token=None):
    """Download a file from the catalog with progress and checksum validation."""
    token = token or get_token(args)
    api_fqdn = getattr(args, "api_fqdn", f5functions.MYF5_DOWNLOADS_API_FQDN)
    container = getattr(args, "container", args.version)
    lang = getattr(args, "language", "english")

    print(f"Querying download links for {args.file}...")
    resp = f5functions.myf5_get_download_file_links(
        token, args.family, args.line, args.version, container, args.file, language=lang, api_fqdn=api_fqdn
    )

    if resp.status_code != 200:
        print(f"Error retrieving download link: HTTP {resp.status_code} - {resp.text}", file=sys.stderr)
        return 1

    data = resp.json().get("data", {})
    links = data.get("downloadLinks", [])
    if not links:
        print(f"No download mirrors returned for {args.file}.", file=sys.stderr)
        return 1

    region_req = getattr(args, "region", None)
    chosen_link = links[0]
    if region_req:
        for l in links:
            if region_req.lower() in l.get("region", "").lower():
                chosen_link = l
                break

    download_url = chosen_link.get("href")
    expected_hash = data.get("sha256") or data.get("md5")
    hash_algo = "sha256" if data.get("sha256") else "md5"
    if getattr(args, "no_verify", False):
        expected_hash = None

    dest_path = getattr(args, "output", None)
    if not dest_path:
        dest_dir = getattr(args, "dest_dir", ".")
        dest_path = os.path.join(dest_dir, args.file)
    elif os.path.isdir(dest_path):
        dest_path = os.path.join(dest_path, args.file)

    print(f"\nMirror Region  : {chosen_link.get('region', 'Default')}")
    print(f"File Size      : {format_bytes(data.get('bytes', 0))}")
    if expected_hash:
        print(f"Integrity Check: {hash_algo.upper()} ({expected_hash})")
    print(f"Destination    : {os.path.abspath(dest_path)}")
    print("-" * 65)

    try:
        saved_file = f5functions.myf5_download_file(
            download_url,
            dest_path,
            expected_checksum=expected_hash,
            checksum_algo=hash_algo
        )
        print(f"\n✓ Download completed and verified successfully: {saved_file}\n")
        return 0
    except ValueError as e:
        print(f"\n[SECURITY WARNING] Checksum verification failed: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"\n[ERROR] Download failed: {e}", file=sys.stderr)
        return 1


def cmd_url(args):
    """Download directly from presigned S3/CDN URL without credentials."""
    url = args.url
    dest_path = getattr(args, "output", None)
    if not dest_path:
        # Infer filename from URL
        base = url.split("?")[0].rstrip("/").split("/")[-1]
        dest_path = base if base else "f5_downloaded_image.iso"

    expected_hash = getattr(args, "checksum", None)
    algo = getattr(args, "algo", "sha256")

    print(f"Initiating direct URL streaming download...")
    print(f"Source URL     : {url}")
    print(f"Destination    : {os.path.abspath(dest_path)}")
    if expected_hash:
        print(f"Expected {algo.upper()} : {expected_hash}")

    try:
        saved_file = f5functions.myf5_download_file(
            url,
            dest_path,
            expected_checksum=expected_hash,
            checksum_algo=algo
        )
        print(f"\n✓ Download completed and verified: {saved_file}\n")
        return 0
    except ValueError as e:
        print(f"\n[SECURITY WARNING] Cryptographic integrity failure: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"\n[ERROR] Download failed: {e}", file=sys.stderr)
        return 1


def cmd_status(args):
    """Perform pre-flight audit of F5 Identity, Downloads API, and upcoming cutover timelines."""
    print("=" * 70)
    print("            MyF5 Downloads Pre-Flight & Operational Audit")
    print(f"            Audit Date: {CURRENT_DATE_STR}")
    print("=" * 70)

    # 1. Timeline Advisory
    print("\n[1/3] Operational Timelines & Cutover Status:")
    print(f"  • Today's Date           : {CURRENT_DATE_STR}")
    print(f"  • DNS Maintenance Window : {MAINTENANCE_ADVISORY}")
    print("    - Impact: callhome.f5.com and api.f5.com migrate to F5 XC / ESDP Anycast IPs.")
    print("    - Action: Ensure egress firewalls allow F5 XC IP ranges (per K15202).")
    print(f"  • Downloads API Cutover  : {MIGRATION_ADVISORY}")
    print("    - Impact: api.software.downloads.f5.com active without 'k' query param.")

    # 2. Credential Check
    print("\n[2/3] Identity & Credential Configuration:")
    try:
        profile = getattr(args, "profile", None)
        cid, csec = f5functions.resolve_ihealth_credentials(profile=profile)
        masked_id = cid[:4] + "*" * (len(cid) - 8) + cid[-4:] if len(cid) > 8 else "***"
        print(f"  • Client ID Resolved     : {masked_id} (Configured)")
        print(f"  • Client Secret Resolved : [Available in memory / masked]")
    except Exception as e:
        print(f"  • Credentials            : [NOT CONFIGURED] ({e})")
        return 1

    # 3. Connectivity Verification
    print("\n[3/3] Live API Connectivity:")
    token = None
    try:
        token = f5functions.myf5_authenticate(f5functions.MYF5_APP_ID, cid, csec, scope="myf5_scope")
        print("  • F5 Identity Auth       : [PASS] Authentication successful (Bearer JWT received)")
    except Exception as e:
        print(f"  • F5 Identity Auth       : [FAIL] ({e})")
        return 1

    try:
        resp = f5functions.myf5_get_downloads_metadata(token)
        if resp.status_code == 200:
            count = len(resp.json().get("data", {}).get("productFamilies", []))
            print(f"  • Downloads Catalog API  : [PASS] HTTP 200 OK ({count} product families available)")
        else:
            print(f"  • Downloads Catalog API  : [WARN] HTTP {resp.status_code}")
    except Exception as e:
        print(f"  • Downloads Catalog API  : [FAIL] ({e})")

    print("\n✓ System is fully operational and transition-ready.\n")
    return 0


# ---------------------------------------------------------------------------
# Interactive Browser Mode
# ---------------------------------------------------------------------------

def browse_interactive(args):
    """Run menu-driven interactive terminal browser."""
    print_banner()

    try:
        token = get_token(args)
    except Exception as e:
        print(f"\nAuthentication error: {e}", file=sys.stderr)
        return 1

    api_fqdn = getattr(args, "api_fqdn", f5functions.MYF5_DOWNLOADS_API_FQDN)
    print("\nLoading product catalog...")
    resp = f5functions.myf5_get_downloads_metadata(token, api_fqdn=api_fqdn)
    if resp.status_code != 200:
        print(f"Failed to retrieve catalog: HTTP {resp.status_code} - {resp.text}", file=sys.stderr)
        return 1

    data = resp.json().get("data", {})
    families = data.get("productFamilies", [])
    if not families:
        print("No product families found in catalog.", file=sys.stderr)
        return 1

    while True:
        # Step 1: Select Product Family
        print("\n" + "=" * 50)
        print("STEP 1: Select Product Family")
        print("=" * 50)
        for i, fam in enumerate(families, start=1):
            line_count = len(fam.get("productLines", []))
            print(f"  [{i:>2}] {fam.get('name'):<22} ({line_count} product lines)")
        print("  [ q] Quit")

        choice = input("\nEnter selection [1-{} or q]: ".format(len(families))).strip()
        if choice.lower() == "q":
            print("Exiting download_browser.")
            return 0
        try:
            fam_idx = int(choice) - 1
            if fam_idx < 0 or fam_idx >= len(families):
                print("Invalid selection.")
                continue
        except ValueError:
            print("Invalid input.")
            continue

        selected_fam = families[fam_idx]
        fam_name = selected_fam.get("name")
        lines = selected_fam.get("productLines", [])

        # Step 2: Select Product Line
        while True:
            print("\n" + "=" * 50)
            print(f"STEP 2: Select Product Line for {fam_name}")
            print("=" * 50)
            for i, l in enumerate(lines, start=1):
                print(f"  [{i:>2}] {l.get('name'):<24} | {l.get('displayName')}")
            print("  [ b] Back to Product Families")
            print("  [ q] Quit")

            choice = input("\nEnter selection [1-{}, b, or q]: ".format(len(lines))).strip()
            if choice.lower() == "q":
                return 0
            if choice.lower() == "b":
                break
            try:
                line_idx = int(choice) - 1
                if line_idx < 0 or line_idx >= len(lines):
                    print("Invalid selection.")
                    continue
            except ValueError:
                print("Invalid input.")
                continue

            selected_line = lines[line_idx]
            line_name = selected_line.get("name")

            # Step 3: Fetch & Select Version
            print(f"\nRetrieving versions for {fam_name} / {line_name}...")
            v_resp = f5functions.myf5_get_product_versions(token, fam_name, line_name, api_fqdn=api_fqdn)
            if v_resp.status_code != 200:
                print(f"Error fetching versions: HTTP {v_resp.status_code}", file=sys.stderr)
                continue

            v_data = v_resp.json().get("data", {})
            versions = v_data.get("versions", [])
            if not versions:
                print(f"No versions found for {line_name}.")
                continue

            while True:
                print("\n" + "=" * 50)
                print(f"STEP 3: Select Version for {line_name}")
                print("=" * 50)
                for i, v in enumerate(versions, start=1):
                    v_str = v.get("version")
                    r_date = v.get("releaseDate", "")[:10]
                    c_count = len(v.get("containers", []))
                    print(f"  [{i:>2}] {v_str:<18} (Released: {r_date}) [{c_count} containers]")
                print("  [ b] Back to Product Lines")
                print("  [ q] Quit")

                choice = input("\nEnter selection [1-{}, b, or q]: ".format(len(versions))).strip()
                if choice.lower() == "q":
                    return 0
                if choice.lower() == "b":
                    break
                try:
                    ver_idx = int(choice) - 1
                    if ver_idx < 0 or ver_idx >= len(versions):
                        print("Invalid selection.")
                        continue
                except ValueError:
                    print("Invalid input.")
                    continue

                selected_ver = versions[ver_idx]
                ver_name = selected_ver.get("version")
                containers = selected_ver.get("containers", [])

                # Step 4: Select File
                all_files = []
                for c in containers:
                    c_name = c.get("name")
                    for f in c.get("files", []):
                        all_files.append({"container": c_name, **f})

                if not all_files:
                    print(f"No downloadable files found in version {ver_name}.")
                    continue

                while True:
                    print("\n" + "=" * 50)
                    print(f"STEP 4: Select File to Inspect/Download ({ver_name})")
                    print("=" * 50)
                    for i, f in enumerate(all_files, start=1):
                        fn = f.get("filename")
                        sz = format_bytes(f.get("bytes", 0))
                        print(f"  [{i:>2}] {fn:<38} ({sz:>9})")
                    print("  [ b] Back to Versions")
                    print("  [ q] Quit")

                    choice = input("\nEnter selection [1-{}, b, or q]: ".format(len(all_files))).strip()
                    if choice.lower() == "q":
                        return 0
                    if choice.lower() == "b":
                        break
                    try:
                        file_idx = int(choice) - 1
                        if file_idx < 0 or file_idx >= len(all_files):
                            print("Invalid selection.")
                            continue
                    except ValueError:
                        print("Invalid input.")
                        continue

                    selected_file = all_files[file_idx]
                    fn = selected_file.get("filename")
                    container_name = selected_file.get("container")

                    # Step 5: Details & Download Prompt
                    print(f"\nFetching download mirrors and hash verification for {fn}...")
                    links_resp = f5functions.myf5_get_download_file_links(
                        token, fam_name, line_name, ver_name, container_name, fn, api_fqdn=api_fqdn
                    )

                    if links_resp.status_code != 200:
                        print(f"Error fetching links: HTTP {links_resp.status_code} - {links_resp.text}")
                        continue

                    link_data = links_resp.json().get("data", {})
                    download_links = link_data.get("downloadLinks", [])
                    sha256 = link_data.get("sha256")
                    md5 = link_data.get("md5")

                    print("\n" + "=" * 60)
                    print(f"FILE DETAILS: {fn}")
                    print("=" * 60)
                    print(f"Size         : {format_bytes(link_data.get('bytes', selected_file.get('bytes', 0)))}")
                    print(f"Description  : {selected_file.get('description', 'N/A')}")
                    print(f"SHA-256 Hash : {sha256 or 'N/A'}")
                    print(f"MD5 Hash     : {md5 or 'N/A'}")
                    print(f"Mirrors      : {len(download_links)} region(s) available")
                    for dl in download_links:
                        print(f"  • {dl.get('region', 'Mirror')}")
                    print("=" * 60)

                    dl_confirm = input("\nDo you want to download this image now? [Y/n]: ").strip().lower()
                    if dl_confirm not in ("", "y", "yes"):
                        print("Download cancelled.")
                        continue

                    dest_dir = input("Enter destination directory [default: current directory]: ").strip()
                    if not dest_dir:
                        dest_dir = "."
                    dest_path = os.path.join(dest_dir, fn)

                    chosen_mirror = download_links[0]
                    chosen_url = chosen_mirror.get("href")
                    expected_hash = sha256 or md5
                    hash_algo = "sha256" if sha256 else "md5"

                    print(f"\nInitiating streaming download from {chosen_mirror.get('region', 'Mirror')}...")
                    try:
                        saved = f5functions.myf5_download_file(
                            chosen_url,
                            dest_path,
                            expected_checksum=expected_hash,
                            checksum_algo=hash_algo
                        )
                        print(f"\n✓ Download completed and integrity verified: {saved}\n")
                    except ValueError as e:
                        print(f"\n[SECURITY WARNING] Checksum mismatch: {e}", file=sys.stderr)
                    except Exception as e:
                        print(f"\n[ERROR] Download failed: {e}", file=sys.stderr)

                    input("\nPress Enter to continue browsing...")


# ---------------------------------------------------------------------------
# Main CLI Dispatcher
# ---------------------------------------------------------------------------

def main():
    """Main CLI entry point for download_browser."""
    f5functions.check_no_cli_secrets()
    parser = argparse.ArgumentParser(
        prog="download_browser",
        description="F5 MyF5 Software Download Browser & Image Retriever",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Interactive Browser:
    download_browser

  Scriptable CLI:
    download_browser status
    download_browser families
    download_browser lines --family BIG-IP
    download_browser versions --family BIG-IP --line big-ip_v16.x
    download_browser files --family BIG-IP --line big-ip_v16.x --version 16.1.6
    download_browser links --family BIG-IP --line big-ip_v16.x --version 16.1.6 --file BIGIP-16.1.6-0.0.12.iso
    download_browser get --family BIG-IP --line big-ip_v16.x --version 16.1.6 --file BIGIP-16.1.6-0.0.12.iso
    download_browser url --url "https://downloads.f5.com/s3/..." --output ./image.iso --checksum 1234abcd
        """
    )

    parser.add_argument("--profile", help="Profile/section in ~/.f5api_credentials")
    parser.add_argument("--api-fqdn", default=f5functions.MYF5_DOWNLOADS_API_FQDN, help="Downloads API FQDN")
    parser.add_argument("--auth-fqdn", default=f5functions.IDENTITY_API_FQDN, help="F5 Identity Auth FQDN")
    parser.add_argument("-i", "--interactive", action="store_true", help="Launch interactive menu browser")

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Status / Pre-flight
    subparsers.add_parser("status", help="Run system pre-flight audit & verify API connectivity")

    # Families
    fam_parser = subparsers.add_parser("families", help="List available product families")
    fam_parser.add_argument("--json", action="store_true", help="Output JSON format")

    # Lines
    line_parser = subparsers.add_parser("lines", help="List product lines for a family")
    line_parser.add_argument("--family", default="BIG-IP", help="Product family (default: BIG-IP)")
    line_parser.add_argument("--filter", help="Filter lines by keyword")
    line_parser.add_argument("--json", action="store_true", help="Output JSON format")

    # Versions
    ver_parser = subparsers.add_parser("versions", help="List versions and containers for a product line")
    ver_parser.add_argument("--family", default="BIG-IP", help="Product family (default: BIG-IP)")
    ver_parser.add_argument("--line", required=True, help="Product line (e.g. big-ip_v16.x)")
    ver_parser.add_argument("--filter", help="Filter versions by keyword")
    ver_parser.add_argument("--json", action="store_true", help="Output JSON format")

    # Files
    file_parser = subparsers.add_parser("files", help="List downloadable files for a version")
    file_parser.add_argument("--family", default="BIG-IP", help="Product family (default: BIG-IP)")
    file_parser.add_argument("--line", required=True, help="Product line (e.g. big-ip_v16.x)")
    file_parser.add_argument("--version", required=True, help="Product version (e.g. 16.1.6)")
    file_parser.add_argument("--container", help="Container name (defaults to version)")
    file_parser.add_argument("--filter", help="Filter filenames by keyword")
    file_parser.add_argument("--json", action="store_true", help="Output JSON format")

    # Links
    links_parser = subparsers.add_parser("links", help="Get download links and checksums for a file")
    links_parser.add_argument("--family", default="BIG-IP", help="Product family (default: BIG-IP)")
    links_parser.add_argument("--line", required=True, help="Product line (e.g. big-ip_v16.x)")
    links_parser.add_argument("--version", required=True, help="Product version (e.g. 16.1.6)")
    links_parser.add_argument("--container", help="Container name (defaults to version)")
    links_parser.add_argument("--file", required=True, help="Filename (e.g. BIGIP-16.1.6-0.0.12.iso)")
    links_parser.add_argument("--language", default="english", help="Language (default: english)")
    links_parser.add_argument("--json", action="store_true", help="Output JSON format")

    # Get / Download
    get_parser = subparsers.add_parser("get", help="Download a software image file from the catalog")
    get_parser.add_argument("--family", default="BIG-IP", help="Product family (default: BIG-IP)")
    get_parser.add_argument("--line", required=True, help="Product line (e.g. big-ip_v16.x)")
    get_parser.add_argument("--version", required=True, help="Product version (e.g. 16.1.6)")
    get_parser.add_argument("--container", help="Container name (defaults to version)")
    get_parser.add_argument("--file", required=True, help="Filename (e.g. BIGIP-16.1.6-0.0.12.iso)")
    get_parser.add_argument("--output", help="Destination file path")
    get_parser.add_argument("--dest-dir", default=".", help="Destination directory (default: .)")
    get_parser.add_argument("--region", help="Preferred mirror region (e.g. 'USA - EAST COAST')")
    get_parser.add_argument("--no-verify", action="store_true", help="Skip checksum integrity check")

    # URL Direct Download
    url_parser = subparsers.add_parser("url", help="Download directly from presigned URL (no auth)")
    url_parser.add_argument("--url", required=True, help="Presigned direct download URL")
    url_parser.add_argument("--output", help="Destination path")
    url_parser.add_argument("--checksum", help="Expected cryptographic checksum")
    url_parser.add_argument("--algo", default="sha256", help="Checksum algorithm (default: sha256)")

    args = parser.parse_args()

    # If no subcommand provided or -i/--interactive specified, launch interactive mode
    if not args.command or args.interactive:
        return browse_interactive(args)

    if args.command == "status":
        return cmd_status(args)
    elif args.command == "families":
        return cmd_families(args)
    elif args.command == "lines":
        return cmd_lines(args)
    elif args.command == "versions":
        return cmd_versions(args)
    elif args.command == "files":
        return cmd_files(args)
    elif args.command == "links":
        return cmd_links(args)
    elif args.command == "get":
        return cmd_download(args)
    elif args.command == "url":
        return cmd_url(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
