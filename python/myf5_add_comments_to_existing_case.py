#!/usr/bin/env python

import f5functions
import argparse

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--client-id', help='Support API Key', required=True)
    parser.add_argument('--client-secret', help='Support API Secret', required=True)
    parser.add_argument('--case-number', help='F5 Support Case Number', required=True)
    parser.add_argument('--comment-text-file', help='File containing notes to attach', required=True)
    parser.add_argument('--app-id', type=str, help='Advanced Users Only - overwrite Support App ID', required=False, default='aus19gt5bu0jGw9Fi358')
    parser.add_argument('--api-url', help='Advanced Users Only -Support API URL', required=False, default="https://support.f5.com")
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
    with open(parse_args().comment_text_file, 'r') as f:
        comments = f.read()
        f.close()

    # Confirm with user
    print(f'The following comments will be added to case {parse_args().case_number}:')
    print(f'{comments}  ')

    # Confirm with user
    confirm = input('Is this correct? (y/n): ')
    if confirm != 'y' and confirm != 'Y':
        raise SystemExit('Aborting.')
    else:
        print(f'Adding comments to case {parse_args().case_number}')
    
    # Update the case
    updated_case = f5functions.myf5_add_comments_to_existing_support_case(api_token_auth_response.json()["access_token"], parse_args().case_number, comments)
    if updated_case.status_code != 200:
        raise SystemExit(f'Failed to update case.\nStatus code: {updated_case.status_code} Full response: {updated_case.text}')
    else:
        print(f'Case update {updated_case.json()["status"]} at {updated_case.json()["data"]["updatedDate"]}. {updated_case.json()["message"]}')
        print(f'Case ID: {updated_case.json()["data"]["caseNumber"]}')
        print(f'Case URL: {updated_case.json()["links"][0]["href"]}')
        print(f'API response: {updated_case.text}')

if __name__ == "__main__":
    main()
    