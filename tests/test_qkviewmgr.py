"""Unit tests for qkviewmgr CLI dispatcher and Auto-Pilot orchestrator."""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "qkviewmgr"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
import qkviewmgr
import f5functions



class TestQKViewMgr(unittest.TestCase):
    """Test suite for unified qkviewmgr CLI commands."""

    @patch("f5functions.get_secure_session")
    def test_cmd_doctor(self, mock_session):
        """Verify doctor diagnostic check queries runtime and endpoints."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp
        mock_session.return_value = mock_client

        args = MagicMock()
        with patch("sys.stdout"):
            qkviewmgr.cmd_doctor(args)

        self.assertGreaterEqual(mock_client.get.call_count, 3)

    @patch("f5functions.bigip_connectivity_test")
    def test_cmd_bigip_test(self, mock_test):
        """Verify bigip test action invokes bigip_connectivity_test."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_test.return_value = mock_resp

        args = MagicMock()
        args.action = "test"
        args.host = "192.0.2.1"
        args.username = "admin"
        args.password = "secret"
        args.no_ssl_verify = True

        with patch("sys.stdout"):
            qkviewmgr.cmd_bigip(args)

        mock_test.assert_called_once_with("192.0.2.1", "admin", "secret", verify=False)

    @patch("f5functions.ihealth_list_qkviews")
    @patch("f5functions.myf5_authenticate", return_value="tok123")
    @patch("f5functions.resolve_ihealth_credentials", return_value=("cid", "csec"))
    def test_cmd_ihealth_list(self, mock_creds, mock_auth, mock_list):
        """Verify ihealth list action resolves credentials and calls list."""
        args = MagicMock()
        args.action = "list"
        args.client_id = None
        args.client_secret = None
        args.profile = None
        args.app_id = None

        with patch("sys.stdout"):
            qkviewmgr.cmd_ihealth(args)

        mock_creds.assert_called_once()
        mock_auth.assert_called_once_with(f5functions.IHEALTH_APP_ID, "cid", "csec", scope="ihealth")
        mock_list.assert_called_once_with("tok123")

    @patch("f5functions.ihealth_upload_qkview")
    @patch("f5functions.bigip_delete_qkview")
    @patch("f5functions.bigip_download_qkview")
    @patch("f5functions.bigip_generate_qkview")
    @patch("f5functions.bigip_connectivity_test")
    @patch("f5functions.myf5_authenticate", return_value="tok123")
    @patch("f5functions.resolve_ihealth_credentials", return_value=("cid", "csec"))
    @patch("f5functions.resolve_bigip_credentials", return_value="pw123")
    @patch("os.path.getsize", return_value=1048576)
    def test_cmd_auto_pilot_flow(
        self, mock_size, mock_bigip_pw, mock_ih_creds, mock_auth,
        mock_test, mock_gen, mock_down, mock_del, mock_upload
    ):
        """Verify full 5-step Auto-Pilot pipeline execution."""
        mock_upload_resp = MagicMock()
        mock_upload_resp.status_code = 200
        mock_upload_resp.json.return_value = {"id": "qv999"}
        mock_upload.return_value = mock_upload_resp

        args = MagicMock()
        args.host = "bigip.local"
        args.username = "admin"
        args.password = None
        args.no_ssl_verify = True
        args.qkview_name = "test.qkview"
        args.output_dir = "."
        args.no_truncate = False
        args.no_delete_remote = False
        args.no_upload = False
        args.case_number = "C12345"
        args.description = "Auto diag"
        args.no_wait = True
        args.client_id = None
        args.client_secret = None
        args.profile = None

        with patch("sys.stdout"):
            qkviewmgr.cmd_auto_pilot(args)

        mock_test.assert_called_once_with("bigip.local", "admin", "pw123", verify=False)
        mock_gen.assert_called_once_with("bigip.local", "admin", "pw123", "test.qkview", no_truncate=False, verify=False)
        mock_down.assert_called_once_with("bigip.local", "admin", "pw123", "test.qkview", os.path.join(".", "test.qkview"), verify=False)
        mock_del.assert_called_once_with("bigip.local", "admin", "pw123", "test.qkview", verify=False)
        mock_upload.assert_called_once()


if __name__ == "__main__":
    unittest.main()
