#!/usr/bin/env python3
"""Test connectivity and system readiness to an F5 BIG-IP device via iControl REST.

Usage:
    python3 examples/bigip_connectivity_test.py --host <ip> --username admin --password <pwd> [--no-ssl-verify]
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
try:
    from qkviewmgr import f5functions
except ImportError:
    import f5functions


def main():
    """Execute connectivity check against /mgmt/tm/sys/ready."""
    args = f5functions.bigip_args()
    verify = not args.no_ssl_verify
    print(f'Connecting to BIG-IP {args.host}')
    response = f5functions.bigip_connectivity_test(args.host, args.username, args.password, verify=verify)
    print(f'Response status code: {response.status_code}')
    print(f'Response text: {response.text}')


if __name__ == "__main__":
    main()
