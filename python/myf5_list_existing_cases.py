#!/usr/bin/env python

import f5functions


def main():
    args = f5functions.myf5_args(
        (["--show-closed"], {"action": "store_true", "help": "Show closed cases", "required": False, "default": False}),
    )
    access_token = f5functions.myf5_authenticate(args.app_id, args.client_id, args.client_secret)

    # List support cases
    support_case_list = f5functions.myf5_list_support_cases(access_token)
    if support_case_list.status_code != 200:
        raise SystemExit(f'Failed to retrieve support cases.\nStatus code: {support_case_list.status_code} Full response: {support_case_list.text}')

    print(f'Total cases found: {support_case_list.json()["count"]}')
    for current_case in support_case_list.json()["data"]:
        if not args.show_closed and current_case["status"] == "Closed":
            continue
        print(f'Case: {current_case["caseNumber"]} ({current_case["status"]}) - {current_case["subject"]} (Opened {current_case["dateOpened"]})')


if __name__ == "__main__":
    main()
