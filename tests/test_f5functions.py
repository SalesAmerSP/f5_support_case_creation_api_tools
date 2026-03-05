import os
import sys
import pytest
from unittest.mock import patch, MagicMock, mock_open

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))
import f5functions


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

def test_constants_defined():
    assert f5functions.MYF5_APP_ID == 'aus19gt5bu0jGw9Fi358'
    assert f5functions.IHEALTH_APP_ID == 'ausp95ykc80HOU7SQ357'
    assert f5functions.MYF5_API_K_VALUE == 'UKKD3Vxv7NHrM3QmYk8Fk2mZnLtljAKX'
    assert f5functions.MYF5_API_FQDN == 'support.apis.f5.com'
    assert f5functions.IHEALTH_API_FQDN == 'ihealth2-api.f5.com'


# ---------------------------------------------------------------------------
# Shared argument parsers
# ---------------------------------------------------------------------------

def test_bigip_args_defaults():
    with patch('sys.argv', ['prog', '--host', 'bigip1.example.com', '--password', 'secret']):
        args = f5functions.bigip_args()
        assert args.host == 'bigip1.example.com'
        assert args.username == 'admin'
        assert args.password == 'secret'
        assert args.no_ssl_verify is False


def test_bigip_args_no_ssl_verify():
    with patch('sys.argv', ['prog', '--host', 'bigip1', '--password', 'pw', '--no-ssl-verify']):
        args = f5functions.bigip_args()
        assert args.no_ssl_verify is True


def test_bigip_args_extra_args():
    with patch('sys.argv', ['prog', '--host', 'h', '--password', 'p', '--filename', 'test.qkview']):
        args = f5functions.bigip_args(
            (["--filename"], {"type": str, "help": "file", "required": True}),
        )
        assert args.filename == 'test.qkview'


def test_ihealth_args_defaults():
    with patch('sys.argv', ['prog', '--client-id', 'cid', '--client-secret', 'csec']):
        args = f5functions.ihealth_args()
        assert args.client_id == 'cid'
        assert args.client_secret == 'csec'
        assert args.app_id == f5functions.IHEALTH_APP_ID


def test_myf5_args_defaults():
    with patch('sys.argv', ['prog', '--client-id', 'cid', '--client-secret', 'csec']):
        args = f5functions.myf5_args()
        assert args.client_id == 'cid'
        assert args.client_secret == 'csec'
        assert args.app_id == f5functions.MYF5_APP_ID
        assert args.k_value == f5functions.MYF5_API_K_VALUE


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

@patch('f5functions.myf5_retrieve_access_token')
def test_myf5_authenticate_success(mock_token):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"access_token": "tok123"}
    mock_token.return_value = mock_response

    token = f5functions.myf5_authenticate('app', 'cid', 'csec')
    assert token == 'tok123'
    mock_token.assert_called_once_with('app', 'cid', 'csec', scope='myf5_scope')


@patch('f5functions.myf5_retrieve_access_token')
def test_myf5_authenticate_failure(mock_token):
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = 'Unauthorized'
    mock_token.return_value = mock_response

    with pytest.raises(SystemExit):
        f5functions.myf5_authenticate('app', 'cid', 'csec')


# ---------------------------------------------------------------------------
# BIG-IP API functions
# ---------------------------------------------------------------------------

@patch('f5functions.requests.get')
def test_bigip_connectivity_test_verify_true(mock_get):
    mock_get.return_value = MagicMock(status_code=200)
    resp = f5functions.bigip_connectivity_test('host', 'user', 'pass', verify=True)
    mock_get.assert_called_once()
    _, kwargs = mock_get.call_args
    assert kwargs['verify'] is True
    assert resp.status_code == 200


@patch('f5functions.requests.get')
def test_bigip_connectivity_test_verify_false(mock_get):
    mock_get.return_value = MagicMock(status_code=200)
    f5functions.bigip_connectivity_test('host', 'user', 'pass', verify=False)
    _, kwargs = mock_get.call_args
    assert kwargs['verify'] is False


@patch('f5functions.requests.get')
def test_bigip_connectivity_test_request_exception(mock_get):
    mock_get.side_effect = f5functions.requests.exceptions.ConnectionError("conn refused")
    with pytest.raises(SystemExit):
        f5functions.bigip_connectivity_test('host', 'user', 'pass')


@patch('f5functions.requests.post')
def test_bigip_generate_qkview_default(mock_post):
    mock_post.return_value = MagicMock(status_code=202)
    resp = f5functions.bigip_generate_qkview('host', 'user', 'pass', 'test.qkview')
    assert resp.status_code == 202
    args, kwargs = mock_post.call_args
    assert '/mgmt/cm/autodeploy/qkview' in args[0]
    assert kwargs['json'] == {'name': 'test.qkview'}


@patch('f5functions.requests.post')
def test_bigip_generate_qkview_no_truncate(mock_post):
    mock_post.return_value = MagicMock(status_code=200)
    f5functions.bigip_generate_qkview('host', 'user', 'pass', 'test.qkview', no_truncate=True)
    args, kwargs = mock_post.call_args
    assert '/mgmt/tm/util/qkview' in args[0]
    assert kwargs['json']['command'] == 'run'


