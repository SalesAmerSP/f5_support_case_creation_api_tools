import argparse
import f5functions

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--client-id', help='Support API Key', required=True)
    parser.add_argument('--client-secret', help='Support API Secret', required=True)
    parser.add_argument('--filename', help='QKview filename', required=True)   
    parser.add_argument('--support-case', type=str, help='Support case number', required=False, default=None)
    parser.add_argument('--app-id', help='Advanced Users Only - Support App ID', required=False, default='ausp95ykc80HOU7SQ357')
    return parser.parse_args()

def main():
    # Generate access token
    api_token_auth_response = f5functions.myf5_retrieve_access_token(parse_args().app_id, parse_args().client_id, parse_args().client_secret, scope='ihealth')
    if api_token_auth_response.status_code != 200:
        raise SystemExit(f'Failed to retrieve API Token.\nStatus code: {api_token_auth_response.status_code} Full response: {api_token_auth_response.text}')
    else:
        print(f'Authentication successful.')

    # Upload QKview
    qkview_upload = f5functions.ihealth_upload_qkview(api_token_auth_response.json()["access_token"], parse_args().filename, parse_args().support_case)
    print(qkview_upload.status_code)
    print(qkview_upload.text)

if __name__ == "__main__":
    main()
