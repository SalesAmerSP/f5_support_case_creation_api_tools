#!/usr/bin/env python

import f5functions
import argparse

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--client-id', help='Support API Key', required=True)
    parser.add_argument('--client-secret', help='Support API Secret', required=True)
    parser.add_argument('--app-id', type=str, help='Advanced Users Only - overwrite Support App ID', required=False, default='aus19gt5bu0jGw9Fi358')
    parser.add_argument('--api-url', help='Advanced Users Only - Support API URL', required=False, default="https://support.f5.com")
    parser.add_argument('--k-value', help='Advanced Users Only - overwrite required API k value', required=False, default="UKKD3Vxv7NHrM3QmYk8Fk2mZnLtljAKX") 
    parser.add_argument('--show-closed', action="store_true", help="Show closed cases", required=False, default=False)
    return parser.parse_args()

def main():
    # Generate access token
    api_token_auth_response = f5functions.myf5_retrieve_access_token(parse_args().app_id, parse_args().client_id, parse_args().client_secret)
    if api_token_auth_response.status_code != 200:
        raise SystemExit(f'Failed to retrieve API Token.\nStatus code: {api_token_auth_response.status_code} Full response: {api_token_auth_response.text}')
    else:
        print(f'Authentication successful.')
    
    # List support cases
    support_case_list = f5functions.myf5_list_support_cases(api_token_auth_response.json()["access_token"])
    if support_case_list.status_code != 200:
        raise SystemExit(f'Failed to retrieve support cases.\nStatus code: {support_case_list.status_code} Full response: {support_case_list.text}')
    else:
        print(f'Total cases found: {support_case_list.json()["count"]}')
        for current_case in support_case_list.json()["data"]:
            if not parse_args().show_closed and current_case["status"] == "Closed":
                continue
            print(f'Case: {current_case["caseNumber"]} ({current_case["status"]}) - {current_case["subject"]} (Opened {current_case["dateOpened"]})')

if __name__ == "__main__":
    main()
    