@patch('f5functions.requests.get')
def test_bigip_list_qkviews(mock_get):
    mock_get.return_value = MagicMock(status_code=200)
    resp = f5functions.bigip_list_qkviews('host', 'user', 'pass')
    assert resp.status_code == 200


@patch('f5functions.bigip_list_qkviews')
@patch('f5functions.requests.delete')
def test_bigip_delete_qkview_found(mock_delete, mock_list):
    mock_list.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value={'items': [{'name': 'test.qkview', 'id': 'abc123'}]})
    )
    mock_delete.return_value = MagicMock(status_code=200)

    resp = f5functions.bigip_delete_qkview('host', 'user', 'pass', 'test.qkview')
    assert resp.status_code == 200


@patch('f5functions.bigip_list_qkviews')
def test_bigip_delete_qkview_not_found(mock_list):
    mock_list.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value={'items': []})
    )
    with pytest.raises(SystemExit, match='not found'):
        f5functions.bigip_delete_qkview('host', 'user', 'pass', 'missing.qkview')


@patch('f5functions.bigip_list_qkviews')
def test_bigip_delete_qkview_list_fails(mock_list):
    mock_list.return_value = MagicMock(status_code=500, text='Internal error')
    with pytest.raises(SystemExit, match='Failed to list'):
        f5functions.bigip_delete_qkview('host', 'user', 'pass', 'test.qkview')


# ---------------------------------------------------------------------------
# MyF5 API functions
# ---------------------------------------------------------------------------

@patch('f5functions.requests.post')
def test_myf5_retrieve_access_token(mock_post):
    mock_post.return_value = MagicMock(status_code=200)
    resp = f5functions.myf5_retrieve_access_token('app', 'cid', 'csec')
    assert resp.status_code == 200
    args, kwargs = mock_post.call_args
    assert 'identity.account.f5.com' in args[0]
    assert kwargs['data']['grant_type'] == 'client_credentials'


@patch('f5functions.requests.get')
def test_myf5_list_support_cases(mock_get):
    mock_get.return_value = MagicMock(status_code=200)
    resp = f5functions.myf5_list_support_cases('token123')
    assert resp.status_code == 200
    args, kwargs = mock_get.call_args
    assert 'Bearer token123' in kwargs['headers']['Authorization']


@patch('f5functions.requests.post')
def test_myf5_create_new_support_case(mock_post):
    mock_post.return_value = MagicMock(status_code=201)
    payload = {'subject': 'test'}
    resp = f5functions.myf5_create_new_support_case('tok', payload)
    assert resp.status_code == 201
    _, kwargs = mock_post.call_args
    assert kwargs['json'] == payload


@patch('f5functions.requests.patch')
def test_myf5_add_comments(mock_patch):
    mock_patch.return_value = MagicMock(status_code=200)
    resp = f5functions.myf5_add_comments_to_existing_support_case('tok', 'C123', 'hello')
    assert resp.status_code == 200
    _, kwargs = mock_patch.call_args
    assert kwargs['json'] == {'comments': 'hello'}
    assert 'C123' in mock_patch.call_args[0][0]


@patch('f5functions.requests.get')
def test_myf5_retrieve_case_creation_metadata(mock_get):
    mock_get.return_value = MagicMock(status_code=200)
    resp = f5functions.myf5_retrieve_case_creation_metadata('tok')
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# iHealth API functions
# ---------------------------------------------------------------------------

@patch('f5functions.requests.get')
def test_ihealth_list_qkview_ids(mock_get):
    mock_get.return_value = MagicMock(status_code=200)
    resp = f5functions.ihealth_list_qkview_ids('tok')
    assert resp.status_code == 200
    _, kwargs = mock_get.call_args
    assert 'Bearer tok' in kwargs['headers']['Authorization']


@patch('f5functions.requests.get')
def test_ihealth_show_qkview_metadata(mock_get):
    mock_get.return_value = MagicMock(status_code=200)
    resp = f5functions.ihealth_show_qkview_metadata('tok', '12345')
    assert resp.status_code == 200
    assert '12345' in mock_get.call_args[0][0]


@patch('f5functions.os.path.isfile', return_value=True)
@patch('f5functions.requests.post')
def test_ihealth_upload_qkview(mock_post, mock_isfile):
    mock_post.return_value = MagicMock(status_code=200)
    m = mock_open(read_data=b'qkview data')
    with patch('builtins.open', m):
        resp = f5functions.ihealth_upload_qkview('tok', '/tmp/test.qkview', 'C123')
    assert resp.status_code == 200
    _, kwargs = mock_post.call_args
    assert kwargs['params']['f5_support_case'] == 'C123'


@patch('f5functions.os.path.isfile', return_value=False)
def test_ihealth_upload_qkview_missing_file(mock_isfile):
    with pytest.raises(SystemExit, match='does not exist'):
        f5functions.ihealth_upload_qkview('tok', '/tmp/missing.qkview')
