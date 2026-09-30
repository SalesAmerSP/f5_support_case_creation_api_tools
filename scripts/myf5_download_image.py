#!/usr/bin/env python3
"""Download software images and verify integrity from the MyF5 Downloads API.

Demonstrates:
  1. Authenticating to F5 Identity Services (Auth0 / legacy Okta).
  2. Resolving product download links and hashes from api.software.downloads.f5.com
     (handling the October 2 URL update and removal of the 'k' parameter).
  3. Streaming chunked download with real-time tqdm progress bar.
  4. Cryptographic integrity verification (SHA-256 / MD5).

Usage:
  # 1. List available product families and product lines:
  python3 examples/myf5_download_image.py --list-products

  # 2. List versions and container images for BIG-IP:
  python3 examples/myf5_download_image.py --list-versions --product-family BIG-IP --product-line big-ip_v16.x

  # 3. Download a software image and verify its SHA-256 hash:
  python3 examples/myf5_download_image.py \
      --product-family BIG-IP \
      --product-line big-ip_v16.x \
      --product-version 16.1.2 \
      --container 16.1.2 \
      --file-name BIGIP-16.1.2-0.0.18.iso \
      --output BIGIP-16.1.2-0.0.18.iso
"""

import argparse
import json
import os
import sys

# Ensure repository src directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
try:
    from qkviewmgr import f5functions
except ImportError:
    import f5functions


