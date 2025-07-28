#!/usr/bin/env python

import f5functions
import argparse

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, help="BIG-IP hostname", required=True, default="")
    parser.add_argument("--username", type=str, help="BIG-IP username", required=False, default="admin")
    parser.add_argument("--password", type=str, help="BIG-IP password", required=True, default="")
    parser.add_argument("--filename", type=str, help="QKView file name", required=True)
    return parser.parse_args()

def main():
    print(f'Downloading QKview on BIG-IP {parse_args().host}')
    qkview_download = f5functions.bigip_download_qkview(parse_args().host, parse_args().username, parse_args().password, parse_args().filename)
    
if __name__ == "__main__":
    main()