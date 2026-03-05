#!/usr/bin/env python

import f5functions
import json


def main():
    args = f5functions.myf5_args(
        (["--inputs-file"], {"help": "Input file", "required": True}),
    )
    access_token = f5functions.myf5_authenticate(args.app_id, args.client_id, args.client_secret)

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
    new_case = f5functions.myf5_create_new_support_case(access_token, inputs)
    if new_case.status_code != 201:
        raise SystemExit(f'Failed to create case.\nStatus code: {new_case.status_code} Full response: {new_case.text}')

    print(f'Case creation {new_case.json()["status"]}. {new_case.json()["message"]}')
    print(f'Case ID: {new_case.json()["data"]["caseNumber"]}')
    print(f'Case URL: {new_case.json()["links"][0]["href"]}')


if __name__ == "__main__":
    main()
