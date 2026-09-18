"""Shared functions and CLI argument parsers for F5 support case creation tools.

This module provides reusable utilities for interacting with:
  - F5 BIG-IP devices via iControl REST (connectivity, QKView generation, download, and deletion).
  - F5 Identity Services via OAuth2 (supporting both Okta and Auth0 per K000162308).
  - F5 iHealth API (connectivity, QKView metadata queries, and multipart uploads).
  - MyF5 Case Management API (listing cases, creating cases, adding comments, and metadata).
"""

import argparse
import configparser
import getpass
import logging
import os
import ssl
import sys
import uuid
import certifi
import requests
from requests.adapters import HTTPAdapter
import tqdm
import urllib3
from urllib3.exceptions import InsecureRequestWarning
from urllib3.util.ssl_ import create_urllib3_context

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Secure TLS 1.2+ and Modern PFS AEAD Cipher Suites
SECURE_CIPHERS = (
    'ECDHE-ECDSA-AES128-GCM-SHA256:'
    'ECDHE-RSA-AES128-GCM-SHA256:'
    'ECDHE-ECDSA-AES256-GCM-SHA384:'
    'ECDHE-RSA-AES256-GCM-SHA384:'
    'ECDHE-ECDSA-CHACHA20-POLY1305:'
    'ECDHE-RSA-CHACHA20-POLY1305:'
    'DHE-RSA-AES128-GCM-SHA256:'
    'DHE-RSA-AES256-GCM-SHA384'
)

# Legacy Okta Identity Endpoints (Pre-August 31, 2026; retirement end of September 2026 per K000162308)
OKTA_IDENTITY_FQDN = 'identity.account.f5.com'
MYF5_APP_ID = 'aus19gt5bu0jGw9Fi358'
IHEALTH_APP_ID = 'ausp95ykc80HOU7SQ357'

# Modern Auth0 Identity Endpoints (Post-August 31, 2026 per K000162308 / K15202)
AUTH0_IDENTITY_FQDN = 'idp.identity.f5.com'
AUTH0_TOKEN_PATH = '/oauth/token'

# Default Identity FQDN
IDENTITY_API_FQDN = OKTA_IDENTITY_FQDN

# API Endpoints
MYF5_API_FQDN = 'support.apis.f5.com'
MYF5_API_K_VALUE = os.getenv('F5_MYF5_API_K_VALUE', 'UKKD3Vxv7NHrM3QmYk8Fk2mZnLtljAKX')

IHEALTH_API_FQDN = 'ihealth2-api.f5.com'
IHEALTH_FALLBACK_API_FQDN = 'ihealth-api.f5.com'

logger = logging.getLogger(__name__)



# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _clean_fqdn(val, default=None):
    """Strip protocol schemes and trailing slashes from an FQDN or URL string.

    Args:
        val (str or None): The raw input FQDN or URL.
        default (str or None): Fallback default value if val is empty.

    Returns:
        str: Sanitized FQDN string (e.g. 'support.apis.f5.com').
    """
    if not val:
        return default
    return val.replace('https://', '').replace('http://', '').strip('/')


class SecureTLSAdapter(HTTPAdapter):
    """Transport adapter enforcing TLS 1.2 minimum, TLS 1.3 preferred, and modern AEAD ciphers."""

    def __init__(self, ssl_version=ssl.TLSVersion.TLSv1_2, ciphers=SECURE_CIPHERS, **kwargs):
        self.ssl_version = ssl_version
        self.ciphers = ciphers
        super().__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context(ciphers=self.ciphers)
        context.minimum_version = self.ssl_version
        kwargs['ssl_context'] = context
        return super().init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        context = create_urllib3_context(ciphers=self.ciphers)
        context.minimum_version = self.ssl_version
        kwargs['ssl_context'] = context
        return super().proxy_manager_for(*args, **kwargs)


def get_secure_session(verify=True):
    """Return a requests Session configured with modern TLS enforcement and trusted CAs.

    Args:
        verify (bool or str): True to verify against Mozilla CA bundle (certifi),
            or path to custom CA bundle file, or False to disable verification.

    Returns:
        requests.Session: Configured session enforcing TLS 1.2+ and AEAD ciphers.
    """
    session = requests.Session()
    if verify:
        adapter = SecureTLSAdapter()
        session.mount('https://', adapter)
        session.verify = certifi.where() if verify is True else verify
    else:
        session.verify = False
    return session


