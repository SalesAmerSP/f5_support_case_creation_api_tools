#!/usr/bin/env python3
"""List uploaded QKViews and analysis metadata from F5 iHealth.

Supports both Okta and Auth0 authentication endpoints (per K000162308).

Usage:
    python3 examples/ihealth_list_qkviews.py --client-id <id> --client-secret <secret> \
        [--auth-fqdn idp.identity.f5.com] [--api-fqdn ihealth2-api.f5.com]
"""

import datetime
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
try:
    from qkviewmgr import f5functions
except ImportError:
    import f5functions


def main():
    """Retrieve all uploaded QKView IDs and display summary diagnostics."""
    args = f5functions.ihealth_args()
    access_token = f5functions.myf5_authenticate(
        args.app_id, args.client_id, args.client_secret,
        scope='ihealth', auth_url=args.auth_url, auth_fqdn=args.auth_fqdn
    )

    qkview_id_list = f5functions.ihealth_list_qkview_ids(access_token, api_fqdn=args.api_fqdn)
    if qkview_id_list.status_code != 200:
        raise SystemExit(f'Failed to retrieve QKview IDs.\nStatus code: {qkview_id_list.status_code} Full response: {qkview_id_list.text}')

    ids = qkview_id_list.json().get("id", [])
    for qkview_id in ids:
        qkview_metadata = f5functions.ihealth_show_qkview_metadata(access_token, qkview_id, api_fqdn=args.api_fqdn)
        if qkview_metadata.status_code not in (200, 202):
            raise SystemExit(f'Failed to retrieve QKview metadata for {qkview_id}.\nStatus code: {qkview_metadata.status_code} Full response: {qkview_metadata.text}')
        data = qkview_metadata.json()
        proc_status = data.get("processing_status", "COMPLETED")
        print('*********************************************************************************************')
        print(f' QKView ID: {qkview_id} [Status: {proc_status}]')
        print(f' Hostname: {data.get("hostname") or "N/A"}')
        print(f' File Name: {data.get("file_name") or "N/A"}')
        print(f' Description: {data.get("description") or "N/A"}')
        gen_date = data.get("generation_date")
        if gen_date:
            try:
                created_date = datetime.datetime.fromtimestamp(gen_date / 1000).strftime('%Y-%m-%d %H:%M:%S')
            except (ValueError, OSError, TypeError):
                created_date = str(gen_date)
        else:
            upload_date = (data.get("upload") or {}).get("date")
            if upload_date:
                try:
                    created_date = datetime.datetime.fromtimestamp(upload_date / 1000).strftime('%Y-%m-%d %H:%M:%S')
                except (ValueError, OSError, TypeError):
                    created_date = str(upload_date)
            else:
                created_date = "Processing..."
        print(f' Date: {created_date}')
        print(f' Chassis Serial: {data.get("chassis_serial") or "N/A"}')
        print(f' Support Case: {data.get("f5_support_case") or "N/A"}')
        print(f' URL: {data.get("gui_uri") or "N/A"}')
        print('*********************************************************************************************')
    print(f'Total QKview IDs found: {len(ids)}')


if __name__ == "__main__":
    main()
