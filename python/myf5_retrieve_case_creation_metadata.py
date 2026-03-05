#!/usr/bin/env python

import f5functions
import json


def main():
    args = f5functions.myf5_args(
        (["--output-file"], {"help": "Output file", "required": False, "default": None}),
        (["--output-to-stdout"], {"action": "store_true", "help": "Output to stdout", "required": False, "default": False}),
    )
    access_token = f5functions.myf5_authenticate(args.app_id, args.client_id, args.client_secret)

    # Retrieve case creation metadata
    case_creation_metadata = f5functions.myf5_retrieve_case_creation_metadata(access_token)
    if case_creation_metadata.status_code != 200:
        raise SystemExit(f'Failed to retrieve case creation metadata.\nStatus code: {case_creation_metadata.status_code} Full response: {case_creation_metadata.text}')

    if args.output_to_stdout:
        print(case_creation_metadata.json())
    else:
        print('Skipping output to stdout; use --output-to-stdout to output to stdout')

    if args.output_file is not None:
        with open(args.output_file, 'w') as f:
            json.dump(case_creation_metadata.json(), f)
    else:
        print('Skipping output to file; use --output-file to output to file')


if __name__ == "__main__":
    main()