def main():
    parser = f5functions._downloads_base_parser() if hasattr(f5functions, '_downloads_base_parser') else argparse.ArgumentParser()
    parser.add_argument('--list-products', action='store_true', help='List all available product families and product lines')
    parser.add_argument('--list-versions', action='store_true', help='List available versions and containers for a product line')
    parser.add_argument('--product-family', '--family', dest='product_family', default=None, help="Product family (e.g. 'BIG-IP')")
    parser.add_argument('--product-line', '--product', dest='product_line', default=None, help="Product line (e.g. 'big-ip_v16.x')")
    parser.add_argument('--product-version', '--version', dest='product_version', default=None, help="Product version (e.g. '16.1.2')")
    parser.add_argument('--container', default=None, help="Container name / version (e.g. '16.1.2')")
    parser.add_argument('--file-name', '--filename', dest='file_name', default=None, help="Software filename (e.g. 'BIGIP-16.1.2-0.0.18.iso')")
    parser.add_argument('--language', default='english', help="Language (default: 'english')")
    parser.add_argument('--url', default=None, help="Direct download URL (skips link resolution)")
    parser.add_argument('--output', '-o', default=None, help="Local destination file path")
    parser.add_argument('--checksum', default=None, help="Expected cryptographic hash (SHA-256 or MD5)")
    parser.add_argument('--checksum-algo', default='sha256', help="Checksum algorithm (default: 'sha256')")
    parser.add_argument('--json', action='store_true', help="Output raw JSON response")

    args = parser.parse_args()

    # If direct URL is given, download immediately
    if args.url:
        output_file = args.output or os.path.basename(args.url.split('?')[0]) or 'downloaded_image.iso'
        print(f"Downloading directly from URL to {output_file}...")
        f5functions.myf5_download_file(
            args.url, output_file,
            expected_checksum=args.checksum,
            checksum_algo=args.checksum_algo
        )
        print(f"✓ Successfully downloaded and verified {output_file}")
        return

    # Authenticate to F5 Identity
    cid, csec = f5functions.resolve_ihealth_credentials(args.client_id, args.client_secret, getattr(args, 'profile', None))
    app_id = getattr(args, 'app_id', f5functions.MYF5_APP_ID)
    auth_url = getattr(args, 'auth_url', None)
    auth_fqdn = getattr(args, 'auth_fqdn', f5functions.IDENTITY_API_FQDN)
    api_fqdn = getattr(args, 'api_fqdn', f5functions.MYF5_DOWNLOADS_API_FQDN)

    print("Authenticating to F5 Identity Services...")
    token = f5functions.myf5_authenticate(app_id, cid, csec, scope='myf5_scope', auth_url=auth_url, auth_fqdn=auth_fqdn)

    # Action 1: List products / metadata
    if args.list_products:
        print(f"Retrieving downloads metadata from {api_fqdn} (no 'k' parameter)...")
        resp = f5functions.myf5_get_downloads_metadata(token, api_fqdn=api_fqdn)
        if resp.status_code != 200:
            raise SystemExit(f"Failed to retrieve metadata: HTTP {resp.status_code} - {resp.text}")
        data = resp.json()
        if args.json:
            print(json.dumps(data, indent=2))
            return
        families = data.get("data", {}).get("productFamilies", [])
        if not families and isinstance(data, list):
            families = data
        print("=" * 75)
        print(" Available Product Families & Product Lines (api.software.downloads.f5.com)")
        print("=" * 75)
        for fam in families:
            print(f"\nProduct Family: {fam.get('name')}")
            for pl in fam.get("productLines", []):
                print(f"  - {pl.get('name'):25} | {pl.get('displayName')}")
        print("=" * 75)
        return

    # Action 2: List versions for product line
    if args.list_versions:
        if not args.product_family or not args.product_line:
            raise SystemExit("Error: --product-family and --product-line are required when using --list-versions.")
        print(f"Retrieving versions for {args.product_family} / {args.product_line}...")
        resp = f5functions.myf5_get_product_versions(token, args.product_family, args.product_line, api_fqdn=api_fqdn)
        if resp.status_code != 200:
            raise SystemExit(f"Failed to retrieve product versions: HTTP {resp.status_code} - {resp.text}")
        data = resp.json()
        if args.json:
            print(json.dumps(data, indent=2))
            return
        print("=" * 75)
        print(f" Available Versions for {args.product_family} / {args.product_line}")
        print("=" * 75)
        for v in data.get("versions", []):
            print(f"\nVersion: {v.get('version')} (Released: {v.get('releaseDate')})")
            for c in v.get("containers", []):
                print(f"  Container: {c.get('container')} [{c.get('type')}] - {c.get('description')}")
                for f in c.get("files", []):
                    fname = f.get("filename")
                    fbytes = f.get("bytes", "0")
                    try:
                        mb = int(fbytes) / (1024 * 1024)
                        size_str = f"{mb:.1f} MB"
                    except Exception:
                        size_str = f"{fbytes} bytes"
                    print(f"    * File: {fname:35} ({size_str})")
        print("=" * 75)
        return

    # Action 3: Download specific file
    if not (args.product_family and args.product_line and args.product_version and args.container and args.file_name):
        parser.print_help()
        print("\nTip: Specify --list-products to explore available products, or provide")
        print("--product-family, --product-line, --product-version, --container, and --file-name to download.")
        sys.exit(1)

    print(f"Fetching download links and checksums for {args.file_name} from {api_fqdn}...")
    resp = f5functions.myf5_get_download_file_links(
        token, args.product_family, args.product_line,
        args.product_version, args.container, args.file_name,
        language=args.language, api_fqdn=api_fqdn
    )
    if resp.status_code != 200:
        raise SystemExit(f"Failed to retrieve file links: HTTP {resp.status_code} - {resp.text}")

    data = resp.json()
    if args.json:
        print(json.dumps(data, indent=2))

    links = data.get("downloadLinks", [])
    if not links:
        raise SystemExit(f"No download links found for {args.file_name}")

    download_url = links[0].get("href")
    meta = data.get("meta", {})
    expected_hash = args.checksum or meta.get(args.checksum_algo.lower()) or data.get(args.checksum_algo.lower())

    out_path = args.output or args.file_name
    print(f"Found download link ({links[0].get('hosting')} / {links[0].get('location')})")
    if expected_hash:
        print(f"Expected {args.checksum_algo.upper()}: {expected_hash}")

    print(f"Streaming {args.file_name} to {out_path}...")
    f5functions.myf5_download_file(
        download_url,
        out_path,
        expected_checksum=expected_hash,
        checksum_algo=args.checksum_algo
    )
    print(f"\n✓ Download and cryptographic verification complete: {out_path}")


if __name__ == '__main__':
    main()
