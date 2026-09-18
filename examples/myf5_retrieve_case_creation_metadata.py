#!/usr/bin/env python3
"""Retrieve and display or save MyF5 case creation schema metadata.

Outputs valid product families, products, versions, severities, and contact methods
required for programmatically creating support cases.

Usage:
    python3 examples/myf5_retrieve_case_creation_metadata.py --client-id <id> --client-secret <secret> \
        [--output-file metadata.json] [--output-to-stdout] [--auth-fqdn idp.identity.f5.com]
"""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
try:
    from qkviewmgr import f5functions
except ImportError:
    import f5functions


def main():
    """Retrieve case creation metadata schema and output to file or stdout."""
    args = f5functions.myf5_args(
        (["--output-file"], {"help": "Path to write metadata JSON file", "required": False, "default": None}),
        (["--output-to-stdout"], {"action": "store_true", "help": "Print JSON metadata to stdout", "required": False, "default": False}),
    )
    access_token = f5functions.myf5_authenticate(
        args.app_id, args.client_id, args.client_secret,
        scope='myf5_scope', auth_url=args.auth_url, auth_fqdn=args.auth_fqdn
    )

    # Retrieve case creation metadata
    print('Retrieving case creation metadata from MyF5...')
    case_creation_metadata = f5functions.myf5_retrieve_case_creation_metadata(
        access_token, api_fqdn=args.api_url, k_value=args.k_value
    )
    if case_creation_metadata.status_code != 200:
        raise SystemExit(f'Failed to retrieve case creation metadata.\nStatus code: {case_creation_metadata.status_code} Full response: {case_creation_metadata.text}')

    if args.output_to_stdout:
        print(json.dumps(case_creation_metadata.json(), indent=2))
    else:
        print('Skipping output to stdout; use --output-to-stdout to print JSON')

    if args.output_file is not None:
        with open(args.output_file, 'w') as f:
            json.dump(case_creation_metadata.json(), f, indent=2)
        print(f'Metadata successfully written to {args.output_file}')
    else:
        print('Skipping output to file; use --output-file to save to a file')


if __name__ == "__main__":
    main()
