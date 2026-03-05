import f5functions
import time
from datetime import datetime


def main():
    args = f5functions.bigip_args(
        (["--filename"], {"type": str, "help": "QKView filename", "required": False}),
        (["--skip-wait"], {"action": "store_true", "help": "Skip the wait for QKView to complete", "required": False}),
        (["--wait-interval"], {"type": int, "help": "Wait interval in seconds", "required": False, "default": 60}),
    )
    verify = not args.no_ssl_verify

    print(f'Generating QKview on BIG-IP {args.host}')
    qkview_creation = f5functions.bigip_generate_qkview(args.host, args.username, args.password, args.filename, verify=verify)
    if qkview_creation.status_code == 400:
        raise SystemExit(f'Failed to generate QKview.\nError message: {qkview_creation.json()["message"]}')
    elif qkview_creation.status_code == 202:
        print('**********************************************************************')
        print(f'QKview Name: {qkview_creation.json()["name"]}')
        print(f'Task ID: {qkview_creation.json()["id"]}')
        print(f'Status: {qkview_creation.json()["status"]}')
        print(f'Last Update: {datetime.fromtimestamp(qkview_creation.json()["lastUpdateMicros"] / 1000000)}')
        print(f'Task URI: {qkview_creation.json()["selfLink"].replace("https://localhost/", f"https://{args.host}/")}')
        print('**********************************************************************')
    else:
        raise SystemExit('Failed to generate QKview.')

    if not args.skip_wait:
        print(f'Polling QKview task on BIG-IP {args.host} every {args.wait_interval} seconds.')
        task_id = qkview_creation.json()["id"]
        qkview_task = f5functions.bigip_query_qkview_task(args.host, args.username, args.password, task_id, verify=verify)
        while qkview_task.json()["status"] == "IN_PROGRESS":
            time.sleep(args.wait_interval)
            qkview_task = f5functions.bigip_query_qkview_task(args.host, args.username, args.password, task_id, verify=verify)
            print(f'QKview Status: {qkview_task.json()["status"]} ({datetime.now()})')
        print('**********************************************************************')
        print(f'Name: {qkview_task.json()["name"]}')
        print(f'Task ID: {qkview_task.json()["id"]}')
        print(f'Last Update: {datetime.fromtimestamp(qkview_task.json()["lastUpdateMicros"] / 1000000)}')
        print(f'Qkview URI: {qkview_task.json()["qkviewUri"].replace("https://localhost/", f"https://{args.host}/")}')
        print('**********************************************************************')
    else:
        print(f'The QKview on BIG-IP {args.host} is likely still in progress. You can query the task status by polling the task URI at {qkview_creation.json()["selfLink"].replace("https://localhost/", f"https://{args.host}/")}.')


if __name__ == "__main__":
    main()