class MultipartProgressStream:
    """Streams a multipart form-data file upload with a real-time tqdm progress meter.

    Avoids buffering large files (e.g. 50MB-1GB QKViews) in memory and provides
    live progress, transfer rate, and ETA indicators during upload over the wire.
    """

    def __init__(self, field_name, file_path, desc=None):
        self.boundary = f'----WebKitFormBoundary{uuid.uuid4().hex}'
        self.content_type = f'multipart/form-data; boundary={self.boundary}'
        self.file_path = file_path
        try:
            self.file_size = os.path.getsize(file_path)
        except (OSError, TypeError):
            self.file_size = 0
        self.filename = os.path.basename(file_path)

        self.header = (
            f'--{self.boundary}\r\n'
            f'Content-Disposition: form-data; name="{field_name}"; filename="{self.filename}"\r\n'
            f'Content-Type: application/octet-stream\r\n\r\n'
        ).encode('utf-8')
        self.footer = f'\r\n--{self.boundary}--\r\n'.encode('utf-8')
        self.total_size = len(self.header) + self.file_size + len(self.footer)

        self._header_sent = 0
        self._file = open(file_path, 'rb')
        self._file_sent = 0
        self._footer_sent = 0

        self.pbar = tqdm.tqdm(
            total=self.file_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
            desc=desc or f'Uploading {self.filename}',
            miniters=1,
        )

    def __len__(self):
        return self.total_size

    def read(self, size=-1):
        if size == -1 or size is None:
            size = 65536

        # 1. Stream boundary header
        if self._header_sent < len(self.header):
            chunk = self.header[self._header_sent:self._header_sent + size]
            self._header_sent += len(chunk)
            return chunk

        # 2. Stream file content with live progress
        if self._file_sent < self.file_size or self.file_size == 0:
            to_read = min(size, self.file_size - self._file_sent) if self.file_size > 0 else size
            chunk = self._file.read(to_read)
            if chunk:
                self._file_sent += len(chunk)
                if self.pbar:
                    self.pbar.update(len(chunk))
                return chunk

        # 3. Stream boundary footer
        if self._footer_sent < len(self.footer):
            chunk = self.footer[self._footer_sent:self._footer_sent + size]
            self._footer_sent += len(chunk)
            return chunk

        return b''

    def close(self):
        if hasattr(self, 'pbar') and self.pbar:
            self.pbar.close()
        if hasattr(self, '_file') and self._file and not self._file.closed:
            self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ---------------------------------------------------------------------------
# Shared argument parsers
# ---------------------------------------------------------------------------

def resolve_bigip_username(username=None):
    """Resolve BIG-IP username safely from CLI argument, environment, or default.

    Order of resolution:
    1. Explicit username argument (if provided and non-empty)
    2. BIGIP_USERNAME, BIGIP_USER, or F5_USERNAME environment variable
    3. Default: 'admin'

    Args:
        username (str, optional): Username passed via CLI or function call.

    Returns:
        str: Resolved BIG-IP username.
    """
    if username:
        return username
    env_user = os.getenv('BIGIP_USERNAME') or os.getenv('BIGIP_USER') or os.getenv('F5_USERNAME')
    if env_user:
        return env_user.strip()
    return 'admin'


def resolve_bigip_credentials(host, username=None, password=None):
    """Resolve BIG-IP credentials safely from CLI, environment, or interactive prompt.

    Args:
        host (str): BIG-IP hostname or IP address.
        username (str, optional): Username (resolves via resolve_bigip_username if None).
        password (str, optional): Password passed via CLI.

    Returns:
        str: BIG-IP password.
    """
    resolved_user = resolve_bigip_username(username)
    if password:
        logger.warning(
            "Passing secrets via CLI arguments exposes them in process listings (ps) "
            "and shell history. Use BIGIP_PASSWORD environment variable or interactive entry instead."
        )
        return password

    env_pw = os.getenv('BIGIP_PASSWORD') or os.getenv('F5_PASSWORD')
    if env_pw:
        return env_pw

    if sys.stdin.isatty():
        prompt_str = f"Enter BIG-IP password for {resolved_user}@{host}: "
        entered = getpass.getpass(prompt_str).strip()
        if entered:
            return entered

    logger.error("BIG-IP password must be provided via BIGIP_PASSWORD environment variable or interactive prompt.")
    sys.exit(1)



