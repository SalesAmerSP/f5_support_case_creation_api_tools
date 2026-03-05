#!/usr/bin/env python

import f5functions


def main():
    args = f5functions.myf5_args()
    f5functions.myf5_authenticate(args.app_id, args.client_id, args.client_secret)


if __name__ == "__main__":
    main()
