#!/usr/bin/env python3
"""Delete a QKView diagnostic file from an F5 BIG-IP device via iControl REST.

Usage:
    python3 python/bigip_delete_qkview.py --host <ip> --username admin --password <pwd> \
        --filename diag.qkview [--no-ssl-verify]
"""

import f5functions


def main():
    """Locate QKView by filename and delete it from the BIG-IP device."""
    args = f5functions.bigip_args(
        (["--filename"], {"type": str, "help": "QKView filename to delete", "required": True}),
    )
    verify = not args.no_ssl_verify

    print(f'Deleting QKview on BIG-IP {args.host}')
    qkview_deletion = f5functions.bigip_delete_qkview(args.host, args.username, args.password, args.filename, verify=verify)
    if qkview_deletion.status_code == 200:
        print('QKview deletion successful.')


if __name__ == "__main__":
    main()