def resolve_ihealth_credentials(client_id=None, client_secret=None, profile=None):
    """Resolve F5 / iHealth API credentials safely from CLI, environment, ~/.ihealth_credentials, or interactive prompt.

    Args:
        client_id (str, optional): Client ID from CLI.
        client_secret (str, optional): Client Secret from CLI.
        profile (str, optional): Profile name in ~/.ihealth_credentials.

    Returns:
        tuple[str, str]: (client_id, client_secret)
    """
    if client_id and client_secret:
        logger.warning(
            "Passing secrets via CLI arguments exposes them in process listings (ps) "
            "and shell history. Use environment variables (F5_CLIENT_ID, F5_CLIENT_SECRET), "
            "~/.ihealth_credentials, or interactive entry instead."
        )
        return client_id, client_secret

    env_id = client_id or os.getenv('F5_CLIENT_ID') or os.getenv('IHEALTH_CLIENT_ID')
    env_secret = client_secret or os.getenv('F5_CLIENT_SECRET') or os.getenv('IHEALTH_CLIENT_SECRET')

    for cred_path in [os.path.expanduser('~/.ihealth_credentials'), os.path.expanduser('~/.f5_credentials')]:
        if os.path.isfile(cred_path):
            try:
                cfg = configparser.ConfigParser()
                cfg.read(cred_path)
                target_section = None
                if profile and cfg.has_section(profile):
                    target_section = profile
                elif 'default' in cfg.sections():
                    target_section = 'default'
                elif cfg.sections():
                    target_section = cfg.sections()[0]

                if target_section:
                    sec = cfg[target_section]
                    if not env_id:
                        for k in ['clientid', 'client_id', 'client-id', 'id']:
                            if k in sec:
                                env_id = sec[k].strip()
                                break
                    if not env_secret:
                        for k in ['clientsecret', 'client_secret', 'client-secret', 'secret']:
                            if k in sec:
                                env_secret = sec[k].strip()
                                break
            except Exception as e:
                logger.debug("Failed to parse credentials file %s: %s", cred_path, e)

    if env_id and env_secret:
        return env_id, env_secret

    if sys.stdin.isatty():
        if not env_id:
            env_id = input("Enter F5 API Client ID: ").strip()
        if not env_secret:
            env_secret = getpass.getpass("Enter F5 API Client Secret: ").strip()
        if env_id and env_secret:
            return env_id, env_secret

    logger.error(
        "F5 API Client ID and Secret must be provided via environment variables "
        "(F5_CLIENT_ID, F5_CLIENT_SECRET), ~/.ihealth_credentials, or interactive prompt."
    )
    sys.exit(1)


def _bigip_base_parser():
    """Create the base argument parser for BIG-IP CLI commands.

    Returns:
        argparse.ArgumentParser: Parser configured with BIG-IP options.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, help="BIG-IP hostname or IP address", required=True)
    parser.add_argument(
        "--username",
        type=str,
        help="BIG-IP username (default: BIGIP_USERNAME env var or admin)",
        required=False,
        default=None,
    )
    parser.add_argument(
        "--password",
        type=str,
        help="BIG-IP password (optional; can be set via BIGIP_PASSWORD env var or prompt)",
        required=False,
        default=None,
    )
    parser.add_argument("--no-ssl-verify", action="store_true", help="Disable SSL certificate verification for BIG-IP", default=False)
    return parser


def bigip_args(*extra_args):
    """Parse base BIG-IP arguments alongside any tool-specific arguments.

    Args:
        *extra_args: Variable length tuples of (*args, **kwargs) passed to add_argument.

    Returns:
        argparse.Namespace: Parsed CLI options.
    """
    parser = _bigip_base_parser()
    for arg_args, arg_kwargs in extra_args:
        parser.add_argument(*arg_args, **arg_kwargs)
    parsed = parser.parse_args()
    parsed.username = resolve_bigip_username(parsed.username)
    parsed.password = resolve_bigip_credentials(parsed.host, parsed.username, parsed.password)
    return parsed



def _ihealth_base_parser():
    """Create the base argument parser for iHealth CLI commands.

    Returns:
        argparse.ArgumentParser: Parser configured with iHealth options.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--client-id', help='Support API Key / Client ID (optional; resolves from env or ~/.ihealth_credentials)', required=False, default=None)
    parser.add_argument('--client-secret', help='Support API Secret / Client Secret (optional; resolves from env or ~/.ihealth_credentials)', required=False, default=None)
    parser.add_argument('--profile', help='Profile/section name in ~/.ihealth_credentials', required=False, default=None)
    parser.add_argument('--app-id', help='Support App ID (default: outp95ykc80HOU7SQ357)', required=False, default=IHEALTH_APP_ID)
    parser.add_argument('--auth-url', help='Direct OAuth2 token URL override', required=False, default=None)
    parser.add_argument('--auth-fqdn', help=f'Identity Provider FQDN (default: {IDENTITY_API_FQDN})', required=False, default=IDENTITY_API_FQDN)
    parser.add_argument('--api-fqdn', help=f'iHealth API FQDN (default: {IHEALTH_API_FQDN})', required=False, default=IHEALTH_API_FQDN)
    return parser


def ihealth_args(*extra_args):
    """Parse base iHealth arguments alongside any tool-specific arguments.

    Args:
        *extra_args: Variable length tuples of (*args, **kwargs) passed to add_argument.

    Returns:
        argparse.Namespace: Parsed CLI options.
    """
    parser = _ihealth_base_parser()
    for arg_args, arg_kwargs in extra_args:
        parser.add_argument(*arg_args, **arg_kwargs)
    parsed = parser.parse_args()
    cid, csec = resolve_ihealth_credentials(parsed.client_id, parsed.client_secret, getattr(parsed, 'profile', None))
    parsed.client_id = cid
    parsed.client_secret = csec
    return parsed


