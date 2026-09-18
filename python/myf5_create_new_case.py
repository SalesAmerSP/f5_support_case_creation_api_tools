#!/usr/bin/env python3
"""Submit a new support case to MyF5 using a pre-generated JSON inputs file.

Usage:
    python3 python/myf5_create_new_case.py --client-id <id> --client-secret <secret> \
        --inputs-file case_inputs.json [--auth-fqdn idp.identity.f5.com]
"""

import json
import f5functions


def main():
    """Load case inputs, review with user, and submit new case to MyF5."""
    args = f5functions.myf5_args(
        (["--inputs-file"], {"help": "Path to input JSON file", "required": True}),
    )
    access_token = f5functions.myf5_authenticate(
        args.app_id, args.client_id, args.client_secret,
        scope='myf5_scope', auth_url=args.auth_url, auth_fqdn=args.auth_fqdn
    )

    # Read inputs file
    with open(args.inputs_file, 'r') as f:
        inputs = json.load(f)

    # Confirm with user
    print('The following inputs will be used to create a new case:')
    for key, value in inputs.items():
        print(f'{key}: {value}')

    confirm = input('Is this correct? (y/n): ')
    if confirm.lower() not in ('y', 'yes'):
        raise SystemExit('Aborting.')

    # Create the case
    print('Submitting case to MyF5...')
    new_case = f5functions.myf5_create_new_support_case(
        access_token, inputs, api_fqdn=args.api_url, k_value=args.k_value
    )
    if new_case.status_code != 201:
        raise SystemExit(f'Failed to create case.\nStatus code: {new_case.status_code} Full response: {new_case.text}')

    print(f'Case creation {new_case.json().get("status", "SUCCESS")}. {new_case.json().get("message", "")}')
    print(f'Case ID: {new_case.json()["data"]["caseNumber"]}')
    if "links" in new_case.json() and new_case.json()["links"]:
        print(f'Case URL: {new_case.json()["links"][0]["href"]}')


if __name__ == "__main__":
    main()
