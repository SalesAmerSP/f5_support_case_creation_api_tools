import f5functions


def main():
    args = f5functions.ihealth_args()
    access_token = f5functions.myf5_authenticate(args.app_id, args.client_id, args.client_secret, scope='ihealth')

    # Verify we can actually reach the iHealth API
    qkview_id_list = f5functions.ihealth_list_qkview_ids(access_token)
    if qkview_id_list.status_code != 200:
        raise SystemExit(f'Failed to reach iHealth API.\nStatus code: {qkview_id_list.status_code} Full response: {qkview_id_list.text}')
    print('iHealth API connectivity test successful.')


if __name__ == "__main__":
    main()
