import f5functions
import argparse
import time
from datetime import datetime

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, help="BIG-IP hostname", required=True, default="")
    parser.add_argument("--username", type=str, help="BIG-IP username", required=False, default="admin")
    parser.add_argument("--password", type=str, help="BIG-IP password", required=True, default="")
    parser.add_argument("--filename", type=str, help="QKView filename", required=False)
    parser.add_argument("--skip-wait", action="store_true", help="Skip the wait for QKView to complete", required=False)
    parser.add_argument("--wait-interval", type=int, help="Wait interval in seconds", required=False, default=60)
    return parser.parse_args()

def main():
    print(f'Generating QKview on BIG-IP {parse_args().host}')
    qkview_creation = f5functions.bigip_generate_qkview(parse_args().host, parse_args().username, parse_args().password, parse_args().filename)
    if qkview_creation.status_code == 400:
        raise SystemExit(f'Failed to generate QKview.\nError message: {qkview_creation.json()['message']}')
    elif qkview_creation.status_code == 202:
        print('**********************************************************************')
        print(f'QKview Name: {qkview_creation.json()["name"]}')
        print(f'Task ID: {qkview_creation.json()["id"]}')
        print(f'Status: {qkview_creation.json()["status"]}')
        print(f'Last Update: {datetime.fromtimestamp(qkview_creation.json()["lastUpdateMicros"] / 1000000)}')
        print(f'Task URI: {qkview_creation.json()["selfLink"].replace("https://localhost/", f"https://{parse_args().host}/")}')
        print('**********************************************************************')
    else:
        raise SystemExit(f'Failed to generate QKview.')

    if parse_args().skip_wait == False:
        print(f'Polling QKview task on BIG-IP {parse_args().host} every {parse_args().wait_interval} seconds.')
        qkview_task = f5functions.bigip_query_qkview_task(parse_args().host, parse_args().username, parse_args().password, qkview_creation.json()["id"])
        while qkview_task.json()["status"] == "IN_PROGRESS":
            qkview_task = f5functions.bigip_query_qkview_task(parse_args().host, parse_args().username, parse_args().password, qkview_creation.json()["id"])
            time.sleep(parse_args().wait_interval)
            print(f'QKview Status: {qkview_task.json()["status"]} ({datetime.now()})')
        print('**********************************************************************')
        print(f'Name: {qkview_task.json()["name"]}')
        print(f'Task ID: {qkview_task.json()["id"]}')
        print(f'Last Update: {datetime.fromtimestamp(qkview_task.json()["lastUpdateMicros"] / 1000000)}')
        print(f'Qkview URI: {qkview_task.json()["qkviewUri"].replace("https://localhost/", f"https://{parse_args().host}/")}')
        print('**********************************************************************')
    else:
        print(f'The QKview on BIG-IP {parse_args().host} is likely still in progress. You can query the task status by polling the task URI at {qkview_creation.json()["selfLink"].replace("https://localhost/", f"https://{parse_args().host}/")}.')

if __name__ == "__main__":
    main()