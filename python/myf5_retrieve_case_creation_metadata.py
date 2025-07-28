#!/usr/bin/env python

import f5functions
import argparse
import json

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--client-id', help='Support API Key', required=True)
    parser.add_argument('--client-secret', help='Support API Secret', required=True)
    parser.add_argument('--output-file', help='Output file', required=False, default=None)
    parser.add_argument('--output-to-stdout', action="store_true", help="Output to stdout", required=False, default=False)
    parser.add_argument('--app-id', type=str, help='Advanced Users Only - overwrite Support App ID', required=False, default='aus19gt5bu0jGw9Fi358')
    parser.add_argument('--api-url', help='Advanced Users Only - overwrite Support API URL', required=False, default="https://support.f5.com")
    parser.add_argument('--k-value', help='Advanced Users Only - overwrite required API k value', required=False, default="UKKD3Vxv7NHrM3QmYk8Fk2mZnLtljAKX") 
    return parser.parse_args()

def main():
    # Generate access token
    api_token_auth_response = f5functions.myf5_retrieve_access_token(parse_args().app_id, parse_args().client_id, parse_args().client_secret)
    if api_token_auth_response.status_code != 200:
        raise SystemExit(f'Failed to retrieve API Token.\nStatus code: {api_token_auth_response.status_code} Full response: {api_token_auth_response.text}')
    else:
        print(f'Authentication successful.')
    
    # Retrieve case creation metadata, which shows the options available for payloads when creating a case
    
    case_creation_metadata = f5functions.myf5_retrieve_case_creation_metadata(api_token_auth_response.json()["access_token"])
    if case_creation_metadata.status_code != 200:
        raise SystemExit(f'Failed to retrieve case creation metadata.\nStatus code: {case_creation_metadata.status_code} Full response: {case_creation_metadata.text}')
    else:
        if parse_args().output_to_stdout:
            print(case_creation_metadata.json())
        else:
            print('Skipping output to stdout; use --output-to-stdout to output to stdout')
        if parse_args().output_file is not None:
            with open(parse_args().output_file, 'w') as f:
                f.write(json.dumps(case_creation_metadata.json()))
                f.close()
        else:
            print('Skipping output to file; use --output-file to output to file')
            
if __name__ == "__main__":
    main()
    