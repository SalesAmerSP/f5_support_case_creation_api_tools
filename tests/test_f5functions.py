"""Unit tests for qkviewmgr.f5functions.
 
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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'qkviewmgr'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
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
    # Credential Resolution & Zero Secret CLI tests
    # ---------------------------------------------------------------------------

    def test_resolve_bigip_credentials_cli(self):
        """Verify resolve_bigip_credentials returns password with security warning."""
        pw = f5functions.resolve_bigip_credentials("192.0.2.1", "admin", "secret_cli")
        self.assertEqual(pw, "secret_cli")

    @patch.dict(os.environ, {"BIGIP_PASSWORD": "secret_from_env"})
    def test_resolve_bigip_credentials_env(self):
        """Verify resolve_bigip_credentials reads BIGIP_PASSWORD environment variable."""
        pw = f5functions.resolve_bigip_credentials("192.0.2.1", "admin")
        self.assertEqual(pw, "secret_from_env")

    @patch('sys.stdin.isatty', return_value=True)
    @patch('getpass.getpass', return_value="secret_interactive")
    def test_resolve_bigip_credentials_interactive(self, mock_getpass, mock_isatty):
        """Verify resolve_bigip_credentials prompts interactively via getpass."""
        with patch.dict(os.environ, {}, clear=True):
            pw = f5functions.resolve_bigip_credentials("192.0.2.1", "admin")
            self.assertEqual(pw, "secret_interactive")
            mock_getpass.assert_called_once()

    def test_resolve_bigip_username_cli(self):
        """Verify resolve_bigip_username returns explicitly passed CLI argument."""
        user = f5functions.resolve_bigip_username("custom_admin")
        self.assertEqual(user, "custom_admin")

    @patch.dict(os.environ, {"BIGIP_USERNAME": "env_user"})
    def test_resolve_bigip_username_env(self):
        """Verify resolve_bigip_username reads BIGIP_USERNAME environment variable."""
        user = f5functions.resolve_bigip_username()
        self.assertEqual(user, "env_user")

    @patch.dict(os.environ, {}, clear=True)
    def test_resolve_bigip_username_default(self):
        """Verify resolve_bigip_username defaults to 'admin' when no argument or env var is set."""
        user = f5functions.resolve_bigip_username()
        self.assertEqual(user, "admin")

    def test_resolve_ihealth_credentials_cli(self):
        """Verify resolve_ihealth_credentials returns arguments when provided via CLI."""
        cid, csec = f5functions.resolve_ihealth_credentials("cli_id", "cli_sec")
        self.assertEqual(cid, "cli_id")
        self.assertEqual(csec, "cli_sec")

    @patch.dict(os.environ, {"F5_CLIENT_ID": "env_id", "F5_CLIENT_SECRET": "env_sec"})
    def test_resolve_ihealth_credentials_env(self):
        """Verify resolve_ihealth_credentials reads F5_CLIENT_ID and F5_CLIENT_SECRET."""
        cid, csec = f5functions.resolve_ihealth_credentials()
        self.assertEqual(cid, "env_id")
        self.assertEqual(csec, "env_sec")

    @patch('os.path.isfile', side_effect=lambda p: p.endswith('.ihealth_credentials'))
    def test_resolve_ihealth_credentials_file(self, mock_isfile):
        """Verify resolve_ihealth_credentials parses ~/.ihealth_credentials file."""
        mock_ini = "[g.robinson@f5.com]\nclientid = file_id\nclientsecret = file_sec\n"
        with patch.dict(os.environ, {}, clear=True):
            with patch('builtins.open', mock_open(read_data=mock_ini)):
                cid, csec = f5functions.resolve_ihealth_credentials()
                self.assertEqual(cid, "file_id")
                self.assertEqual(csec, "file_sec")

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

    @patch('f5functions.get_secure_session')
    def test_myf5_retrieve_access_token_okta(self, mock_get_session):
        """Verify legacy Okta token retrieval with HTTPBasicAuth."""
        mock_session = MagicMock()
        mock_session.post.return_value = MagicMock(status_code=200)
        mock_get_session.return_value = mock_session

        resp = f5functions.myf5_retrieve_access_token('app', 'cid', 'csec')
        self.assertEqual(resp.status_code, 200)
        args, kwargs = mock_session.post.call_args
        self.assertIn('identity.account.f5.com', args[0])
        self.assertEqual(kwargs['data']['grant_type'], 'client_credentials')

    @patch('f5functions.get_secure_session')
    def test_myf5_retrieve_access_token_auth0(self, mock_get_session):
        """Verify modern Auth0 token retrieval format on idp.identity.f5.com."""
        mock_session = MagicMock()
        mock_session.post.return_value = MagicMock(status_code=200)
        mock_get_session.return_value = mock_session

        resp = f5functions.myf5_retrieve_access_token(
            'app', 'cid', 'csec', auth_fqdn='idp.identity.f5.com'
        )
        self.assertEqual(resp.status_code, 200)
        args, kwargs = mock_session.post.call_args
        self.assertIn('idp.identity.f5.com/oauth/token', args[0])
        self.assertEqual(kwargs['data']['client_id'], 'cid')
        self.assertEqual(kwargs['data']['client_secret'], 'csec')
        self.assertIsNone(kwargs['auth'])

    @patch('f5functions.get_secure_session')
    def test_myf5_retrieve_access_token_custom_auth_url(self, mock_get_session):
        """Verify custom auth_url override targeting an enterprise proxy."""
        mock_session = MagicMock()
        mock_session.post.return_value = MagicMock(status_code=200)
        mock_get_session.return_value = mock_session

        resp = f5functions.myf5_retrieve_access_token(
            'app', 'cid', 'csec', auth_url='https://custom.idp.local/token'
        )
        self.assertEqual(resp.status_code, 200)
        args, kwargs = mock_session.post.call_args
        self.assertEqual(args[0], 'https://custom.idp.local/token')
        self.assertEqual(kwargs['data']['client_id'], 'cid')

    @patch('f5functions.get_secure_session')
    def test_myf5_list_support_cases(self, mock_get_session):
        """Verify listing support cases with Bearer authorization header."""
        mock_session = MagicMock()
        mock_session.get.return_value = MagicMock(status_code=200)
        mock_get_session.return_value = mock_session

        resp = f5functions.myf5_list_support_cases('token123')
        self.assertEqual(resp.status_code, 200)
        args, kwargs = mock_session.get.call_args
        self.assertIn('Bearer token123', kwargs['headers']['Authorization'])

    @patch('f5functions.get_secure_session')
    def test_myf5_create_new_support_case(self, mock_get_session):
        """Verify creating support case forwards JSON payload."""
        mock_session = MagicMock()
        mock_session.post.return_value = MagicMock(status_code=201)
        mock_get_session.return_value = mock_session

        payload = {'subject': 'test'}
        resp = f5functions.myf5_create_new_support_case('tok', payload)
        self.assertEqual(resp.status_code, 201)
        _, kwargs = mock_session.post.call_args
        self.assertEqual(kwargs['json'], payload)

    @patch('f5functions.get_secure_session')
    def test_myf5_add_comments(self, mock_get_session):
        """Verify adding comments uses PATCH on case number URI."""
        mock_session = MagicMock()
        mock_session.patch.return_value = MagicMock(status_code=200)
        mock_get_session.return_value = mock_session

        resp = f5functions.myf5_add_comments_to_existing_support_case('tok', 'C123', 'hello')
        self.assertEqual(resp.status_code, 200)
        _, kwargs = mock_session.patch.call_args
        self.assertEqual(kwargs['json'], {'comments': 'hello'})
        self.assertIn('C123', mock_session.patch.call_args[0][0])

    @patch('f5functions.get_secure_session')
    def test_myf5_retrieve_case_creation_metadata(self, mock_get_session):
        """Verify retrieving case creation schema metadata."""
        mock_session = MagicMock()
        mock_session.get.return_value = MagicMock(status_code=200)
        mock_get_session.return_value = mock_session

        resp = f5functions.myf5_retrieve_case_creation_metadata('tok')
        self.assertEqual(resp.status_code, 200)

    # ---------------------------------------------------------------------------
    # iHealth API functions & Fallback
    # ---------------------------------------------------------------------------

    @patch('f5functions.get_secure_session')
    def test_ihealth_list_qkview_ids(self, mock_get_session):
        """Verify listing QKView IDs sends correct vendor accept header."""
        mock_session = MagicMock()
        mock_session.get.return_value = MagicMock(status_code=200)
        mock_get_session.return_value = mock_session

        resp = f5functions.ihealth_list_qkview_ids('tok')
        self.assertEqual(resp.status_code, 200)
        _, kwargs = mock_session.get.call_args
        self.assertIn('Bearer tok', kwargs['headers']['Authorization'])

    @patch('f5functions.get_secure_session')
    def test_ihealth_list_qkview_ids_fallback(self, mock_get_session):
        """Verify automatic fallback from ihealth2-api to ihealth-api on connection error."""
        primary_fail = f5functions.requests.exceptions.ConnectionError("Primary failed")
        fallback_success = MagicMock(status_code=200)
        mock_session = MagicMock()
        mock_session.get.side_effect = [primary_fail, fallback_success]
        mock_get_session.return_value = mock_session

        resp = f5functions.ihealth_list_qkview_ids('tok')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(mock_session.get.call_count, 2)
        first_call_url = mock_session.get.call_args_list[0][0][0]
        second_call_url = mock_session.get.call_args_list[1][0][0]
        self.assertIn('ihealth2-api.f5.com', first_call_url)
        self.assertIn('ihealth-api.f5.com', second_call_url)

    @patch('f5functions.get_secure_session')
    def test_ihealth_show_qkview_metadata(self, mock_get_session):
        """Verify show_qkview_metadata includes QKView ID in target URL."""
        mock_session = MagicMock()
        mock_session.get.return_value = MagicMock(status_code=200)
        mock_get_session.return_value = mock_session

        resp = f5functions.ihealth_show_qkview_metadata('tok', '12345')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('12345', mock_session.get.call_args[0][0])

    @patch('f5functions.os.path.isfile', return_value=True)
    @patch('f5functions.get_secure_session')
    def test_ihealth_upload_qkview(self, mock_get_session, mock_isfile):
        """Verify uploading QKView file with support case parameter."""
        mock_session = MagicMock()
        mock_session.post.return_value = MagicMock(status_code=200)
        mock_get_session.return_value = mock_session

        m = mock_open(read_data=b'qkview data')
        with patch('builtins.open', m):
            resp = f5functions.ihealth_upload_qkview('tok', '/tmp/test.qkview', 'C123')
        self.assertEqual(resp.status_code, 200)
        _, kwargs = mock_session.post.call_args
        self.assertEqual(kwargs['params']['f5_support_case'], 'C123')

    @patch('f5functions.os.path.isfile', return_value=False)
    def test_ihealth_upload_qkview_missing_file(self, mock_isfile):
        """Verify upload aborts with SystemExit if file does not exist."""
        with self.assertRaises(SystemExit) as ctx:
            f5functions.ihealth_upload_qkview('tok', '/tmp/missing.qkview')
        self.assertIn('does not exist', str(ctx.exception))

    # ---------------------------------------------------------------------------
    # Cryptographic & Streaming Verification
    # ---------------------------------------------------------------------------

    def test_secure_tls_adapter_config(self):
        """Verify SecureTLSAdapter enforces TLS 1.2+ minimum and PFS AEAD ciphers."""
        adapter = f5functions.SecureTLSAdapter()
        self.assertEqual(adapter.ssl_version, f5functions.ssl.TLSVersion.TLSv1_2)
        self.assertIn('ECDHE-RSA-AES256-GCM-SHA384', adapter.ciphers)

    def test_get_secure_session_verify_true(self):
        """Verify get_secure_session mounts SecureTLSAdapter and Mozilla certifi CA bundle."""
        session = f5functions.get_secure_session(verify=True)
        self.assertIn('https://', session.adapters)
        self.assertIsInstance(session.adapters['https://'], f5functions.SecureTLSAdapter)
        self.assertEqual(session.verify, f5functions.certifi.where())

    def test_get_secure_session_verify_false(self):
        """Verify get_secure_session handles verify=False for self-signed lab targets."""
        session = f5functions.get_secure_session(verify=False)
        self.assertFalse(session.verify)

    def test_multipart_progress_stream(self):
        """Verify MultipartProgressStream accurately builds boundaries and streams chunks."""
        m = mock_open(read_data=b'1234567890' * 100)
        with patch('builtins.open', m), patch('f5functions.os.path.getsize', return_value=1000):
            stream = f5functions.MultipartProgressStream('field', '/tmp/sample.qkview')
            self.assertIn('multipart/form-data', stream.content_type)
            self.assertGreater(len(stream), 1000)
            data = b''
            while True:
                chunk = stream.read(128)
                if not chunk:
                    break
                data += chunk
            self.assertIn(b'1234567890', data)
            self.assertIn(b'sample.qkview', data)
            stream.close()

    @patch('f5functions.ihealth_list_qkview_ids')
    def test_ihealth_connectivity_test(self, mock_list):
        """Verify ihealth_connectivity_test returns True on 200 OK."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_list.return_value = mock_resp
        with patch('sys.stdout'):
            result = f5functions.ihealth_connectivity_test('test_token')
        self.assertTrue(result)
        mock_list.assert_called_once_with('test_token', api_fqdn=f5functions.IHEALTH_API_FQDN)

    @patch('f5functions.myf5_retrieve_case_creation_metadata')
    def test_myf5_connectivity_test(self, mock_meta):
        """Verify myf5_connectivity_test returns True on 200 OK."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_meta.return_value = mock_resp
        with patch('sys.stdout'):
            result = f5functions.myf5_connectivity_test('test_token')
        self.assertTrue(result)
        mock_meta.assert_called_once_with('test_token', api_fqdn=f5functions.MYF5_API_FQDN, k_value=f5functions.MYF5_API_K_VALUE)

    def test_myf5_add_comments_alias(self):
        """Verify myf5_add_comments alias references myf5_add_comments_to_existing_support_case."""
        self.assertIs(f5functions.myf5_add_comments, f5functions.myf5_add_comments_to_existing_support_case)

    @patch('f5functions.requests.get')
    @patch('f5functions.os.makedirs')
    def test_bigip_download_qkview_preserves_dir(self, mock_mkdirs, mock_get):
        """Verify bigip_download_qkview preserves destination directory structure."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {'Content-Range': '0-9/10'}
        mock_resp.iter_content = MagicMock(return_value=[b'1234567890'])
        mock_get.return_value = mock_resp

        m = mock_open()
        with patch('builtins.open', m):
            f5functions.bigip_download_qkview(
                '192.0.2.1', 'admin', 'secret',
                'sample.qkview', local_filename='/custom/dir/sample.qkview', verify=False
            )
        mock_mkdirs.assert_called_once_with('/custom/dir', exist_ok=True)
        m.assert_called_once_with('/custom/dir/sample.qkview', 'wb')


if __name__ == '__main__':
    unittest.main()

