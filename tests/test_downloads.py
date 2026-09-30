"""Unit tests for MyF5 Downloads API integration and credential resolution.

Verifies:
  1. Base URL defaults to api.software.downloads.f5.com per the October 2 announcement.
  2. Removal of the 'k' query parameter from all Downloads API calls.
  3. Correct REST endpoints for metadata, product versions, and download file links.
  4. File download streaming with chunking, tqdm progress, and cryptographic checksum validation.
  5. Reading F5 API credentials from ~/.f5api_credentials in KEY=VALUE format.
  6. Subcommand parsing and execution in qkviewmgr downloads.
"""

import hashlib
import io
import json
import os
import sys
import tempfile
from unittest import mock
import pytest
import requests

_src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

import f5functions
from qkviewmgr import qkviewmgr


# ---------------------------------------------------------------------------
# Constant and URL Configuration Tests
# ---------------------------------------------------------------------------

def test_myf5_downloads_api_fqdn_default():
    """Verify that default Downloads API FQDN matches the October 2 announcement."""
    assert f5functions.MYF5_DOWNLOADS_API_FQDN == "api.software.downloads.f5.com"


def test_myf5_downloads_api_fqdn_env_override():
    """Verify that F5_MYF5_DOWNLOADS_API_FQDN overrides the default endpoint."""
    with mock.patch.dict(os.environ, {"F5_MYF5_DOWNLOADS_API_FQDN": "custom-downloads.f5.com"}):
        import importlib
        importlib.reload(f5functions)
        assert f5functions.MYF5_DOWNLOADS_API_FQDN == "custom-downloads.f5.com"
    # Restore
    importlib.reload(f5functions)


# ---------------------------------------------------------------------------
# API Client Tests (Verifying NO 'k' parameter is ever sent)
# ---------------------------------------------------------------------------

@mock.patch("f5functions.get_secure_session")
def test_myf5_get_downloads_metadata(mock_session_cls):
    """Verify myf5_get_downloads_metadata targets api.software.downloads.f5.com without 'k' param."""
    mock_session = mock.MagicMock()
    mock_resp = mock.MagicMock(status_code=200)
    mock_resp.json.return_value = {
        "data": {
            "productFamilies": [
                {"name": "BIG-IP", "productLines": [{"name": "big-ip_v16.x", "displayName": "BIG-IP v16.x"}]}
            ]
        }
    }
    mock_session.get.return_value = mock_resp
    mock_session_cls.return_value = mock_session

    token = "test-token-123"
    resp = f5functions.myf5_get_downloads_metadata(token)

    assert resp.status_code == 200
    mock_session.get.assert_called_once()
    called_url = mock_session.get.call_args[0][0]
    called_kwargs = mock_session.get.call_args[1]

    # Check URL structure and assert NO 'k' query param exists
    assert "https://api.software.downloads.f5.com/downloads-management/v1/downloads/metadata" == called_url
    assert "k=" not in called_url
    assert "params" not in called_kwargs or "k" not in called_kwargs.get("params", {})
    assert called_kwargs["headers"]["Authorization"] == "Bearer test-token-123"
    assert called_kwargs["headers"]["accept"] == "application/json"


@mock.patch("f5functions.get_secure_session")
def test_myf5_get_product_versions(mock_session_cls):
    """Verify myf5_get_product_versions targets correct path without 'k' parameter."""
    mock_session = mock.MagicMock()
    mock_resp = mock.MagicMock(status_code=200)
    mock_resp.json.return_value = {
        "family": "BIG-IP",
        "product": "big-ip_v16.x",
        "versions": [{"version": "16.1.2", "containers": []}]
    }
    mock_session.get.return_value = mock_resp
    mock_session_cls.return_value = mock_session

    token = "test-token-abc"
    resp = f5functions.myf5_get_product_versions(token, "BIG-IP", "big-ip_v16.x")

    assert resp.status_code == 200
    called_url = mock_session.get.call_args[0][0]
    called_kwargs = mock_session.get.call_args[1]

    expected_url = "https://api.software.downloads.f5.com/downloads-management/v1/downloads/product/BIG-IP/big-ip_v16.x"
    assert called_url == expected_url
    assert "k=" not in called_url
    assert "params" not in called_kwargs or "k" not in called_kwargs.get("params", {})
    assert called_kwargs["headers"]["Authorization"] == "Bearer test-token-abc"


