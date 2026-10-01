"""Unit tests for MyF5 Downloads API integration and credential resolution.

Verifies:
  1. Base URL defaults to api.software.downloads.f5.com per the October 2 announcement.
  2. Removal of the 'k' query parameter from all Downloads API calls.
  3. Correct REST endpoints for metadata, product versions, and download file links.
  4. File download streaming with chunking, tqdm progress, and cryptographic checksum validation.
  5. Reading F5 API credentials from ~/.f5api_credentials in KEY=VALUE format.
  6. Subcommand parsing and execution in qkviewmgr downloads.
"""

import contextlib
import hashlib
import importlib
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

_src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

import f5functions
from qkviewmgr import qkviewmgr


class TestMyF5Downloads(unittest.TestCase):
    """Test suite for MyF5 Downloads API and credential resolution."""

    def test_myf5_downloads_api_fqdn_default(self):
        """Verify that default Downloads API FQDN matches the October 2 announcement."""
        self.assertEqual(f5functions.MYF5_DOWNLOADS_API_FQDN, "api.software.downloads.f5.com")

    def test_myf5_downloads_api_fqdn_env_override(self):
        """Verify that F5_MYF5_DOWNLOADS_API_FQDN overrides the default endpoint."""
        with mock.patch.dict(os.environ, {"F5_MYF5_DOWNLOADS_API_FQDN": "custom-downloads.f5.com"}):
            importlib.reload(f5functions)
            self.assertEqual(f5functions.MYF5_DOWNLOADS_API_FQDN, "custom-downloads.f5.com")
        importlib.reload(f5functions)

    @mock.patch("f5functions.get_secure_session")
    def test_myf5_get_downloads_metadata(self, mock_session_cls):
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

        self.assertEqual(resp.status_code, 200)
        mock_session.get.assert_called_once()
        called_url = mock_session.get.call_args[0][0]
        called_kwargs = mock_session.get.call_args[1]

        self.assertEqual(
            "https://api.software.downloads.f5.com/downloads-management/v1/downloads/metadata",
            called_url
        )
        self.assertNotIn("k=", called_url)
        self.assertTrue("params" not in called_kwargs or "k" not in called_kwargs.get("params", {}))
        self.assertEqual(called_kwargs["headers"]["Authorization"], "Bearer test-token-123")
        self.assertEqual(called_kwargs["headers"]["accept"], "application/json")

    @mock.patch("f5functions.get_secure_session")
    def test_myf5_get_product_versions(self, mock_session_cls):
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

        self.assertEqual(resp.status_code, 200)
        called_url = mock_session.get.call_args[0][0]
        called_kwargs = mock_session.get.call_args[1]

        expected_url = "https://api.software.downloads.f5.com/downloads-management/v1/downloads/product/BIG-IP/big-ip_v16.x"
        self.assertEqual(called_url, expected_url)
        self.assertNotIn("k=", called_url)
        self.assertTrue("params" not in called_kwargs or "k" not in called_kwargs.get("params", {}))
        self.assertEqual(called_kwargs["headers"]["Authorization"], "Bearer test-token-abc")

    @mock.patch("f5functions.get_secure_session")
    def test_myf5_get_download_file_links(self, mock_session_cls):
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

        self.assertEqual(resp.status_code, 200)
        called_url = mock_session.get.call_args[0][0]
        called_kwargs = mock_session.get.call_args[1]

        expected_url = (
            "https://api.software.downloads.f5.com/downloads-management/v1/downloads/product/"
            "BIG-IP/big-ip_v16.x/16.1.2/english/16.1.2/BIGIP-16.1.2-0.0.18.iso"
        )
        self.assertEqual(called_url, expected_url)
        self.assertNotIn("k=", called_url)
        self.assertTrue("params" not in called_kwargs or "k" not in called_kwargs.get("params", {}))

    @mock.patch("f5functions.get_secure_session")
    def test_myf5_download_file_success(self, mock_session_cls):
        """Verify chunked download with successful SHA-256 integrity verification."""
        mock_session = mock.MagicMock()
        content = b"Mock F5 BIG-IP ISO File Content Here..."
        expected_sha256 = hashlib.sha256(content).hexdigest()

        mock_resp = mock.MagicMock(status_code=200)
        mock_resp.headers = {"content-length": str(len(content))}
        mock_resp.iter_content.return_value = [content[:10], content[10:]]
        mock_session.get.return_value = mock_resp
        mock_session_cls.return_value = mock_session

        with tempfile.TemporaryDirectory() as tmp_dir:
            dest_file = os.path.join(tmp_dir, "test_image.iso")
            result = f5functions.myf5_download_file(
                "https://downloads.f5.com/s3/test_image.iso",
                dest_file,
                expected_checksum=expected_sha256,
                checksum_algo="sha256"
            )

            self.assertEqual(result, dest_file)
            with open(dest_file, "rb") as f:
                self.assertEqual(f.read(), content)

    @mock.patch("f5functions.get_secure_session")
    def test_myf5_download_file_checksum_mismatch(self, mock_session_cls):
        """Verify that myf5_download_file raises ValueError when hash mismatch is detected."""
        mock_session = mock.MagicMock()
        content = b"Corrupted download chunk data"
        wrong_hash = "0000000000000000000000000000000000000000000000000000000000000000"

        mock_resp = mock.MagicMock(status_code=200)
        mock_resp.headers = {"content-length": str(len(content))}
        mock_resp.iter_content.return_value = [content]
        mock_session.get.return_value = mock_resp
        mock_session_cls.return_value = mock_session

        with tempfile.TemporaryDirectory() as tmp_dir:
            dest_file = os.path.join(tmp_dir, "bad_image.iso")
            with self.assertRaises(ValueError) as cm:
                f5functions.myf5_download_file(
                    "https://downloads.f5.com/s3/bad_image.iso",
                    dest_file,
                    expected_checksum=wrong_hash,
                    checksum_algo="sha256"
                )
            self.assertIn("Checksum mismatch", str(cm.exception))

    @mock.patch("f5functions.get_secure_session")
    def test_myf5_download_file_http_error(self, mock_session_cls):
        """Verify that myf5_download_file raises RuntimeError on HTTP error status."""
        mock_session = mock.MagicMock()
        mock_resp = mock.MagicMock(status_code=403, text="Access Denied")
        mock_session.get.return_value = mock_resp
        mock_session_cls.return_value = mock_session

        with tempfile.TemporaryDirectory() as tmp_dir:
            dest_file = os.path.join(tmp_dir, "error_image.iso")
            with self.assertRaises(RuntimeError) as cm:
                f5functions.myf5_download_file(
                    "https://downloads.f5.com/s3/error_image.iso",
                    dest_file
                )
            self.assertIn("Download failed: HTTP 403", str(cm.exception))

    def test_resolve_credentials_from_f5api_credentials_key_value(self):
        """Verify resolution of client_id and client_secret from ~/.f5api_credentials in KEY=VALUE format."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            f5api_file = os.path.join(tmp_dir, ".f5api_credentials")
            with open(f5api_file, "w") as f:
                f.write(
                    "# F5 Support API Credentials\n"
                    "client_id=my-f5-api-id-123\n"
                    "client_secret=my-f5-api-secret-456\n"
                    "username=admin\n"
                )

            with mock.patch("os.path.expanduser", side_effect=lambda p: f5api_file if ".f5api_credentials" in p else "/nonexistent"):
                with mock.patch.dict(os.environ, {}, clear=True):
                    cid, csec = f5functions.resolve_ihealth_credentials()
                    self.assertEqual(cid, "my-f5-api-id-123")
                    self.assertEqual(csec, "my-f5-api-secret-456")

                    # Check alias
                    m_cid, m_csec = f5functions.resolve_myf5_credentials()
                    self.assertEqual(m_cid, cid)
                    self.assertEqual(m_csec, csec)

    def test_resolve_credentials_from_f5api_credentials_quoted_values(self):
        """Verify resolution from ~/.f5api_credentials when values are quoted."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            f5api_file = os.path.join(tmp_dir, ".f5api_credentials")
            with open(f5api_file, "w") as f:
                f.write(
                    'client_id="quoted-id-999"\n'
                    "client_secret='quoted-secret-888'\n"
                )

            with mock.patch("os.path.expanduser", side_effect=lambda p: f5api_file if ".f5api_credentials" in p else "/nonexistent"):
                with mock.patch.dict(os.environ, {}, clear=True):
                    cid, csec = f5functions.resolve_ihealth_credentials()
                    self.assertEqual(cid, "quoted-id-999")
                    self.assertEqual(csec, "quoted-secret-888")

    @mock.patch("f5functions.myf5_authenticate", return_value="fake-token")
    @mock.patch("f5functions.resolve_ihealth_credentials", return_value=("id", "sec"))
    @mock.patch("f5functions.myf5_get_downloads_metadata")
    def test_cmd_downloads_metadata(self, mock_meta, mock_creds, mock_auth):
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
            with io.StringIO() as buf, contextlib.redirect_stdout(buf):
                qkviewmgr.main()
                out = buf.getvalue()

        self.assertIn("Available Product Families", out)
        self.assertIn("BIG-IP", out)
        self.assertIn("big-ip_v16.x", out)
        mock_meta.assert_called_once_with("fake-token", api_fqdn=f5functions.MYF5_DOWNLOADS_API_FQDN)

    @mock.patch("f5functions.myf5_download_file")
    def test_cmd_downloads_get_url(self, mock_download):
        """Verify 'qkviewmgr downloads get --url ...' downloads directly without requiring credentials."""
        mock_download.return_value = "my_image.iso"

        test_args = [
            "qkviewmgr", "downloads", "get",
            "--url", "https://downloads.f5.com/s3/my_image.iso",
            "--output", "my_image.iso",
            "--checksum", "123456"
        ]
        with mock.patch("sys.argv", test_args):
            with io.StringIO() as buf, contextlib.redirect_stdout(buf):
                qkviewmgr.main()
                out = buf.getvalue()

        self.assertIn("Initiating direct", out)
        self.assertIn("my_image.iso", out)
        mock_download.assert_called_once_with(
            "https://downloads.f5.com/s3/my_image.iso",
            "my_image.iso",
            expected_checksum="123456",
            checksum_algo="sha256"
        )

    @mock.patch("f5functions.myf5_authenticate", return_value="fake-token")
    @mock.patch("f5functions.resolve_ihealth_credentials", return_value=("fake_cid", "fake_csec"))
    @mock.patch("f5functions.myf5_get_product_versions")
    def test_cmd_downloads_versions_geoip(self, mock_ver, mock_creds, mock_auth):
        """Verify 'qkviewmgr downloads versions' handles root-level versions (GeoIP schema)."""
        mock_resp = mock.MagicMock(status_code=200)
        mock_resp.json.return_value = {
            "family": "BIG-IP_Next",
            "product": "GeoIP_Updates",
            "versions": [
                {
                    "version": "1.0.0",
                    "releaseDate": "2026-09-29",
                    "containers": [
                        {
                            "container": "GeoIP_Updates",
                            "files": [
                                {"filename": "ip-geolocation-v3-20260928.zip", "bytes": "10661336"}
                            ]
                        }
                    ]
                }
            ]
        }
        mock_ver.return_value = mock_resp

        test_args = [
            "qkviewmgr", "downloads", "versions",
            "--product-family", "BIG-IP_Next",
            "--product-line", "GeoIP_Updates"
        ]
        with mock.patch("sys.argv", test_args):
            with io.StringIO() as buf, contextlib.redirect_stdout(buf):
                qkviewmgr.main()
                out = buf.getvalue()

        self.assertIn("Product: BIG-IP_Next / GeoIP_Updates", out)
        self.assertIn("Version: 1.0.0", out)
        self.assertIn("GeoIP_Updates", out)
        self.assertIn("ip-geolocation-v3-20260928.zip", out)

    @mock.patch("f5functions.myf5_authenticate", return_value="fake-token")
    @mock.patch("f5functions.resolve_ihealth_credentials", return_value=("fake_cid", "fake_csec"))
    @mock.patch("f5functions.myf5_get_download_file_links")
    def test_cmd_downloads_links_geoip(self, mock_links, mock_creds, mock_auth):
        """Verify 'qkviewmgr downloads links' handles root-level downloadLinks and location mirrors."""
        mock_resp = mock.MagicMock(status_code=200)
        mock_resp.json.return_value = {
            "downloadLinks": [
                {"hosting": "AWS", "href": "https://s3.amazonaws.com/geoip.zip", "location": "USA - WEST COAST"}
            ],
            "meta": {
                "sha256": "abc123sha256"
            }
        }
        mock_links.return_value = mock_resp

        test_args = [
            "qkviewmgr", "downloads", "links",
            "--product-family", "BIG-IP_Next",
            "--product-line", "GeoIP_Updates",
            "--product-version", "1.0.0",
            "--container", "GeoIP_Updates",
            "--file-name", "ip-geolocation-v3-20260928.zip"
        ]
        with mock.patch("sys.argv", test_args):
            with io.StringIO() as buf, contextlib.redirect_stdout(buf):
                qkviewmgr.main()
                out = buf.getvalue()

        self.assertIn("Download Links for ip-geolocation-v3-20260928.zip", out)
        self.assertIn("USA - WEST COAST", out)
        self.assertIn("abc123sha256", out)


if __name__ == "__main__":
    unittest.main()
