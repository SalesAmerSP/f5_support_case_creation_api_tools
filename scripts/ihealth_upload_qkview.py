#!/usr/bin/env python3
"""Upload a local QKView file to F5 iHealth for analysis and case association.

Usage:
    # Requires F5_CLIENT_ID & F5_CLIENT_SECRET in env or ~/.f5api_credentials
    python3 scripts/ihealth_upload_qkview.py --filename diag.qkview [--support-case C12345] [--profile <profile>]
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
try:
    from qkviewmgr import f5functions
except ImportError:
    import f5functions


def main():
    """Authenticate and upload specified QKView file to iHealth."""
    args = f5functions.ihealth_args(
        (["--filename"], {"help": "Path to local QKview file to upload", "required": True}),
        (["--support-case"], {"type": str, "help": "F5 Support Case number to associate", "required": False, "default": None}),
    )
    access_token = f5functions.myf5_authenticate(
        args.app_id, args.client_id, args.client_secret,
        scope='ihealth', auth_url=args.auth_url, auth_fqdn=args.auth_fqdn
    )

    print(f'Uploading {args.filename} to iHealth...')
    qkview_upload = f5functions.ihealth_upload_qkview(
        access_token, args.filename,
        support_case_number=args.support_case or '',
        api_fqdn=args.api_fqdn
    )
    print(f'Status code: {qkview_upload.status_code}')
    print(qkview_upload.text)


if __name__ == "__main__":
    main()