def _myf5_base_parser():
    """Create the base argument parser for MyF5 CLI commands.

    Returns:
        argparse.ArgumentParser: Parser configured with MyF5 options.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--client-id', help='Support API Key / Client ID (optional; resolves from env or ~/.ihealth_credentials)', required=False, default=None)
    parser.add_argument('--client-secret', help='Support API Secret / Client Secret (optional; resolves from env or ~/.ihealth_credentials)', required=False, default=None)
    parser.add_argument('--profile', help='Profile/section name in ~/.ihealth_credentials', required=False, default=None)
    parser.add_argument('--app-id', type=str, help='Support App ID (default: aus19gt5bu0jGw9Fi358)', required=False, default=MYF5_APP_ID)
    parser.add_argument('--auth-url', help='Direct OAuth2 token URL override', required=False, default=None)
    parser.add_argument('--auth-fqdn', help=f'Identity Provider FQDN (default: {IDENTITY_API_FQDN})', required=False, default=IDENTITY_API_FQDN)
    parser.add_argument('--api-url', help=f'Support API FQDN or URL (default: {MYF5_API_FQDN})', required=False, default=MYF5_API_FQDN)
    parser.add_argument('--k-value', help='MyF5 Gateway API k value', required=False, default=MYF5_API_K_VALUE)
    return parser


def myf5_args(*extra_args):
    """Parse base MyF5 arguments alongside any tool-specific arguments.

    Args:
        *extra_args: Variable length tuples of (*args, **kwargs) passed to add_argument.

    Returns:
        argparse.Namespace: Parsed CLI options.
    """
    parser = _myf5_base_parser()
    for arg_args, arg_kwargs in extra_args:
        parser.add_argument(*arg_args, **arg_kwargs)
    parsed = parser.parse_args()
    cid, csec = resolve_ihealth_credentials(parsed.client_id, parsed.client_secret, getattr(parsed, 'profile', None))
    parsed.client_id = cid
    parsed.client_secret = csec
    return parsed



# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

def myf5_authenticate(app_id, client_id, client_secret, scope='myf5_scope', auth_url=None, auth_fqdn=IDENTITY_API_FQDN):
    """Authenticate against F5 Identity Services and retrieve a Bearer access token.

    Supports both legacy Okta authentication and modern Auth0 authentication per K000162308.

    Args:
        app_id (str): Authorization server app ID (for Okta).
        client_id (str): F5 Support API Client ID.
        client_secret (str): F5 Support API Client Secret.
        scope (str): OAuth2 scope ('myf5_scope' or 'ihealth').
        auth_url (str, optional): Explicit token endpoint URL override.
        auth_fqdn (str, optional): FQDN of the identity provider.

    Returns:
        str: OAuth2 Bearer access token string.

    Raises:
        SystemExit: If authentication fails or HTTP status is not 200.
    """
    response = myf5_retrieve_access_token(
        app_id, client_id, client_secret,
        scope=scope, auth_url=auth_url, auth_fqdn=auth_fqdn
    )
    if response.status_code != 200:
        if response.status_code in (401, 403):
            raise SystemExit(
                f'Failed to retrieve API Token (Status code: {response.status_code}).\n'
                f'Response: {response.text}\n'
                f'Note: F5 migrated its Identity Platform from Okta to Auth0 on August 31, 2026 (K000162308).\n'
                f'- If credentials have expired, generate new credentials in iHealth Settings or MyF5.\n'
                f'- For Auth0-issued credentials, specify --auth-fqdn idp.identity.f5.com or supply --auth-url.\n'
                f'- Verify firewall allowlists per K15202 (identity.account.f5.com and idp.identity.f5.com).'
            )
        raise SystemExit(f'Failed to retrieve API Token.\nStatus code: {response.status_code} Full response: {response.text}')
    print('Authentication successful.')
    return response.json()["access_token"]


# ---------------------------------------------------------------------------
# BIG-IP API functions
# ---------------------------------------------------------------------------

def _bigip_url(host, path):
    """Build an HTTPS URL targeting a BIG-IP host.

    Args:
        host (str): BIG-IP hostname or IP address.
        path (str): URI path starting with a forward slash.

    Returns:
        str: Fully qualified HTTPS URL.
    """
    return f'https://{host}{path}'


def _bigip_request(method, host, path, username, password, verify=True, **kwargs):
    """Execute an authenticated HTTP request against a BIG-IP device.

    Args:
        method (callable): Requests HTTP method function (e.g. requests.get, requests.post).
        host (str): BIG-IP hostname or IP.
        path (str): API endpoint path.
        username (str): BIG-IP admin username.
        password (str): BIG-IP admin password.
        verify (bool): Whether to verify SSL certificates (default: True).
        **kwargs: Additional arguments forwarded to requests method.

    Returns:
        requests.Response: HTTP response from BIG-IP.

    Raises:
        SystemExit: On network connection errors or unreachable host.
    """
    url = _bigip_url(host, path)
    if not verify:
        urllib3.disable_warnings(InsecureRequestWarning)
    try:
        return method(url, auth=(username, password), verify=verify, **kwargs)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)


def bigip_connectivity_test(host, username, password, verify=True):
    """Verify HTTP connectivity and authentication against BIG-IP system readiness.

    Args:
        host (str): BIG-IP hostname or IP.
        username (str): BIG-IP username.
        password (str): BIG-IP password.
        verify (bool): Whether to verify SSL certificates.

    Returns:
        requests.Response: HTTP response from /mgmt/tm/sys/ready.
    """
    return _bigip_request(
        requests.get, host, '/mgmt/tm/sys/ready',
        username, password, verify=verify,
        headers={'accept': 'application/json'}
    )


def bigip_generate_qkview(host, username, password, filename, no_truncate=False, verify=True):
    """Trigger QKView generation on a BIG-IP device.

    Args:
        host (str): BIG-IP hostname or IP.
        username (str): BIG-IP username.
        password (str): BIG-IP password.
        filename (str): Name of the QKView archive to produce.
        no_truncate (bool): When True, generates complete QKView via /mgmt/tm/util/qkview with -s0.
        verify (bool): Whether to verify SSL certificates.

    Returns:
        requests.Response: HTTP response containing task creation details.
    """
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
    """List all completed QKViews present on a BIG-IP device.

    Args:
        host (str): BIG-IP hostname or IP.
        username (str): BIG-IP username.
        password (str): BIG-IP password.
        verify (bool): Whether to verify SSL certificates.

    Returns:
        requests.Response: HTTP response containing JSON list of QKViews.
    """
    return _bigip_request(
        requests.get, host, '/mgmt/cm/autodeploy/qkview/',
        username, password, verify=verify,
        headers={'accept': 'application/json'}
    )


def bigip_query_qkview_task(host, username, password, task_id, verify=True):
    """Query the status of an ongoing QKView generation task on BIG-IP.

    Args:
        host (str): BIG-IP hostname or IP.
        username (str): BIG-IP username.
        password (str): BIG-IP password.
        task_id (str): The ID of the autodeploy qkview task.
        verify (bool): Whether to verify SSL certificates.

    Returns:
        requests.Response: HTTP response containing task status.
    """
    return _bigip_request(
        requests.get, host, f'/mgmt/cm/autodeploy/qkview/{task_id}',
        username, password, verify=verify,
        headers={'accept': 'application/json'}
    )


def bigip_download_qkview(host, username, password, filename, local_filename=None, verify=True):
    """Download a QKView file from BIG-IP using chunked HTTP Range requests.

    Args:
        host (str): BIG-IP hostname or IP.
        username (str): BIG-IP username.
        password (str): BIG-IP password.
        filename (str): Name of the remote QKView file on BIG-IP.
        local_filename (str, optional): Target local destination filename.
        verify (bool): Whether to verify SSL certificates.

    Raises:
        SystemExit: On missing Content-Range header or network failure.
    """
    url = _bigip_url(host, f'/mgmt/cm/autodeploy/qkview-downloads/{filename}')
    if not verify:
        urllib3.disable_warnings(InsecureRequestWarning)
    output_filename = os.path.basename(filename) if local_filename is None else local_filename
    out_dir = os.path.dirname(output_filename)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
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
                    desc=f'Downloading {os.path.basename(output_filename)}'
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
    """Delete a generated QKView from BIG-IP by filename.

    Args:
        host (str): BIG-IP hostname or IP.
        username (str): BIG-IP username.
        password (str): BIG-IP password.
        filename (str): Name of the QKView to locate and remove.
        verify (bool): Whether to verify SSL certificates.

    Returns:
        requests.Response: HTTP response from DELETE request.

    Raises:
        SystemExit: If listing fails or QKView filename is not found.
    """
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

def myf5_retrieve_access_token(app_id, client_id, client_secret, scope='myf5_scope',
                               auth_url=None, auth_fqdn=IDENTITY_API_FQDN):
    """Retrieve an OAuth2 token from F5 Identity services (Okta or Auth0).

    Args:
        app_id (str): Authorization server app ID (for Okta).
        client_id (str): F5 Support API Client ID.
        client_secret (str): F5 Support API Client Secret.
        scope (str): Token scope ('myf5_scope' or 'ihealth').
        auth_url (str, optional): Explicit token URL override.
        auth_fqdn (str, optional): Identity provider FQDN (default: identity.account.f5.com).

    Returns:
        requests.Response: HTTP response containing the OAuth2 token payload.

    Raises:
        SystemExit: If connection fails, citing K15202 firewall guidance.
    """
    clean_auth_fqdn = _clean_fqdn(auth_fqdn, default=IDENTITY_API_FQDN)
    if auth_url:
        url = auth_url
        payload = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
            'scope': scope
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        auth = None
    elif 'idp.identity.f5.com' in clean_auth_fqdn:
        url = f'https://{clean_auth_fqdn}{AUTH0_TOKEN_PATH}'
        payload = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
            'scope': scope
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        auth = None
    else:
        # Legacy Okta Authorization Server
        url = f'https://{clean_auth_fqdn}/oauth2/{app_id}/v1/token'
        payload = {'grant_type': 'client_credentials', 'scope': scope}
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        auth = requests.auth.HTTPBasicAuth(client_id, client_secret)

    session = get_secure_session(verify=True)
    try:
        return session.post(
            url,
            auth=auth,
            data=payload,
            headers=headers
        )
    except requests.exceptions.RequestException as e:
        raise SystemExit(
            f'Failed to connect to F5 Identity token endpoint ({url}): {e}\n'
            f'Note: Check firewall egress per K15202 (identity.account.f5.com and idp.identity.f5.com).'
        )


def myf5_list_support_cases(access_token, api_fqdn=MYF5_API_FQDN, k_value=MYF5_API_K_VALUE):
    """Retrieve existing support cases from MyF5 Case Management API.

    Args:
        access_token (str): Bearer access token.
        api_fqdn (str): MyF5 API FQDN (default: support.apis.f5.com).
        k_value (str): MyF5 client gateway key.

    Returns:
        requests.Response: HTTP response containing cases JSON list.

    Raises:
        SystemExit: On network request error.
    """
    fqdn = _clean_fqdn(api_fqdn, default=MYF5_API_FQDN)
    url = f'https://{fqdn}/case-management/v1/cases?type=ALL_CASES&k={k_value}'
    session = get_secure_session(verify=True)
    try:
        return session.get(url, headers={'accept': 'application/json', 'Authorization': f'Bearer {access_token}'})
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)


def myf5_create_new_support_case(access_token, json_payload, api_fqdn=MYF5_API_FQDN, k_value=MYF5_API_K_VALUE):
    """Submit a new support case creation request to MyF5.

    Args:
        access_token (str): Bearer access token.
        json_payload (dict): Structured case details matching MyF5 schema.
        api_fqdn (str): MyF5 API FQDN (default: support.apis.f5.com).
        k_value (str): MyF5 client gateway key.

    Returns:
        requests.Response: HTTP response containing created case number and details.

    Raises:
        SystemExit: On network request error.
    """
    fqdn = _clean_fqdn(api_fqdn, default=MYF5_API_FQDN)
    url = f'https://{fqdn}/case-management/v1/cases?k={k_value}'
    session = get_secure_session(verify=True)
    try:
        return session.post(
            url,
            headers={'content-type': 'application/json', 'accept': 'application/json', 'Authorization': f'Bearer {access_token}'},
            json=json_payload
        )
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)


def myf5_add_comments_to_existing_support_case(access_token, case_number, comments, api_fqdn=MYF5_API_FQDN, k_value=MYF5_API_K_VALUE):
    """Append text comments or notes to an existing MyF5 support case.

    Args:
        access_token (str): Bearer access token.
        case_number (str): Target F5 support case number.
        comments (str): Text comments to attach.
        api_fqdn (str): MyF5 API FQDN (default: support.apis.f5.com).
        k_value (str): MyF5 client gateway key.

    Returns:
        requests.Response: HTTP response from PATCH request.

    Raises:
        SystemExit: On network request error.
    """
    fqdn = _clean_fqdn(api_fqdn, default=MYF5_API_FQDN)
    url = f'https://{fqdn}/case-management/v1/cases/{case_number}?k={k_value}'
    session = get_secure_session(verify=True)
    try:
        return session.patch(
            url,
            headers={'content-type': 'application/json', 'accept': 'application/json', 'Authorization': f'Bearer {access_token}'},
            json={'comments': str(comments)}
        )
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)


def myf5_retrieve_case_creation_metadata(access_token, api_fqdn=MYF5_API_FQDN, k_value=MYF5_API_K_VALUE):
    """Retrieve metadata (allowed products, versions, severities) for MyF5 case creation.

    Args:
        access_token (str): Bearer access token.
        api_fqdn (str): MyF5 API FQDN (default: support.apis.f5.com).
        k_value (str): MyF5 client gateway key.

    Returns:
        requests.Response: HTTP response containing metadata JSON schema.

    Raises:
        SystemExit: On network request error.
    """
    fqdn = _clean_fqdn(api_fqdn, default=MYF5_API_FQDN)
    url = f'https://{fqdn}/case-management/v1/cases/metadata?k={k_value}'
    session = get_secure_session(verify=True)
    try:
        return session.get(url, headers={'accept': 'application/json', 'Authorization': f'Bearer {access_token}'})
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)


# Alias for backward compatibility and CLI convenience
myf5_add_comments = myf5_add_comments_to_existing_support_case


def myf5_connectivity_test(access_token, api_fqdn=MYF5_API_FQDN, k_value=MYF5_API_K_VALUE):
    """Test connectivity and authentication against MyF5 Support Case API.

    Args:
        access_token (str): Bearer access token.
        api_fqdn (str): MyF5 API FQDN (default: support.apis.f5.com).
        k_value (str): MyF5 client gateway key.

    Returns:
        bool: True if connectivity succeeds, False otherwise.
    """
    resp = myf5_retrieve_case_creation_metadata(access_token, api_fqdn=api_fqdn, k_value=k_value)
    if resp.status_code == 200:
        print("✓ Successfully connected and authenticated to MyF5 Support Case API.")
        return True
    print(f"✗ Failed to connect to MyF5 API: HTTP {resp.status_code} - {resp.text}")
    return False


# ---------------------------------------------------------------------------
# iHealth API functions
# ---------------------------------------------------------------------------

def ihealth_list_qkview_ids(access_token, api_fqdn=IHEALTH_API_FQDN):
    """Fetch the list of all QKView IDs uploaded to iHealth.

    Supports automatic fallback to secondary iHealth endpoint if primary fails.

    Args:
        access_token (str): Bearer access token.
        api_fqdn (str): iHealth API FQDN (default: ihealth2-api.f5.com).

    Returns:
        requests.Response: HTTP response containing JSON list of QKView IDs.

    Raises:
        SystemExit: On network request failure across primary and fallback endpoints.
    """
    fqdn = _clean_fqdn(api_fqdn, default=IHEALTH_API_FQDN)
    url = f'https://{fqdn}/qkview-analyzer/api/qkviews/'
    headers = {
        'accept': 'application/vnd.f5.ihealth.api.v1.0+json',
        'Authorization': f'Bearer {access_token}'
    }
    session = get_secure_session(verify=True)
    try:
        return session.get(url, headers=headers)
    except requests.exceptions.RequestException as e:
        if fqdn == IHEALTH_API_FQDN and IHEALTH_FALLBACK_API_FQDN:
            fallback_url = f'https://{IHEALTH_FALLBACK_API_FQDN}/qkview-analyzer/api/qkviews/'
            logger.warning('Failed to connect to %s (%s), falling back to %s', url, e, fallback_url)
            try:
                return session.get(fallback_url, headers=headers)
            except requests.exceptions.RequestException as fb_e:
                raise SystemExit(f'iHealth request failed on primary ({e}) and fallback ({fb_e})')
        raise SystemExit(e)


def ihealth_list_qkviews(access_token, api_fqdn=IHEALTH_API_FQDN):

    """Retrieve and display table of existing QKViews and diagnostics from F5 iHealth.

    Args:
        access_token (str): Bearer access token.
        api_fqdn (str): iHealth API FQDN.

    Returns:
        list[dict]: List of parsed QKView metadata dictionaries.
    """
    import datetime
    resp = ihealth_list_qkview_ids(access_token, api_fqdn=api_fqdn)
    if resp.status_code != 200:
        logger.error("Failed to retrieve QKView IDs: HTTP %s: %s", resp.status_code, resp.text)
        return []

    ids = resp.json().get("id", [])
    results = []
    for qkview_id in ids:
        meta_resp = ihealth_show_qkview_metadata(access_token, qkview_id, api_fqdn=api_fqdn)
        if meta_resp.status_code in (200, 202):
            data = meta_resp.json()
            results.append(data)
            proc_status = data.get("processing_status", "COMPLETE")
            print("*" * 90)
            print(f" QKView ID: {qkview_id} [Status: {proc_status}]")
            print(f" Hostname: {data.get('hostname') or 'N/A'}")
            print(f" File Name: {data.get('file_name') or 'N/A'}")
            print(f" Description: {data.get('description') or 'N/A'}")
            gen_date = data.get("generation_date")
            if gen_date:
                try:
                    created_date = datetime.datetime.fromtimestamp(gen_date / 1000).strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    created_date = str(gen_date)
            else:
                upload_date = (data.get("upload") or {}).get("date")
                if upload_date:
                    try:
                        created_date = datetime.datetime.fromtimestamp(upload_date / 1000).strftime('%Y-%m-%d %H:%M:%S')
                    except Exception:
                        created_date = str(upload_date)
                else:
                    created_date = "Processing..."
            print(f" Date: {created_date}")
            print(f" Chassis Serial: {data.get('chassis_serial') or 'N/A'}")
            print(f" Support Case: {data.get('f5_support_case') or 'N/A'}")
            print(f" URL: {data.get('gui_uri') or 'N/A'}")
            print("*" * 90)
    print(f"Total QKview IDs found: {len(ids)}")
    return results


def ihealth_show_qkview_metadata(access_token, qkview_id, api_fqdn=IHEALTH_API_FQDN):
    """Fetch diagnostic metadata for a specific QKView analysis on iHealth.

    Args:
        access_token (str): Bearer access token.
        qkview_id (str): The unique ID of the QKView on iHealth.
        api_fqdn (str): iHealth API FQDN (default: ihealth2-api.f5.com).

    Returns:
        requests.Response: HTTP response containing diagnostic metadata JSON.

    Raises:
        SystemExit: On network request failure.
    """
    fqdn = _clean_fqdn(api_fqdn, default=IHEALTH_API_FQDN)
    url = f'https://{fqdn}/qkview-analyzer/api/qkviews/{qkview_id}'
    headers = {
        'accept': 'application/vnd.f5.ihealth.api.v1.0+json',
        'Authorization': f'Bearer {access_token}'
    }
    session = get_secure_session(verify=True)
    try:
        return session.get(url, headers=headers)
    except requests.exceptions.RequestException as e:
        if fqdn == IHEALTH_API_FQDN and IHEALTH_FALLBACK_API_FQDN:
            fallback_url = f'https://{IHEALTH_FALLBACK_API_FQDN}/qkview-analyzer/api/qkviews/{qkview_id}'
            logger.warning('Failed to connect to %s (%s), falling back to %s', url, e, fallback_url)
            try:
                return session.get(fallback_url, headers=headers)
            except requests.exceptions.RequestException as fb_e:
                raise SystemExit(f'iHealth request failed on primary ({e}) and fallback ({fb_e})')
        raise SystemExit(e)


def ihealth_upload_qkview(access_token, filename, support_case_number='', api_fqdn=IHEALTH_API_FQDN):
    """Upload a local QKView file to iHealth for analysis.

    Args:
        access_token (str): Bearer access token.
        filename (str): Path to local *.qkview file to upload.
        support_case_number (str, optional): Support case number to associate with upload.
        api_fqdn (str): iHealth API FQDN (default: ihealth2-api.f5.com).

    Returns:
        requests.Response: HTTP response from iHealth upload endpoint.

    Raises:
        SystemExit: If file does not exist or network upload fails.
    """
    if not os.path.isfile(filename):
        raise SystemExit(f'File {filename} does not exist.')
    fqdn = _clean_fqdn(api_fqdn, default=IHEALTH_API_FQDN)
    url = f'https://{fqdn}/qkview-analyzer/api/qkviews'
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

    session = get_secure_session(verify=True)
    try:
        with MultipartProgressStream('qkview', filename, desc=f'Uploading {os.path.basename(filename)}') as stream:
            upload_headers = dict(headers)
            upload_headers['Content-Type'] = stream.content_type
            upload_headers['Content-Length'] = str(len(stream))
            return session.post(
                url,
                data=stream,
                headers=upload_headers,
                params=params
            )
    except requests.exceptions.RequestException as e:
        if fqdn == IHEALTH_API_FQDN and IHEALTH_FALLBACK_API_FQDN:
            fallback_url = f'https://{IHEALTH_FALLBACK_API_FQDN}/qkview-analyzer/api/qkviews'
            logger.warning('Failed to upload to %s (%s), falling back to %s', url, e, fallback_url)
            try:
                with MultipartProgressStream('qkview', filename, desc=f'Uploading {os.path.basename(filename)} (fallback)') as stream:
                    upload_headers = dict(headers)
                    upload_headers['Content-Type'] = stream.content_type
                    upload_headers['Content-Length'] = str(len(stream))
                    return session.post(
                        fallback_url,
                        data=stream,
                        headers=upload_headers,
                        params=params
                    )
            except requests.exceptions.RequestException as fb_e:
                raise SystemExit(f'iHealth upload failed on primary ({e}) and fallback ({fb_e})')
        raise SystemExit(e)


def ihealth_connectivity_test(access_token, api_fqdn=IHEALTH_API_FQDN):
    """Test connectivity and authentication against F5 iHealth API.

    Args:
        access_token (str): Bearer access token.
        api_fqdn (str): iHealth API FQDN (default: ihealth2-api.f5.com).

    Returns:
        bool: True if connectivity and authentication succeed, False otherwise.
    """
    resp = ihealth_list_qkview_ids(access_token, api_fqdn=api_fqdn)
    if resp.status_code == 200:
        print("✓ Successfully connected and authenticated to F5 iHealth API.")
        return True
    print(f"✗ Failed to connect to F5 iHealth API: HTTP {resp.status_code} - {resp.text}")
    return False

