#!/usr/bin/env python3
"""Append notes or comments to an existing MyF5 support case from a text file.

Usage:
    python3 examples/myf5_add_comments_to_existing_case.py --client-id <id> --client-secret <secret> \
        --case-number C12345 --comment-text-file notes.txt [--auth-fqdn idp.identity.f5.com]
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
try:
    from qkviewmgr import f5functions
except ImportError:
    import f5functions


def main():
    """Read comment text, confirm with user, and attach notes to target support case."""
    args = f5functions.myf5_args(
        (["--case-number"], {"help": "F5 Support Case Number", "required": True}),
        (["--comment-text-file"], {"help": "Path to text file containing notes to attach", "required": True}),
    )
    access_token = f5functions.myf5_authenticate(
        args.app_id, args.client_id, args.client_secret,
        scope='myf5_scope', auth_url=args.auth_url, auth_fqdn=args.auth_fqdn
    )

    # Read comments file
    with open(args.comment_text_file, 'r') as f:
        comments = f.read()

    # Confirm with user
    print(f'The following comments will be added to case {args.case_number}:')
    print(f'{comments}\n')

    confirm = input('Is this correct? (y/n): ')
    if confirm.lower() not in ('y', 'yes'):
        raise SystemExit('Aborting.')
    print(f'Adding comments to case {args.case_number}...')

    # Update the case
    updated_case = f5functions.myf5_add_comments_to_existing_support_case(
        access_token, args.case_number, comments, api_fqdn=args.api_url, k_value=args.k_value
    )
    if updated_case.status_code != 200:
        raise SystemExit(f'Failed to update case.\nStatus code: {updated_case.status_code} Full response: {updated_case.text}')

    case_data = updated_case.json().get("data", {})
    print(f'Case update {updated_case.json().get("status", "SUCCESS")} at {case_data.get("updatedDate", "now")}. '
          f'{updated_case.json().get("message", "")}')
    print(f'Case ID: {case_data.get("caseNumber", args.case_number)}')
    if "links" in updated_case.json() and updated_case.json()["links"]:
        print(f'Case URL: {updated_case.json()["links"][0]["href"]}')


if __name__ == "__main__":
    main()
