import f5functions


def main():
    args = f5functions.bigip_args()
    verify = not args.no_ssl_verify
    print(f'Connecting to BIG-IP {args.host}')
    response = f5functions.bigip_connectivity_test(args.host, args.username, args.password, verify=verify)
    print(f'Response status code: {response.status_code}')
    print(f'Response text: {response.text}')


if __name__ == "__main__":
    main()
