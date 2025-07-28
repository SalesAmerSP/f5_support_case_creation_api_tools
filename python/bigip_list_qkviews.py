import f5functions
import argparse
from datetime import datetime

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, help="BIG-IP hostname", required=True, default="")
    parser.add_argument("--username", type=str, help="BIG-IP username", required=False, default="admin")
    parser.add_argument("--password", type=str, help="BIG-IP password", required=True, default="")
    parser.add_argument("--filename", type=str, help="QKView filename", required=False)
    parser.add_argument("--skip-wait", action="store_true", help="Skip the wait for QKView to complete", required=False)
    parser.add_argument("--wait-interval", type=int, help="Wait interval in seconds", required=False, default=10)
    return parser.parse_args()

def main():
    print(f'Retrieving list of QKviews on BIG-IP {parse_args().host}\n')
    qkview_list = f5functions.bigip_list_qkviews(parse_args().host, parse_args().username, parse_args().password)
    if qkview_list.status_code != 200:
        raise SystemExit(f'Failed to retrieve QKview list.\nStatus code: {qkview_list.status_code} Full response: {qkview_list.text}')
    else:
        for current_qkview in qkview_list.json()["items"]:
            print(f'Name: {current_qkview["name"]}')
            print(f'Status: {current_qkview["status"]}')
            print(f'ID: {current_qkview["id"]}')
            print(f'Last Update: {datetime.fromtimestamp(current_qkview["lastUpdateMicros"] / 1000000)}')
            try:
                print(f'URI: {current_qkview["qkviewUri"].replace("https://localhost/", f"https://{parse_args().host}/")}\n')
            except KeyError as e:
                print(f'URI: {current_qkview["selfLink"].replace("https://localhost/", f"https://{parse_args().host}/")}\n')
        print(f'Total Qkviews found: {len(qkview_list.json()["items"])}')
        
if __name__ == "__main__":
    main()