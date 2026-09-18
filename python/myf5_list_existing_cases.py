#!/usr/bin/env python3
"""List existing support cases associated with your MyF5 account.

Usage:
    python3 python/myf5_list_existing_cases.py --client-id <id> --client-secret <secret> \
        [--show-closed] [--auth-fqdn idp.identity.f5.com]
"""

import f5functions


def main():
    """Retrieve and display open (and optionally closed) MyF5 support cases."""
    args = f5functions.myf5_args(
        (["--show-closed"], {"action": "store_true", "help": "Include closed cases in output", "required": False, "default": False}),
    )
    access_token = f5functions.myf5_authenticate(
        args.app_id, args.client_id, args.client_secret,
        scope='myf5_scope', auth_url=args.auth_url, auth_fqdn=args.auth_fqdn
    )

    # List support cases
    support_case_list = f5functions.myf5_list_support_cases(
        access_token, api_fqdn=args.api_url, k_value=args.k_value
    )
    if support_case_list.status_code != 200:
        raise SystemExit(f'Failed to retrieve support cases.\nStatus code: {support_case_list.status_code} Full response: {support_case_list.text}')

    cases = support_case_list.json().get("data", [])
    print(f'Total cases found: {support_case_list.json().get("count", len(cases))}')
    for current_case in cases:
        if not args.show_closed and current_case.get("status") == "Closed":
            continue
        print(f'Case: {current_case.get("caseNumber")} ({current_case.get("status")}) - '
              f'{current_case.get("subject")} (Opened {current_case.get("dateOpened")})')


if __name__ == "__main__":
    main()
