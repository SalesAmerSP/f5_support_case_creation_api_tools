#!/usr/bin/env python

import f5functions


def main():
    args = f5functions.myf5_args(
        (["--case-number"], {"help": "F5 Support Case Number", "required": True}),
        (["--comment-text-file"], {"help": "File containing notes to attach", "required": True}),
    )
    access_token = f5functions.myf5_authenticate(args.app_id, args.client_id, args.client_secret)

    # Read comments file
    with open(args.comment_text_file, 'r') as f:
        comments = f.read()

    # Confirm with user
    print(f'The following comments will be added to case {args.case_number}:')
    print(f'{comments}  ')

    confirm = input('Is this correct? (y/n): ')
    if confirm.lower() not in ('y', 'yes'):
        raise SystemExit('Aborting.')
    print(f'Adding comments to case {args.case_number}')

    # Update the case
    updated_case = f5functions.myf5_add_comments_to_existing_support_case(access_token, args.case_number, comments)
    if updated_case.status_code != 200:
        raise SystemExit(f'Failed to update case.\nStatus code: {updated_case.status_code} Full response: {updated_case.text}')

    print(f'Case update {updated_case.json()["status"]} at {updated_case.json()["data"]["updatedDate"]}. {updated_case.json()["message"]}')
    print(f'Case ID: {updated_case.json()["data"]["caseNumber"]}')
    print(f'Case URL: {updated_case.json()["links"][0]["href"]}')
    print(f'API response: {updated_case.text}')


if __name__ == "__main__":
    main()
