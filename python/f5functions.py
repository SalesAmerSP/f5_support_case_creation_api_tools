import requests
import base64
import os
import tqdm 
import urllib3
from urllib3.exceptions import InsecureRequestWarning

# disable insecure warnings
urllib3.disable_warnings(InsecureRequestWarning)

def generate_basic_auth_string():
    if not os.environ.get('IHEALTH_CLIENT_ID') or not os.environ.get('IHEALTH_CLIENT_SECRET'):
        raise Exception('IHEALTH_CLIENT_ID and IHEALTH_CLIENT_SECRET environment variables must be set.')
    client_id = os.environ['IHEALTH_CLIENT_ID']
    client_secret = os.environ['IHEALTH_CLIENT_SECRET']
    basic_auth_string = f'{client_id}:{client_secret}'
    ascii_bytes = basic_auth_string.encode('ascii')
    base64_bytes = base64.b64encode(ascii_bytes)
    return base64_bytes.decode()

def bigip_connectivity_test(_bigip_host, _bigip_username, _bigip_password):
    _api_query = requests.Request()
    _api_query.url = 'https://' + _bigip_host + '/mgmt/tm/sys/ready'
    _api_query.auth = (_bigip_username, _bigip_password)
    _api_query.headers = {'accept': 'application/json'}
    try:
        _api_response = requests.get(_api_query.url, auth=_api_query.auth, headers=_api_query.headers)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)
    return _api_response

def bigip_generate_qkview(_bigip_host, _bigip_username, _bigip_password, _qkview_filename, _no_truncate=False):
    if _no_truncate:
        _api_query = requests.Request()
        _api_query.url = 'https://' + _bigip_host + '/mgmt/tm/util/qkview'
        _api_query.auth = (_bigip_username, _bigip_password)
        _api_query.headers = {'content-type': 'application/json'}
        _api_query.data = {'command': 'run', 'utilCmdArgs': f'-s0 -f {_qkview_filename}'}
        try:
            _api_response = requests.post(_api_query.url, auth=_api_query.auth, headers=_api_query.headers, json=_api_query.data)
        except requests.exceptions.RequestException as e:
            raise SystemExit(e)
        return _api_response                
    elif _no_truncate == False:        
        _api_query = requests.Request()
        _api_query.url = 'https://' + _bigip_host + '/mgmt/cm/autodeploy/qkview'
        _api_query.auth = (_bigip_username, _bigip_password)
        _api_query.headers = {'content-type': 'application/json'}
        _api_query.data = {'name': _qkview_filename}
        try:
            _api_response = requests.post(_api_query.url, auth=_api_query.auth, headers=_api_query.headers, json=_api_query.data)
        except requests.exceptions.RequestException as e:
            raise SystemExit(e)
        return _api_response
    else:
        raise Exception('no_truncate must be True or False')


def bigip_list_qkviews(_bigip_host, _bigip_username, _bigip_password):
    _api_query = requests.Request()
    _api_query.url = 'https://' + _bigip_host + '/mgmt/cm/autodeploy/qkview/'
    _api_query.auth = (_bigip_username, _bigip_password)
    _api_query.headers = {'accept': 'application/json'}
    try:
        _api_response = requests.get(_api_query.url, auth=_api_query.auth, headers=_api_query.headers)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)
    return _api_response

def bigip_query_qkview_task(_bigip_host, _bigip_username, _bigip_password, _qkview_task_id):
    _api_query = requests.Request()
    _api_query.url = 'https://' + _bigip_host + '/mgmt/cm/autodeploy/qkview/' + _qkview_task_id
    _api_query.auth = (_bigip_username, _bigip_password)
    _api_query.headers = {'accept': 'application/json'}
    try:
        _api_response = requests.get(_api_query.url, auth=_api_query.auth, headers=_api_query.headers)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)
    return _api_response

