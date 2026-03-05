import argparse
import logging
import os
import requests
import tqdm
import urllib3
from urllib3.exceptions import InsecureRequestWarning

# Constants
MYF5_APP_ID = 'aus19gt5bu0jGw9Fi358'
IHEALTH_APP_ID = 'ausp95ykc80HOU7SQ357'
MYF5_API_K_VALUE = 'UKKD3Vxv7NHrM3QmYk8Fk2mZnLtljAKX'
MYF5_API_FQDN = 'support.apis.f5.com'
IHEALTH_API_FQDN = 'ihealth2-api.f5.com'

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared argument parsers
# ---------------------------------------------------------------------------

def _bigip_base_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, help="BIG-IP hostname", required=True)
    parser.add_argument("--username", type=str, help="BIG-IP username", required=False, default="admin")
    parser.add_argument("--password", type=str, help="BIG-IP password", required=True)
    parser.add_argument("--no-ssl-verify", action="store_true", help="Disable SSL certificate verification for BIG-IP", default=False)
    return parser


def bigip_args(*extra_args):
    parser = _bigip_base_parser()
    for arg_args, arg_kwargs in extra_args:
        parser.add_argument(*arg_args, **arg_kwargs)
    return parser.parse_args()


def _ihealth_base_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--client-id', help='Support API Key', required=True)
    parser.add_argument('--client-secret', help='Support API Secret', required=True)
    parser.add_argument('--app-id', help='Advanced Users Only - Support App ID', required=False, default=IHEALTH_APP_ID)
    return parser


def ihealth_args(*extra_args):
    parser = _ihealth_base_parser()
    for arg_args, arg_kwargs in extra_args:
        parser.add_argument(*arg_args, **arg_kwargs)
    return parser.parse_args()


def _myf5_base_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--client-id', help='Support API Key', required=True)
    parser.add_argument('--client-secret', help='Support API Secret', required=True)
    parser.add_argument('--app-id', type=str, help='Advanced Users Only - overwrite Support App ID', required=False, default=MYF5_APP_ID)
    parser.add_argument('--api-url', help='Advanced Users Only - Support API URL', required=False, default="https://support.f5.com")
    parser.add_argument('--k-value', help='Advanced Users Only - overwrite required API k value', required=False, default=MYF5_API_K_VALUE)
    return parser


def myf5_args(*extra_args):
    parser = _myf5_base_parser()
    for arg_args, arg_kwargs in extra_args:
        parser.add_argument(*arg_args, **arg_kwargs)
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

def myf5_authenticate(app_id, client_id, client_secret, scope='myf5_scope'):
    response = myf5_retrieve_access_token(app_id, client_id, client_secret, scope=scope)
    if response.status_code != 200:
        raise SystemExit(f'Failed to retrieve API Token.\nStatus code: {response.status_code} Full response: {response.text}')
    print('Authentication successful.')
    return response.json()["access_token"]


# ---------------------------------------------------------------------------
# BIG-IP API functions
# ---------------------------------------------------------------------------

def _bigip_url(host, path):
    return f'https://{host}{path}'


def _bigip_request(method, host, path, username, password, verify=True, **kwargs):
    url = _bigip_url(host, path)
    if not verify:
        urllib3.disable_warnings(InsecureRequestWarning)
    try:
        return method(url, auth=(username, password), verify=verify, **kwargs)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)


def bigip_connectivity_test(host, username, password, verify=True):
    return _bigip_request(
        requests.get, host, '/mgmt/tm/sys/ready',
        username, password, verify=verify,
        headers={'accept': 'application/json'}
    )


def bigip_generate_qkview(host, username, password, filename, no_truncate=False, verify=True):
    if no_truncate:
        return _bigip_request(
            requests.post, host, '/mgmt/tm/util/qkview',
            username, password, verify=verify,
            headers={'content-type': 'application/json'},
            json={'command': 'run', 'utilCmdArgs': f'-s0 -f {filename}'}
        )
    else:
        return _bigip_request(
            requests.post, host, '/mgmt/cm/autodeploy/qkview',
            username, password, verify=verify,
            headers={'content-type': 'application/json'},
            json={'name': filename}
        )


def bigip_list_qkviews(host, username, password, verify=True):
    return _bigip_request(
        requests.get, host, '/mgmt/cm/autodeploy/qkview/',
        username, password, verify=verify,
        headers={'accept': 'application/json'}
    )


def bigip_query_qkview_task(host, username, password, task_id, verify=True):
    return _bigip_request(
        requests.get, host, f'/mgmt/cm/autodeploy/qkview/{task_id}',
        username, password, verify=verify,
        headers={'accept': 'application/json'}
    )


def bigip_download_qkview(host, username, password, filename, local_filename=None, verify=True):
    url = _bigip_url(host, f'/mgmt/cm/autodeploy/qkview-downloads/{filename}')
    if not verify:
        urllib3.disable_warnings(InsecureRequestWarning)
    output_filename = os.path.basename(filename) if local_filename is None else os.path.basename(local_filename)
    pbar = None
    with open(output_filename, 'wb') as f:
        chunk_size = 512 * 1024
        start = 0
        end = chunk_size - 1
        total_size = 0
        current_bytes = 0

        while True:
            content_range = f'{start}-{end}/{total_size}'
            headers = {
                'Content-type': 'application/octet-stream',
                'Content-Range': content_range
            }
            try:
                response = requests.get(url, auth=(username, password), headers=headers, verify=verify, stream=True)
            except requests.exceptions.RequestException as e:
                raise SystemExit(e)

            if response.status_code == 200:
                if total_size > 0:
                    if pbar:
                        pbar.update(min(chunk_size, total_size - current_bytes + 1))
                    current_bytes += chunk_size
                    for chunk in response.iter_content(chunk_size):
                        f.write(chunk)
                if end == total_size:
                    break

            if 'Content-Range' not in response.headers:
                raise SystemExit(f'Unexpected response (status {response.status_code}): missing Content-Range header')

            crange = response.headers['Content-Range']

            if total_size == 0:
                total_size = int(crange.split('/')[-1]) - 1
                pbar = tqdm.tqdm(
                    total=total_size + 1,
                    unit='B',
                    unit_scale=True,
                    desc=os.path.basename(output_filename)
                )
                if chunk_size > total_size:
                    end = total_size
                continue

            start += chunk_size
            if (current_bytes + chunk_size) > total_size:
                end = total_size
            else:
                end = start + chunk_size - 1

    if pbar:
        pbar.close()


