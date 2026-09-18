#!/usr/bin/env python3
"""Download a QKView file from an F5 BIG-IP device using chunked streaming.

Usage:
    python3 python/bigip_download_qkview.py --host <ip> --username admin --password <pwd> \
        --filename diag.qkview [--no-ssl-verify]
"""

import f5functions


def main():
    """Stream and save QKView file locally with progress bar tracking."""
    args = f5functions.bigip_args(
        (["--filename"], {"type": str, "help": "QKView filename on BIG-IP", "required": True}),
    )
    verify = not args.no_ssl_verify

    print(f'Downloading QKview on BIG-IP {args.host}')
    f5functions.bigip_download_qkview(args.host, args.username, args.password, args.filename, verify=verify)


if __name__ == "__main__":
    main()
