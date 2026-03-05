#!/usr/bin/env python

import f5functions


def main():
    args = f5functions.bigip_args(
        (["--filename"], {"type": str, "help": "QKView filename", "required": True}),
    )
    verify = not args.no_ssl_verify

    print(f'Deleting QKview on BIG-IP {args.host}')
    qkview_deletion = f5functions.bigip_delete_qkview(args.host, args.username, args.password, args.filename, verify=verify)
    if qkview_deletion.status_code == 200:
        print('QKview deletion successful.')


if __name__ == "__main__":
    main()
