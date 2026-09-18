"""Unit tests for python/f5functions.py.

Compatible with both python standard library unittest and pytest.
Gracefully stubs external packages if running in minimal offline environments.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, mock_open

# Ensure required libraries are mockable even if not yet installed in host environment
try:
    import requests
    import urllib3
    import tqdm
except ImportError:
    class RequestException(Exception):
        pass

    class ConnectionError(RequestException):
        pass

    class InsecureRequestWarning(Warning):
        pass

    mock_requests = MagicMock()
    mock_requests.exceptions.RequestException = RequestException
    mock_requests.exceptions.ConnectionError = ConnectionError
    mock_requests.auth.HTTPBasicAuth = lambda u, p: ('basic', u, p)

    mock_urllib3 = MagicMock()
    mock_urllib3.exceptions.InsecureRequestWarning = InsecureRequestWarning

    mock_tqdm = MagicMock()

    sys.modules['requests'] = mock_requests
    sys.modules['requests.exceptions'] = mock_requests.exceptions
    sys.modules['requests.auth'] = mock_requests.auth
    sys.modules['urllib3'] = mock_urllib3
    sys.modules['urllib3.exceptions'] = mock_urllib3.exceptions
    sys.modules['tqdm'] = mock_tqdm

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))
import f5functions


class TestF5Functions(unittest.TestCase):
    """Test suite for F5 functions, CLI arguments, and API integrations."""

    # ---------------------------------------------------------------------------
    # Constants & Helpers
    # ---------------------------------------------------------------------------

    def test_constants_defined(self):
        """Verify standard constants match current F5 architecture."""
        self.assertEqual(f5functions.MYF5_APP_ID, 'aus19gt5bu0jGw9Fi358')
        self.assertEqual(f5functions.IHEALTH_APP_ID, 'ausp95ykc80HOU7SQ357')
        self.assertEqual(f5functions.MYF5_API_K_VALUE, 'UKKD3Vxv7NHrM3QmYk8Fk2mZnLtljAKX')
        self.assertEqual(f5functions.MYF5_API_FQDN, 'support.apis.f5.com')
        self.assertEqual(f5functions.IHEALTH_API_FQDN, 'ihealth2-api.f5.com')
        self.assertEqual(f5functions.IHEALTH_FALLBACK_API_FQDN, 'ihealth-api.f5.com')
        self.assertEqual(f5functions.OKTA_IDENTITY_FQDN, 'identity.account.f5.com')
        self.assertEqual(f5functions.AUTH0_IDENTITY_FQDN, 'idp.identity.f5.com')

    def test_clean_fqdn(self):
        """Verify _clean_fqdn sanitizes URLs and protocol prefixes correctly."""
        self.assertEqual(f5functions._clean_fqdn('https://support.apis.f5.com/'), 'support.apis.f5.com')
        self.assertEqual(f5functions._clean_fqdn('http://idp.identity.f5.com'), 'idp.identity.f5.com')
        self.assertEqual(f5functions._clean_fqdn('ihealth2-api.f5.com'), 'ihealth2-api.f5.com')
        self.assertEqual(f5functions._clean_fqdn(None, default='default.fqdn'), 'default.fqdn')
        self.assertEqual(f5functions._clean_fqdn('', default='default.fqdn'), 'default.fqdn')

    # ---------------------------------------------------------------------------
    # Shared argument parsers
    # ---------------------------------------------------------------------------

    def test_bigip_args_defaults(self):
        """Verify default argument parsing for BIG-IP CLI commands."""
        with patch('sys.argv', ['prog', '--host', 'bigip1.example.com', '--password', 'secret']):
            args = f5functions.bigip_args()
            self.assertEqual(args.host, 'bigip1.example.com')
            self.assertEqual(args.username, 'admin')
            self.assertEqual(args.password, 'secret')
            self.assertFalse(args.no_ssl_verify)

    def test_bigip_args_no_ssl_verify(self):
        """Verify --no-ssl-verify flag sets no_ssl_verify to True."""
        with patch('sys.argv', ['prog', '--host', 'bigip1', '--password', 'pw', '--no-ssl-verify']):
            args = f5functions.bigip_args()
            self.assertTrue(args.no_ssl_verify)

    def test_bigip_args_extra_args(self):
        """Verify passing extra tool-specific arguments to bigip_args."""
        with patch('sys.argv', ['prog', '--host', 'h', '--password', 'p', '--filename', 'test.qkview']):
            args = f5functions.bigip_args(
                (["--filename"], {"type": str, "help": "file", "required": True}),
            )
            self.assertEqual(args.filename, 'test.qkview')

    def test_ihealth_args_defaults(self):
        """Verify default argument parsing for iHealth CLI commands."""
        with patch('sys.argv', ['prog', '--client-id', 'cid', '--client-secret', 'csec']):
            args = f5functions.ihealth_args()
            self.assertEqual(args.client_id, 'cid')
            self.assertEqual(args.client_secret, 'csec')
            self.assertEqual(args.app_id, f5functions.IHEALTH_APP_ID)
            self.assertIsNone(args.auth_url)
            self.assertEqual(args.auth_fqdn, f5functions.IDENTITY_API_FQDN)
            self.assertEqual(args.api_fqdn, f5functions.IHEALTH_API_FQDN)

    def test_myf5_args_defaults(self):
        """Verify default argument parsing for MyF5 CLI commands."""
        with patch('sys.argv', ['prog', '--client-id', 'cid', '--client-secret', 'csec']):
            args = f5functions.myf5_args()
            self.assertEqual(args.client_id, 'cid')
            self.assertEqual(args.client_secret, 'csec')
            self.assertEqual(args.app_id, f5functions.MYF5_APP_ID)
            self.assertEqual(args.k_value, f5functions.MYF5_API_K_VALUE)
            self.assertIsNone(args.auth_url)
            self.assertEqual(args.auth_fqdn, f5functions.IDENTITY_API_FQDN)
            self.assertEqual(args.api_url, f5functions.MYF5_API_FQDN)

    # ---------------------------------------------------------------------------
    # Auth helper
    # ---------------------------------------------------------------------------

    @patch('f5functions.myf5_retrieve_access_token')
    def test_myf5_authenticate_success(self, mock_token):
        """Verify successful token extraction on HTTP 200."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "tok123"}
        mock_token.return_value = mock_response

        token = f5functions.myf5_authenticate('app', 'cid', 'csec')
        self.assertEqual(token, 'tok123')
        mock_token.assert_called_once_with('app', 'cid', 'csec', scope='myf5_scope', auth_url=None, auth_fqdn=f5functions.IDENTITY_API_FQDN)

    @patch('f5functions.myf5_retrieve_access_token')
    def test_myf5_authenticate_failure_k000162308_diagnostic(self, mock_token):
        """Verify informative K000162308 diagnostic message on HTTP 401."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = 'Unauthorized'
        mock_token.return_value = mock_response

        with self.assertRaises(SystemExit) as ctx:
            f5functions.myf5_authenticate('app', 'cid', 'csec')
        self.assertIn('K000162308', str(ctx.exception))
        self.assertIn('Auth0', str(ctx.exception))

    # ---------------------------------------------------------------------------
    # BIG-IP API functions
    # ---------------------------------------------------------------------------

    @patch('f5functions.requests.get')
    def test_bigip_connectivity_test_verify_true(self, mock_get):
        """Verify bigip_connectivity_test passes verify=True to requests."""
        mock_get.return_value = MagicMock(status_code=200)
        resp = f5functions.bigip_connectivity_test('host', 'user', 'pass', verify=True)
        mock_get.assert_called_once()
        _, kwargs = mock_get.call_args
        self.assertTrue(kwargs['verify'])
        self.assertEqual(resp.status_code, 200)

    @patch('f5functions.requests.get')
    def test_bigip_connectivity_test_verify_false(self, mock_get):
        """Verify bigip_connectivity_test passes verify=False to requests."""
        mock_get.return_value = MagicMock(status_code=200)
        f5functions.bigip_connectivity_test('host', 'user', 'pass', verify=False)
        _, kwargs = mock_get.call_args
        self.assertFalse(kwargs['verify'])

    @patch('f5functions.requests.get')
    def test_bigip_connectivity_test_request_exception(self, mock_get):
        """Verify bigip_connectivity_test raises SystemExit on connection error."""
        mock_get.side_effect = f5functions.requests.exceptions.ConnectionError("conn refused")
        with self.assertRaises(SystemExit):
            f5functions.bigip_connectivity_test('host', 'user', 'pass')

    @patch('f5functions.requests.post')
    def test_bigip_generate_qkview_default(self, mock_post):
        """Verify bigip_generate_qkview calls autodeploy qkview by default."""
        mock_post.return_value = MagicMock(status_code=202)
        resp = f5functions.bigip_generate_qkview('host', 'user', 'pass', 'test.qkview')
        self.assertEqual(resp.status_code, 202)
        args, kwargs = mock_post.call_args
        self.assertIn('/mgmt/cm/autodeploy/qkview', args[0])
        self.assertEqual(kwargs['json'], {'name': 'test.qkview'})

    @patch('f5functions.requests.post')
    def test_bigip_generate_qkview_no_truncate(self, mock_post):
        """Verify bigip_generate_qkview with no_truncate uses /mgmt/tm/util/qkview -s0."""
        mock_post.return_value = MagicMock(status_code=200)
        f5functions.bigip_generate_qkview('host', 'user', 'pass', 'test.qkview', no_truncate=True)
        args, kwargs = mock_post.call_args
        self.assertIn('/mgmt/tm/util/qkview', args[0])
        self.assertEqual(kwargs['json']['command'], 'run')

    @patch('f5functions.requests.get')
    def test_bigip_list_qkviews(self, mock_get):
        """Verify bigip_list_qkviews queries autodeploy endpoint."""
        mock_get.return_value = MagicMock(status_code=200)
        resp = f5functions.bigip_list_qkviews('host', 'user', 'pass')
        self.assertEqual(resp.status_code, 200)

    @patch('f5functions.bigip_list_qkviews')
    @patch('f5functions.requests.delete')
    def test_bigip_delete_qkview_found(self, mock_delete, mock_list):
        """Verify bigip_delete_qkview successfully deletes an existing QKView."""
        mock_list.return_value = MagicMock(
            status_code=200,
            json=MagicMock(return_value={'items': [{'name': 'test.qkview', 'id': 'abc123'}]})
        )
        mock_delete.return_value = MagicMock(status_code=200)

        resp = f5functions.bigip_delete_qkview('host', 'user', 'pass', 'test.qkview')
        self.assertEqual(resp.status_code, 200)

    @patch('f5functions.bigip_list_qkviews')
    def test_bigip_delete_qkview_not_found(self, mock_list):
        """Verify bigip_delete_qkview raises SystemExit if filename not found."""
        mock_list.return_value = MagicMock(
            status_code=200,
            json=MagicMock(return_value={'items': []})
        )
        with self.assertRaises(SystemExit) as ctx:
            f5functions.bigip_delete_qkview('host', 'user', 'pass', 'missing.qkview')
        self.assertIn('not found', str(ctx.exception))

    @patch('f5functions.bigip_list_qkviews')
    def test_bigip_delete_qkview_list_fails(self, mock_list):
        """Verify bigip_delete_qkview handles list failure."""
        mock_list.return_value = MagicMock(status_code=500, text='Internal error')
        with self.assertRaises(SystemExit) as ctx:
            f5functions.bigip_delete_qkview('host', 'user', 'pass', 'test.qkview')
        self.assertIn('Failed to list', str(ctx.exception))

    # ---------------------------------------------------------------------------
    # MyF5 API functions & Auth0 / Okta flows
    # ---------------------------------------------------------------------------

    @patch('f5functions.requests.post')
    def test_myf5_retrieve_access_token_okta(self, mock_post):
        """Verify legacy Okta token retrieval with HTTPBasicAuth."""
        mock_post.return_value = MagicMock(status_code=200)
        resp = f5functions.myf5_retrieve_access_token('app', 'cid', 'csec')
        self.assertEqual(resp.status_code, 200)
        args, kwargs = mock_post.call_args
        self.assertIn('identity.account.f5.com', args[0])
        self.assertEqual(kwargs['data']['grant_type'], 'client_credentials')

    @patch('f5functions.requests.post')
    def test_myf5_retrieve_access_token_auth0(self, mock_post):
        """Verify modern Auth0 token retrieval format on idp.identity.f5.com."""
        mock_post.return_value = MagicMock(status_code=200)
        resp = f5functions.myf5_retrieve_access_token(
            'app', 'cid', 'csec', auth_fqdn='idp.identity.f5.com'
        )
        self.assertEqual(resp.status_code, 200)
        args, kwargs = mock_post.call_args
        self.assertIn('idp.identity.f5.com/oauth/token', args[0])
        self.assertEqual(kwargs['data']['client_id'], 'cid')
        self.assertEqual(kwargs['data']['client_secret'], 'csec')
        self.assertIsNone(kwargs['auth'])

    @patch('f5functions.requests.post')
    def test_myf5_retrieve_access_token_custom_auth_url(self, mock_post):
        """Verify custom auth_url override targeting an enterprise proxy."""
        mock_post.return_value = MagicMock(status_code=200)
        resp = f5functions.myf5_retrieve_access_token(
            'app', 'cid', 'csec', auth_url='https://custom.idp.local/token'
        )
        self.assertEqual(resp.status_code, 200)
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], 'https://custom.idp.local/token')
        self.assertEqual(kwargs['data']['client_id'], 'cid')

    @patch('f5functions.requests.get')
    def test_myf5_list_support_cases(self, mock_get):
        """Verify listing support cases with Bearer authorization header."""
        mock_get.return_value = MagicMock(status_code=200)
        resp = f5functions.myf5_list_support_cases('token123')
        self.assertEqual(resp.status_code, 200)
        args, kwargs = mock_get.call_args
        self.assertIn('Bearer token123', kwargs['headers']['Authorization'])

    @patch('f5functions.requests.post')
    def test_myf5_create_new_support_case(self, mock_post):
        """Verify creating support case forwards JSON payload."""
        mock_post.return_value = MagicMock(status_code=201)
        payload = {'subject': 'test'}
        resp = f5functions.myf5_create_new_support_case('tok', payload)
        self.assertEqual(resp.status_code, 201)
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json'], payload)

    @patch('f5functions.requests.patch')
    def test_myf5_add_comments(self, mock_patch):
        """Verify adding comments uses PATCH on case number URI."""
        mock_patch.return_value = MagicMock(status_code=200)
        resp = f5functions.myf5_add_comments_to_existing_support_case('tok', 'C123', 'hello')
        self.assertEqual(resp.status_code, 200)
        _, kwargs = mock_patch.call_args
        self.assertEqual(kwargs['json'], {'comments': 'hello'})
        self.assertIn('C123', mock_patch.call_args[0][0])

    @patch('f5functions.requests.get')
    def test_myf5_retrieve_case_creation_metadata(self, mock_get):
        """Verify retrieving case creation schema metadata."""
        mock_get.return_value = MagicMock(status_code=200)
        resp = f5functions.myf5_retrieve_case_creation_metadata('tok')
        self.assertEqual(resp.status_code, 200)

    # ---------------------------------------------------------------------------
    # iHealth API functions & Fallback
    # ---------------------------------------------------------------------------

    @patch('f5functions.requests.get')
    def test_ihealth_list_qkview_ids(self, mock_get):
        """Verify listing QKView IDs sends correct vendor accept header."""
        mock_get.return_value = MagicMock(status_code=200)
        resp = f5functions.ihealth_list_qkview_ids('tok')
        self.assertEqual(resp.status_code, 200)
        _, kwargs = mock_get.call_args
        self.assertIn('Bearer tok', kwargs['headers']['Authorization'])

    @patch('f5functions.requests.get')
    def test_ihealth_list_qkview_ids_fallback(self, mock_get):
        """Verify automatic fallback from ihealth2-api to ihealth-api on connection error."""
        primary_fail = f5functions.requests.exceptions.ConnectionError("Primary failed")
        fallback_success = MagicMock(status_code=200)
        mock_get.side_effect = [primary_fail, fallback_success]

        resp = f5functions.ihealth_list_qkview_ids('tok')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(mock_get.call_count, 2)
        first_call_url = mock_get.call_args_list[0][0][0]
        second_call_url = mock_get.call_args_list[1][0][0]
        self.assertIn('ihealth2-api.f5.com', first_call_url)
        self.assertIn('ihealth-api.f5.com', second_call_url)

    @patch('f5functions.requests.get')
    def test_ihealth_show_qkview_metadata(self, mock_get):
        """Verify show_qkview_metadata includes QKView ID in target URL."""
        mock_get.return_value = MagicMock(status_code=200)
        resp = f5functions.ihealth_show_qkview_metadata('tok', '12345')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('12345', mock_get.call_args[0][0])

    @patch('f5functions.os.path.isfile', return_value=True)
    @patch('f5functions.requests.post')
    def test_ihealth_upload_qkview(self, mock_post, mock_isfile):
        """Verify uploading QKView file with support case parameter."""
        mock_post.return_value = MagicMock(status_code=200)
        m = mock_open(read_data=b'qkview data')
        with patch('builtins.open', m):
            resp = f5functions.ihealth_upload_qkview('tok', '/tmp/test.qkview', 'C123')
        self.assertEqual(resp.status_code, 200)
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs['params']['f5_support_case'], 'C123')

    @patch('f5functions.os.path.isfile', return_value=False)
    def test_ihealth_upload_qkview_missing_file(self, mock_isfile):
        """Verify upload aborts with SystemExit if file does not exist."""
        with self.assertRaises(SystemExit) as ctx:
            f5functions.ihealth_upload_qkview('tok', '/tmp/missing.qkview')
        self.assertIn('does not exist', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
