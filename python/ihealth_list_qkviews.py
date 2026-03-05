import f5functions
import datetime


def main():
    args = f5functions.ihealth_args()
    access_token = f5functions.myf5_authenticate(args.app_id, args.client_id, args.client_secret, scope='ihealth')

    qkview_id_list = f5functions.ihealth_list_qkview_ids(access_token)
    if qkview_id_list.status_code != 200:
        raise SystemExit(f'Failed to retrieve QKview IDs.\nStatus code: {qkview_id_list.status_code} Full response: {qkview_id_list.text}')

    for qkview_id in qkview_id_list.json()["id"]:
        qkview_metadata = f5functions.ihealth_show_qkview_metadata(access_token, qkview_id)
        if qkview_metadata.status_code != 200:
            raise SystemExit(f'Failed to retrieve QKview metadata.\nStatus code: {qkview_metadata.status_code} Full response: {qkview_metadata.text}')
        data = qkview_metadata.json()
        print('*********************************************************************************************')
        print(f' Hostname: {data.get("hostname", "N/A")}')
        print(f' Description: {data.get("description", "N/A")}')
        created_date = datetime.datetime.fromtimestamp(data["generation_date"] / 1000).strftime('%Y-%m-%d %H:%M:%S')
        print(f' Created Date: {created_date}')
        print(f' Chassis Serial: {data.get("chassis_serial", "N/A")}')
        print(f' Support Case: {data.get("f5_support_case", "N/A")}')
        print(f' URL: {data.get("gui_uri", "N/A")}')
        print('*********************************************************************************************')
    print(f'Total QKview IDs found: {len(qkview_id_list.json()["id"])}')


if __name__ == "__main__":
    main()