@mock.patch("f5functions.get_secure_session")
def test_myf5_get_download_file_links(mock_session_cls):
    """Verify myf5_get_download_file_links targets correct path without 'k' parameter."""
    mock_session = mock.MagicMock()
    mock_resp = mock.MagicMock(status_code=200)
    mock_resp.json.return_value = {
        "downloadLinks": [{"href": "https://downloads.f5.com/s3/BIGIP-16.1.2.iso"}],
        "meta": {"sha256": "fakehash256", "md5": "fakehashmd5"}
    }
    mock_session.get.return_value = mock_resp
    mock_session_cls.return_value = mock_session

    token = "test-token-xyz"
    resp = f5functions.myf5_get_download_file_links(
        token, "BIG-IP", "big-ip_v16.x", "16.1.2", "16.1.2", "BIGIP-16.1.2-0.0.18.iso"
    )

    assert resp.status_code == 200
    called_url = mock_session.get.call_args[0][0]
    called_kwargs = mock_session.get.call_args[1]

    expected_url = (
        "https://api.software.downloads.f5.com/downloads-management/v1/downloads/product/"
        "BIG-IP/big-ip_v16.x/16.1.2/english/16.1.2/BIGIP-16.1.2-0.0.18.iso"
    )
    assert called_url == expected_url
    assert "k=" not in called_url
    assert "params" not in called_kwargs or "k" not in called_kwargs.get("params", {})


# ---------------------------------------------------------------------------
# File Download & Checksum Integrity Tests
# ---------------------------------------------------------------------------

@mock.patch("f5functions.get_secure_session")
def test_myf5_download_file_success(mock_session_cls, tmp_path):
    """Verify chunked download with successful SHA-256 integrity verification."""
    mock_session = mock.MagicMock()
    content = b"Mock F5 BIG-IP ISO File Content Here..."
    expected_sha256 = hashlib.sha256(content).hexdigest()

    mock_resp = mock.MagicMock(status_code=200)
    mock_resp.headers = {"content-length": str(len(content))}
    mock_resp.iter_content.return_value = [content[:10], content[10:]]
    mock_session.get.return_value = mock_resp
    mock_session_cls.return_value = mock_session

    dest_file = tmp_path / "test_image.iso"
    result = f5functions.myf5_download_file(
        "https://downloads.f5.com/s3/test_image.iso",
        str(dest_file),
        expected_checksum=expected_sha256,
        checksum_algo="sha256"
    )

    assert result == str(dest_file)
    assert dest_file.read_bytes() == content


@mock.patch("f5functions.get_secure_session")
def test_myf5_download_file_checksum_mismatch(mock_session_cls, tmp_path):
    """Verify that myf5_download_file raises ValueError when hash mismatch is detected."""
    mock_session = mock.MagicMock()
    content = b"Corrupted download chunk data"
    wrong_hash = "0000000000000000000000000000000000000000000000000000000000000000"

    mock_resp = mock.MagicMock(status_code=200)
    mock_resp.headers = {"content-length": str(len(content))}
    mock_resp.iter_content.return_value = [content]
    mock_session.get.return_value = mock_resp
    mock_session_cls.return_value = mock_session

    dest_file = tmp_path / "bad_image.iso"
    with pytest.raises(ValueError, match="Checksum mismatch"):
        f5functions.myf5_download_file(
            "https://downloads.f5.com/s3/bad_image.iso",
            str(dest_file),
            expected_checksum=wrong_hash,
            checksum_algo="sha256"
        )


@mock.patch("f5functions.get_secure_session")
def test_myf5_download_file_http_error(mock_session_cls, tmp_path):
    """Verify that myf5_download_file raises RuntimeError on HTTP error status."""
    mock_session = mock.MagicMock()
    mock_resp = mock.MagicMock(status_code=403, text="Access Denied")
    mock_session.get.return_value = mock_resp
    mock_session_cls.return_value = mock_session

    dest_file = tmp_path / "error_image.iso"
    with pytest.raises(RuntimeError, match="Download failed: HTTP 403"):
        f5functions.myf5_download_file(
            "https://downloads.f5.com/s3/error_image.iso",
            str(dest_file)
        )