def bigip_download_qkview(_bigip_host, _bigip_username, _bigip_password, _qkview_filename, _local_filename=None):
    _api_query = requests.Request()
    _api_query.url = 'https://' + _bigip_host + '/mgmt/cm/autodeploy/qkview-downloads/' + _qkview_filename
    _api_query.auth = (_bigip_username, _bigip_password)
    _api_query.headers = {'Content-type': 'application/octet-stream'}
    _output_filename = os.path.basename(_qkview_filename) if _local_filename is None else os.path.basename(_local_filename)
    _pbar = None
    with open(_output_filename, 'wb') as f:
        _download_chunk_size = 512 * 1024
        _download_start = 0
        _download_end = _download_chunk_size - 1
        _download_size = 0
        _download_current_bytes = 0

        while True:
            _content_range = '%s-%s/%s' % (_download_start, _download_end, _download_size)
            _api_query.headers['Content-Range'] = _content_range
            
            _api_response = requests.get(_api_query.url, auth=_api_query.auth, headers=_api_query.headers, verify=False, stream=True)
            
            if _api_response.status_code == 200:
                # If the size is zero, then this is the first time through the
                # loop and we don't want to write data because we haven't yet
                # figured out the total size of the file.
                if _download_size > 0:
                    # Update progress bar with current chunk
                    if _pbar:
                        _pbar.update(min(_download_chunk_size, _download_size - _download_current_bytes + 1))
                    
                    _download_current_bytes += _download_chunk_size
                    for chunk in _api_response.iter_content(_download_chunk_size):
                        f.write(chunk)
                
                # Once we've downloaded the entire file, we can break out of
                # the loop
                if _download_end == _download_size:
                    break
            
            crange = _api_response.headers['Content-Range']
            
            # Determine the total number of bytes to read
            if _download_size == 0:
                _download_size = int(crange.split('/')[-1]) - 1
                
                # Initialize progress bar now that we know the file size
                _pbar = tqdm.tqdm(
                    total=_download_size + 1,  # +1 because size is 0-indexed
                    unit='B',
                    unit_scale=True,
                    desc=os.path.basename(_output_filename)
                )
                
                # If the file is smaller than the chunk size, BIG-IP will
                # return an HTTP 400. So adjust the chunk_size down to the
                # total file size...
                if _download_chunk_size > _download_size:
                    _download_end = _download_size
                # ...and pass on the rest of the code
                continue
            
            _download_start += _download_chunk_size
            if (_download_current_bytes + _download_chunk_size) > _download_size:
                _download_end = _download_size
            else:
                _download_end = _download_start + _download_chunk_size - 1
    
    # Close progress bar
    if _pbar:
        _pbar.close()

def bigip_delete_qkview(_bigip_host, _bigip_username, _bigip_password, _qkview_filename):
    _qkview_list = bigip_list_qkviews(_bigip_host, _bigip_username, _bigip_password)
    for _current_qkview in _qkview_list.json()['items']:
        if _current_qkview['name'] == _qkview_filename:
            _qkview_id = _current_qkview['id']
            print(f'Found QKview {_current_qkview["name"]} with ID {_current_qkview["id"]}')
            _api_query = requests.Request()
            _api_query.url = 'https://' + _bigip_host + '/mgmt/cm/autodeploy/qkview/' + _qkview_id
            _api_query.auth = (_bigip_username, _bigip_password)    
            _api_query.headers = {'accept': 'application/json'}
            try:
                _api_response = requests.delete(_api_query.url, auth=_api_query.auth, headers=_api_query.headers)
            except requests.exceptions.RequestException as e:
                raise SystemExit(e)
            return _api_response
    raise SystemExit(f'QKview {_qkview_filename} not found on BIG-IP {_bigip_host}')

def myf5_retrieve_access_token(_support_app_id, _client_id, _client_secret, scope='myf5_scope'):
    _api_query = requests.Request()
    _api_query.url = f'https://identity.account.f5.com/oauth2/{_support_app_id}/v1/token'
    _api_query.auth = (_client_id, _client_secret)
    _api_query.headers = {'Content-type': 'application/x-www-form-urlencoded'}
    _api_query.data = {'grant_type': 'client_credentials', 'scope': scope}
    try:
        _api_response = requests.post(_api_query.url, auth=_api_query.auth, data=_api_query.data, headers=_api_query.headers)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)    
    return _api_response

def myf5_list_support_cases(_access_token, _support_api_fqdn='support.apis.f5.com', _api_k_value='UKKD3Vxv7NHrM3QmYk8Fk2mZnLtljAKX'):
    _api_query = requests.Request()
    _api_query.url = 'https://' + _support_api_fqdn + '/case-management/v1/cases' + '?type=ALL_CASES' + '&k=' + _api_k_value
    _api_query.headers = {'accept': 'application/json', 'Authorization': 'Bearer ' + _access_token}
    try:
        _api_response = requests.get(_api_query.url, auth=_api_query.auth, headers=_api_query.headers)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)
    return _api_response