def bigip_delete_qkview(host, username, password, filename, verify=True):
    qkview_list = bigip_list_qkviews(host, username, password, verify=verify)
    if qkview_list.status_code != 200:
        raise SystemExit(f'Failed to list QKviews.\nStatus code: {qkview_list.status_code} Full response: {qkview_list.text}')
    for current_qkview in qkview_list.json().get('items', []):
        if current_qkview['name'] == filename:
            qkview_id = current_qkview['id']
            print(f'Found QKview {current_qkview["name"]} with ID {qkview_id}')
            return _bigip_request(
                requests.delete, host, f'/mgmt/cm/autodeploy/qkview/{qkview_id}',
                username, password, verify=verify,
                headers={'accept': 'application/json'}
            )
    raise SystemExit(f'QKview {filename} not found on BIG-IP {host}')


# ---------------------------------------------------------------------------
# MyF5 API functions
# ---------------------------------------------------------------------------

def myf5_retrieve_access_token(app_id, client_id, client_secret, scope='myf5_scope'):
    url = f'https://identity.account.f5.com/oauth2/{app_id}/v1/token'
    try:
        return requests.post(
            url,
            auth=(client_id, client_secret),
            data={'grant_type': 'client_credentials', 'scope': scope},
            headers={'Content-type': 'application/x-www-form-urlencoded'}
        )
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)


def myf5_list_support_cases(access_token, api_fqdn=MYF5_API_FQDN, k_value=MYF5_API_K_VALUE):
    url = f'https://{api_fqdn}/case-management/v1/cases?type=ALL_CASES&k={k_value}'
    try:
        return requests.get(url, headers={'accept': 'application/json', 'Authorization': f'Bearer {access_token}'})
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)


def myf5_create_new_support_case(access_token, json_payload, api_fqdn=MYF5_API_FQDN, k_value=MYF5_API_K_VALUE):
    url = f'https://{api_fqdn}/case-management/v1/cases?k={k_value}'
    try:
        return requests.post(
            url,
            headers={'content-type': 'application/json', 'accept': 'application/json', 'Authorization': f'Bearer {access_token}'},
            json=json_payload
        )
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)


def myf5_add_comments_to_existing_support_case(access_token, case_number, comments, api_fqdn=MYF5_API_FQDN, k_value=MYF5_API_K_VALUE):
    url = f'https://{api_fqdn}/case-management/v1/cases/{case_number}?k={k_value}'
    try:
        return requests.patch(
            url,
            headers={'content-type': 'application/json', 'accept': 'application/json', 'Authorization': f'Bearer {access_token}'},
            json={'comments': str(comments)}
        )
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)


def myf5_retrieve_case_creation_metadata(access_token, api_fqdn=MYF5_API_FQDN, k_value=MYF5_API_K_VALUE):
    url = f'https://{api_fqdn}/case-management/v1/cases/metadata?k={k_value}'
    try:
        return requests.get(url, headers={'accept': 'application/json', 'Authorization': f'Bearer {access_token}'})
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)


# ---------------------------------------------------------------------------
# iHealth API functions
# ---------------------------------------------------------------------------

def ihealth_list_qkview_ids(access_token, api_fqdn=IHEALTH_API_FQDN):
    url = f'https://{api_fqdn}/qkview-analyzer/api/qkviews/'
    try:
        return requests.get(url, headers={
            'accept': 'application/vnd.f5.ihealth.api.v1.0+json',
            'Authorization': f'Bearer {access_token}'
        })
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)


def ihealth_show_qkview_metadata(access_token, qkview_id, api_fqdn=IHEALTH_API_FQDN):
    url = f'https://{api_fqdn}/qkview-analyzer/api/qkviews/{qkview_id}'
    try:
        return requests.get(url, headers={
            'accept': 'application/vnd.f5.ihealth.api.v1.0+json',
            'Authorization': f'Bearer {access_token}'
        })
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)


def ihealth_upload_qkview(access_token, filename, support_case_number='', api_fqdn=IHEALTH_API_FQDN):
    url = f'https://{api_fqdn}/qkview-analyzer/api/qkviews'
    if not os.path.isfile(filename):
        raise SystemExit(f'File {filename} does not exist.')
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/vnd.f5.ihealth.api',
        'User-Agent': 'MyGreatiHealthClient'
    }
    params = {
        'visible_in_gui': 'true',
        'share_with_case_owner': 'true',
        'description': 'uploaded via automation'
    }
    if support_case_number:
        params['f5_support_case'] = support_case_number
    with open(filename, 'rb') as f:
        return requests.post(
            url,
            files={'qkview': (os.path.basename(filename), f)},
            headers=headers,
            params=params
        )