# ---------------------------------------------------------------------------
# ~/.f5api_credentials KEY=VALUE Resolution Tests
# ---------------------------------------------------------------------------

def test_resolve_credentials_from_f5api_credentials_key_value(tmp_path):
    """Verify resolution of client_id and client_secret from ~/.f5api_credentials in KEY=VALUE format."""
    f5api_file = tmp_path / ".f5api_credentials"
    f5api_file.write_text(
        "# F5 Support API Credentials\n"
        "client_id=my-f5-api-id-123\n"
        "client_secret=my-f5-api-secret-456\n"
        "username=admin\n"
    )

    with mock.patch("os.path.expanduser", side_effect=lambda p: str(f5api_file) if ".f5api_credentials" in p else "/nonexistent"):
        with mock.patch.dict(os.environ, {}, clear=True):
            cid, csec = f5functions.resolve_ihealth_credentials()
            assert cid == "my-f5-api-id-123"
            assert csec == "my-f5-api-secret-456"

            # Check alias
            m_cid, m_csec = f5functions.resolve_myf5_credentials()
            assert m_cid == cid
            assert m_csec == csec


def test_resolve_credentials_from_f5api_credentials_quoted_values(tmp_path):
    """Verify resolution from ~/.f5api_credentials when values are quoted."""
    f5api_file = tmp_path / ".f5api_credentials"
    f5api_file.write_text(
        'client_id="quoted-id-999"\n'
        "client_secret='quoted-secret-888'\n"
    )

    with mock.patch("os.path.expanduser", side_effect=lambda p: str(f5api_file) if ".f5api_credentials" in p else "/nonexistent"):
        with mock.patch.dict(os.environ, {}, clear=True):
            cid, csec = f5functions.resolve_ihealth_credentials()
            assert cid == "quoted-id-999"
            assert csec == "quoted-secret-888"


# ---------------------------------------------------------------------------
# CLI Command Dispatcher Tests
# ---------------------------------------------------------------------------

@mock.patch("f5functions.myf5_authenticate", return_value="fake-token")
@mock.patch("f5functions.resolve_ihealth_credentials", return_value=("id", "sec"))
@mock.patch("f5functions.myf5_get_downloads_metadata")
def test_cmd_downloads_metadata(mock_meta, mock_creds, mock_auth, capsys):
    """Verify 'qkviewmgr downloads metadata' CLI command."""
    mock_resp = mock.MagicMock(status_code=200)
    mock_resp.json.return_value = {
        "data": {
            "productFamilies": [
                {"name": "BIG-IP", "productLines": [{"name": "big-ip_v16.x", "displayName": "BIG-IP v16.x"}]}
            ]
        }
    }
    mock_meta.return_value = mock_resp

    test_args = ["qkviewmgr", "downloads", "metadata"]
    with mock.patch("sys.argv", test_args):
        qkviewmgr.main()

    out, _ = capsys.readouterr()
    assert "Available Product Families" in out
    assert "BIG-IP" in out
    assert "big-ip_v16.x" in out
    mock_meta.assert_called_once_with("fake-token", api_fqdn=f5functions.MYF5_DOWNLOADS_API_FQDN)


@mock.patch("f5functions.myf5_download_file")
def test_cmd_downloads_get_url(mock_download, capsys):
    """Verify 'qkviewmgr downloads get --url ...' downloads directly without requiring credentials."""
    mock_download.return_value = "my_image.iso"

    test_args = [
        "qkviewmgr", "downloads", "get",
        "--url", "https://downloads.f5.com/s3/my_image.iso",
        "--output", "my_image.iso",
        "--checksum", "123456"
    ]
    with mock.patch("sys.argv", test_args):
        qkviewmgr.main()

    out, _ = capsys.readouterr()
    assert "Initiating direct" in out
    assert "my_image.iso" in out
    mock_download.assert_called_once_with(
        "https://downloads.f5.com/s3/my_image.iso",
        "my_image.iso",
        expected_checksum="123456",
        checksum_algo="sha256"
    )
