import f5functions
import argparse

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, help="BIG-IP hostname", required=True, default="")
    parser.add_argument("--username", type=str, help="BIG-IP username", required=True, default="")
    parser.add_argument("--password", type=str, help="BIG-IP password", required=True, default="")
    return parser.parse_args()

def main():
    print(f'Connecting to BIG-IP {parse_args().host}')
    connectivity_test_response = f5functions.bigip_connectivity_test(parse_args().host, parse_args().username, parse_args().password)
    print(f'Response status code: {connectivity_test_response.status_code}')
    print(f'Response text: {connectivity_test_response.text}')    
    
if __name__ == "__main__":
    main()