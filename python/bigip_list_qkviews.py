#!/usr/bin/env python3
"""List completed QKViews present on an F5 BIG-IP device via iControl REST.

Usage:
    python3 python/bigip_list_qkviews.py --host <ip> --username admin --password <pwd> [--no-ssl-verify]
"""

from datetime import datetime
import f5functions


def main():
    """Retrieve and display table of existing QKViews on the BIG-IP device."""
    args = f5functions.bigip_args()
    verify = not args.no_ssl_verify

    print(f'Retrieving list of QKviews on BIG-IP {args.host}\n')
    qkview_list = f5functions.bigip_list_qkviews(args.host, args.username, args.password, verify=verify)
    if qkview_list.status_code != 200:
        raise SystemExit(f'Failed to retrieve QKview list.\nStatus code: {qkview_list.status_code} Full response: {qkview_list.text}')

    items = qkview_list.json().get("items", [])
    for current_qkview in items:
        print(f'Name: {current_qkview.get("name", "N/A")}')
        print(f'Status: {current_qkview.get("status", "N/A")}')
        print(f'ID: {current_qkview.get("id", "N/A")}')
        last_update = current_qkview.get("lastUpdateMicros", 0)
        print(f'Last Update: {datetime.fromtimestamp(last_update / 1000000)}')
        try:
            print(f'URI: {current_qkview["qkviewUri"].replace("https://localhost/", f"https://{args.host}/")}\n')
        except KeyError:
            print(f'URI: {current_qkview.get("selfLink", "").replace("https://localhost/", f"https://{args.host}/")}\n')
    print(f'Total Qkviews found: {len(items)}')


if __name__ == "__main__":
    main()
