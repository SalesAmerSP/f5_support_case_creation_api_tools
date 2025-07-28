import argparse
import f5functions
import datetime

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--client-id', help='Support API Key', required=True)
    parser.add_argument('--client-secret', help='Support API Secret', required=True)
    parser.add_argument('--app-id', help='Advanced Users Only - Support App ID', required=False, default='ausp95ykc80HOU7SQ357')
    return parser.parse_args()

def main():
    # Generate access token
    api_token_auth_response = f5functions.myf5_retrieve_access_token(parse_args().app_id, parse_args().client_id, parse_args().client_secret, scope='ihealth')
    if api_token_auth_response.status_code != 200:
        raise SystemExit(f'Failed to retrieve API Token.\nStatus code: {api_token_auth_response.status_code} Full response: {api_token_auth_response.text}')
    else:
        print(f'Authentication successful.')

    qkview_id_list = f5functions.ihealth_list_qkview_ids(api_token_auth_response.json()["access_token"])
    if qkview_id_list.status_code != 200:
        raise SystemExit(f'Failed to retrieve QKview IDs.\nStatus code: {qkview_id_list.status_code} Full response: {qkview_id_list.text}')
    else:
        for qkview_id in qkview_id_list.json()["id"]:
            qkview_metadata = f5functions.ihealth_show_qkview_metadata(api_token_auth_response.json()["access_token"], qkview_id)
            if qkview_metadata.status_code != 200:
                raise SystemExit(f'Failed to retrieve QKview metadata.\nStatus code: {qkview_metadata.status_code} Full response: {qkview_metadata.text}')
            else:
                print('*********************************************************************************************')
                print(f' Hostname: {qkview_metadata.json()["hostname"]}')
                print(f' Description: {qkview_metadata.json()["description"]}')
                created_date = datetime.datetime.fromtimestamp(qkview_metadata.json()["generation_date"] / 1000).strftime('%Y-%m-%d %H:%M:%S')
                print(f' Created Date: {created_date}')
                print(f' Chassis Serial: {qkview_metadata.json()["chassis_serial"]}')
                print(f' Support Case: {qkview_metadata.json()["f5_support_case"]}')
                print(f' URL: {qkview_metadata.json()['gui_uri']}')
                print('*********************************************************************************************')
        print(f'Total QKview IDs found: {len(qkview_id_list.json()["id"])}')  
                
if __name__ == "__main__":
    main()
