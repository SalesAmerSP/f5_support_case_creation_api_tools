import f5functions


def main():
    args = f5functions.ihealth_args(
        (["--filename"], {"help": "QKview filename", "required": True}),
        (["--support-case"], {"type": str, "help": "Support case number", "required": False, "default": None}),
    )
    access_token = f5functions.myf5_authenticate(args.app_id, args.client_id, args.client_secret, scope='ihealth')

    qkview_upload = f5functions.ihealth_upload_qkview(access_token, args.filename, args.support_case or '')
    print(f'Status code: {qkview_upload.status_code}')
    print(qkview_upload.text)


if __name__ == "__main__":
    main()
