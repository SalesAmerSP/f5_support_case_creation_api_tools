import f5functions
from datetime import datetime


def main():
    args = f5functions.bigip_args()
    verify = not args.no_ssl_verify

    print(f'Retrieving list of QKviews on BIG-IP {args.host}\n')
    qkview_list = f5functions.bigip_list_qkviews(args.host, args.username, args.password, verify=verify)
    if qkview_list.status_code != 200:
        raise SystemExit(f'Failed to retrieve QKview list.\nStatus code: {qkview_list.status_code} Full response: {qkview_list.text}')

    for current_qkview in qkview_list.json()["items"]:
        print(f'Name: {current_qkview["name"]}')
        print(f'Status: {current_qkview["status"]}')
        print(f'ID: {current_qkview["id"]}')
        print(f'Last Update: {datetime.fromtimestamp(current_qkview["lastUpdateMicros"] / 1000000)}')
        try:
            print(f'URI: {current_qkview["qkviewUri"].replace("https://localhost/", f"https://{args.host}/")}\n')
        except KeyError:
            print(f'URI: {current_qkview["selfLink"].replace("https://localhost/", f"https://{args.host}/")}\n')
    print(f'Total Qkviews found: {len(qkview_list.json()["items"])}')


if __name__ == "__main__":
    main()
