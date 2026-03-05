#!/usr/bin/env python

import f5functions


def main():
    args = f5functions.bigip_args(
        (["--filename"], {"type": str, "help": "QKView file name", "required": True}),
    )
    verify = not args.no_ssl_verify

    print(f'Downloading QKview on BIG-IP {args.host}')
    f5functions.bigip_download_qkview(args.host, args.username, args.password, args.filename, verify=verify)


if __name__ == "__main__":
    main()