def myf5_create_new_support_case(_access_token, _json_payload, _support_api_fqdn='support.apis.f5.com', _api_k_value='UKKD3Vxv7NHrM3QmYk8Fk2mZnLtljAKX'):
    _api_request = requests.Request()
    _api_request.url = 'https://' + _support_api_fqdn + '/case-management/v1/cases' + '?k=' + _api_k_value
    _api_request.headers = {'content-type': 'application/json', 'accept': 'application/json', 'Authorization': 'Bearer ' + _access_token}
    try:
        _api_response = requests.post(_api_request.url, auth=_api_request.auth, headers=_api_request.headers, json=_json_payload)
    except Exception as e:
        raise SystemExit(e)
    return _api_response

def myf5_add_comments_to_existing_support_case(_access_token, _case_number, _comments, _support_api_fqdn='support.apis.f5.com', _api_k_value='UKKD3Vxv7NHrM3QmYk8Fk2mZnLtljAKX'):
    _api_request = requests.Request()
    _api_request.url = 'https://' + _support_api_fqdn + '/case-management/v1/cases/' + f'{_case_number}' + '?k=' + _api_k_value
    _api_request.headers = {'content-type': 'application/json', 'accept': 'application/json', 'Authorization': 'Bearer ' + _access_token}
    _json_payload = {'comments': f'{_comments}'}
    try:
        _api_response = requests.patch(_api_request.url, auth=_api_request.auth, headers=_api_request.headers, json=_json_payload)
    except Exception as e:
        raise SystemExit(e)
    return _api_response

def myf5_retrieve_case_creation_metadata(_access_token, _support_api_fqdn='support.apis.f5.com', _api_k_value='UKKD3Vxv7NHrM3QmYk8Fk2mZnLtljAKX'):
    _api_query = requests.Request()
    _api_query.url = 'https://' + _support_api_fqdn + '/case-management/v1/cases/metadata' + '?k=' + _api_k_value
    _api_query.headers = {'accept': 'application/json', 'Authorization': 'Bearer ' + _access_token}
    try:
        _api_response = requests.get(_api_query.url, auth=_api_query.auth, headers=_api_query.headers)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)
    return _api_response

def ihealth_list_qkview_ids(_access_token, _ihealth_api_fqdn='ihealth2-api.f5.com'):
    _api_query = requests.Request()
    _api_query.url = 'https://' + _ihealth_api_fqdn + '/qkview-analyzer/api/qkviews/'
    _api_query.headers = {'accept': 'application/vnd.f5.ihealth.api.v1.0+json', 'Authorization': 'Bearer ' + _access_token}
    try:
        _api_response = requests.get(_api_query.url, auth=_api_query.auth, headers=_api_query.headers)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)
    return _api_response

def ihealth_show_qkview_metadata(_access_token, _qkview_id, _ihealth_api_fqdn='ihealth2-api.f5.com'):
    _api_query = requests.Request()
    _api_query.url = 'https://' + _ihealth_api_fqdn + '/qkview-analyzer/api/qkviews/' + str(_qkview_id)
    _api_query.headers = {'accept': 'application/vnd.f5.ihealth.api.v1.0+json', 'Authorization': 'Bearer ' + _access_token}
    try:
        _api_response = requests.get(_api_query.url, auth=_api_query.auth, headers=_api_query.headers)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)
    return _api_response

def ihealth_upload_qkview(_access_token, _qkview_filename, _support_case_number='', _ihealth_api_fqdn='ihealth2-api.f5.com'):
    _api_request = requests.Request()
    _api_request.url = 'https://' + _ihealth_api_fqdn + '/qkview-analyzer/api/qkviews'
    _api_request.headers = {
        'Authorization': f'Bearer {_access_token}', 
        'Accept': 'application/vnd.f5.ihealth.api', 
        'User-Agent': 'MyGreatiHealthClient'
        }
    # ensure that file exists
    if not os.path.isfile(_qkview_filename):
        raise SystemExit(f'File {_qkview_filename} does not exist.')
    # upload the file to iHealth
    with open(_qkview_filename, 'rb') as f:
        _file_size = os.path.getsize(_qkview_filename)
        with open(_qkview_filename, 'rb') as f:
            _api_request.params = {
                'visible_in_gui': 'true',
                'share_with_case_owner': 'true',
                'description': 'uploaded via automation'
            }
            # add support case number, if provided
            if _support_case_number:
                _api_request.params['f5_support_case'] = _support_case_number
            # add the file
            _api_request.files = {
                'qkview': (os.path.basename(_qkview_filename), f)
            }
            # send the request
            _api_response = requests.post(
                _api_request.url,
                files=_api_request.files,
                headers=_api_request.headers,
                params=_api_request.params
            )
    return _api_response

