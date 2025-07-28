#!/usr/bin/env python

import f5functions
import argparse
import json

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--client-id', help='Support API Key', required=True)
    parser.add_argument('--client-secret', help='Support API Secret', required=True)
    parser.add_argument('--inputs-file', help='Input file', required=True)
    parser.add_argument('--app-id', type=str, help='Advanced Users Only - overwrite Support App ID', required=False, default='aus19gt5bu0jGw9Fi358')
    parser.add_argument('--api-url', help='Support API URL', required=False, default="https://support.f5.com")
    parser.add_argument('--k-value', help='Advanced Users Only - overwrite required API k value', required=False, default="UKKD3Vxv7NHrM3QmYk8Fk2mZnLtljAKX") 
    return parser.parse_args()

def main():
    # Generate access token
    api_token_auth_response = f5functions.myf5_retrieve_access_token(parse_args().app_id, parse_args().client_id, parse_args().client_secret)
    if api_token_auth_response.status_code != 200:
        raise SystemExit(f'Failed to retrieve API Token.\nStatus code: {api_token_auth_response.status_code} Full response: {api_token_auth_response.text}')
    else:
        print(f'Authentication successful.')

    # Read inputs file
    with open(parse_args().inputs_file, 'r') as f:
        inputs = json.load(f)
        f.close()

    # Confirm with user
    print('The following inputs will be used to create a new case:')
    for key, value in inputs.items():
        print(f'{key}: {value}')

    # Confirm with user
    confirm = input('Is this correct? (y/n): ')
    if confirm != 'y':
        raise SystemExit('Aborting.')
    
    # Create the case
    new_case = f5functions.myf5_create_new_support_case(api_token_auth_response.json()["access_token"], inputs)
    if new_case.status_code != 201:
        raise SystemExit(f'Failed to create case.\nStatus code: {new_case.status_code} Full response: {new_case.text}')
    else:
        print(f'Case creation {new_case.json()["status"]}. {new_case.json()["message"]}')
        print(f'Case ID: {new_case.json()["data"]["caseNumber"]}')
        print(f'Case URL: {new_case.json()["links"][0]["href"]}')

if __name__ == "__main__":
    main()
    