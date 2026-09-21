"""Unit tests for qkviewmgr CLI dispatcher and Auto-Pilot orchestrator."""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

_src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

import qkviewmgr.qkviewmgr as qkviewmgr
import qkviewmgr.f5functions as f5functions
sys.modules['qkviewmgr'] = qkviewmgr
sys.modules['f5functions'] = f5functions



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

    @patch("f5functions.bigip_connectivity_test")
    @patch("f5functions.resolve_bigip_credentials", return_value="secret")
    @patch.dict(os.environ, {"BIGIP_USERNAME": "ops_user"})
    def test_cmd_bigip_test_env_username(self, mock_creds, mock_test):
        """Verify bigip test uses BIGIP_USERNAME environment variable when username is None."""
        mock_test.return_value = MagicMock(status_code=200)

        args = MagicMock()
        args.action = "test"
        args.host = "192.0.2.1"
        args.username = None
        args.password = None
        args.no_ssl_verify = True

        with patch("sys.stdout"):
            qkviewmgr.cmd_bigip(args)

        mock_test.assert_called_once_with("192.0.2.1", "ops_user", "secret", verify=False)

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
    @patch("f5functions.bigip_wait_for_qkview")
    @patch("f5functions.bigip_generate_qkview")
    @patch("f5functions.bigip_connectivity_test")
    @patch("f5functions.myf5_authenticate", return_value="tok123")
    @patch("f5functions.resolve_ihealth_credentials", return_value=("cid", "csec"))
    @patch("f5functions.resolve_bigip_credentials", return_value="pw123")
    @patch("os.path.getsize", return_value=1048576)
    def test_cmd_auto_pilot_flow(
        self, mock_size, mock_bigip_pw, mock_ih_creds, mock_auth,
        mock_test, mock_gen, mock_wait, mock_down, mock_del, mock_upload
    ):
        """Verify full 5-step Auto-Pilot pipeline execution including async task waiting."""
        mock_gen_resp = MagicMock()
        mock_gen_resp.status_code = 202
        mock_gen_resp.json.return_value = {"id": "task-uuid-456"}
        mock_gen.return_value = mock_gen_resp

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
        mock_wait.assert_called_once_with("bigip.local", "admin", "pw123", "task-uuid-456", verify=False)
        mock_down.assert_called_once_with("bigip.local", "admin", "pw123", "test.qkview", os.path.join(".", "test.qkview"), verify=False)
        mock_del.assert_called_once_with("bigip.local", "admin", "pw123", "test.qkview", verify=False)
        mock_upload.assert_called_once()

    @patch("f5functions.resolve_ihealth_credentials", return_value=("cid", "csec"))
    @patch("f5functions.myf5_authenticate", return_value="dummy_token")
    @patch("f5functions.ihealth_connectivity_test", return_value=True)
    def test_cmd_ihealth_test(self, mock_test, mock_auth, mock_creds):
        """Verify cmd_ihealth test invokes ihealth_connectivity_test."""
        args = MagicMock()
        args.action = "test"
        args.app_id = None
        args.client_id = None
        args.client_secret = None
        args.profile = None

        with patch("sys.stdout"):
            qkviewmgr.cmd_ihealth(args)

        mock_test.assert_called_once_with("dummy_token")

    @patch("f5functions.resolve_ihealth_credentials", return_value=("cid", "csec"))
    @patch("f5functions.myf5_authenticate", return_value="dummy_token")
    @patch("f5functions.myf5_list_support_cases")
    def test_cmd_case_list(self, mock_list, mock_auth, mock_creds):
        """Verify cmd_case list parses and displays cases."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": [{"caseNumber": "C123", "subject": "Test", "status": "Open"}]}
        mock_list.return_value = mock_resp

        args = MagicMock()
        args.action = "list"
        args.app_id = None
        args.client_id = None
        args.client_secret = None
        args.profile = None

        with patch("sys.stdout"):
            qkviewmgr.cmd_case(args)

        mock_list.assert_called_once_with("dummy_token")

    @patch("f5functions.resolve_ihealth_credentials", return_value=("cid", "csec"))
    @patch("f5functions.myf5_authenticate", return_value="dummy_token")
    @patch("f5functions.myf5_add_comments_to_existing_support_case")
    def test_cmd_case_comment(self, mock_comment, mock_auth, mock_creds):
        """Verify cmd_case comment invokes comments function with proper args."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_comment.return_value = mock_resp

        args = MagicMock()
        args.action = "comment"
        args.case_number = "C123"
        args.comment = "New notes"
        args.app_id = None
        args.client_id = None
        args.client_secret = None
        args.profile = None

        with patch("sys.stdout"):
            qkviewmgr.cmd_case(args)

        mock_comment.assert_called_once_with("dummy_token", "C123", "New notes")

    @patch("f5functions.bigip_get_system_info")
    @patch("f5functions.resolve_bigip_credentials", return_value="pw")
    def test_cmd_bigip_status(self, mock_creds, mock_info):
        """Verify bigip status action retrieves and displays system info."""
        mock_info.return_value = {
            "hostname": "bigip-a.lab",
            "product": "BIG-IP",
            "version": "17.1.3.5",
            "build": "0.0.14",
            "edition": "Point Release 5",
            "failover_state": "active",
        }
        args = MagicMock()
        args.action = "status"
        args.host = "52.73.20.25"
        args.username = "admin"
        args.password = None
        args.no_ssl_verify = True

        with patch("sys.stdout"):
            qkviewmgr.cmd_bigip(args)

        mock_info.assert_called_once_with("52.73.20.25", "admin", "pw", verify=False)

    @patch("f5functions.bigip_wait_for_qkview")
    @patch("f5functions.bigip_generate_qkview")
    @patch("f5functions.resolve_bigip_credentials", return_value="pw")
    def test_cmd_bigip_generate_wait(self, mock_creds, mock_gen, mock_wait):
        """Verify bigip generate with --wait flag invokes wait_for_qkview."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": "task-uuid-123"}
        mock_gen.return_value = mock_resp

        args = MagicMock()
        args.action = "generate"
        args.host = "52.73.20.25"
        args.username = "admin"
        args.password = None
        args.no_ssl_verify = True
        args.filename = "my.qkview"
        args.no_truncate = False
        args.wait = True
        args.wait_timeout = 60

        with patch("sys.stdout"):
            qkviewmgr.cmd_bigip(args)

        mock_gen.assert_called_once_with("52.73.20.25", "admin", "pw", "my.qkview", no_truncate=False, verify=False)
        mock_wait.assert_called_once()

    @patch("f5functions.bigip_download_qkview")
    @patch("f5functions.resolve_bigip_credentials", return_value="pw")
    def test_cmd_bigip_download(self, mock_creds, mock_down):
        """Verify bigip download action invokes bigip_download_qkview."""
        args = MagicMock()
        args.action = "download"
        args.host = "52.73.20.25"
        args.username = "admin"
        args.password = None
        args.no_ssl_verify = True
        args.filename = "my.qkview"
        args.output = "local.qkview"

        with patch("sys.stdout"):
            qkviewmgr.cmd_bigip(args)

        mock_down.assert_called_once_with("52.73.20.25", "admin", "pw", "my.qkview", "local.qkview", verify=False)

    @patch("f5functions.bigip_delete_qkview")
    @patch("f5functions.resolve_bigip_credentials", return_value="pw")
    def test_cmd_bigip_delete(self, mock_creds, mock_del):
        """Verify bigip delete action invokes bigip_delete_qkview."""
        args = MagicMock()
        args.action = "delete"
        args.host = "52.73.20.25"
        args.username = "admin"
        args.password = None
        args.no_ssl_verify = True
        args.filename = "my.qkview"

        with patch("sys.stdout"):
            qkviewmgr.cmd_bigip(args)

        mock_del.assert_called_once_with("52.73.20.25", "admin", "pw", "my.qkview", verify=False)

    @patch("f5functions.resolve_ihealth_credentials", return_value=("cid", "csec"))
    @patch("f5functions.myf5_authenticate", return_value="dummy_token")
    @patch("f5functions.ihealth_show_qkview_metadata")
    def test_cmd_ihealth_show(self, mock_show, mock_auth, mock_creds):
        """Verify ihealth show action displays qkview metadata."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "qv123", "status": "completed"}
        mock_show.return_value = mock_resp

        args = MagicMock()
        args.action = "show"
        args.qkview_id = "qv123"
        args.app_id = None
        args.client_id = None
        args.client_secret = None
        args.profile = None

        with patch("sys.stdout"):
            qkviewmgr.cmd_ihealth(args)

        mock_show.assert_called_once_with("dummy_token", "qv123")

    @patch("f5functions.resolve_ihealth_credentials", return_value=("cid", "csec"))
    @patch("f5functions.myf5_authenticate", return_value="dummy_token")
    @patch("f5functions.myf5_retrieve_case_creation_metadata")
    def test_cmd_case_metadata(self, mock_meta, mock_auth, mock_creds):
        """Verify case metadata retrieval."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"severities": ["Standard", "Urgent"]}
        mock_meta.return_value = mock_resp

        args = MagicMock()
        args.action = "metadata"
        args.app_id = None
        args.client_id = None
        args.client_secret = None
        args.profile = None

        with patch("sys.stdout"):
            qkviewmgr.cmd_case(args)

        mock_meta.assert_called_once_with("dummy_token")

    @patch("f5functions.resolve_ihealth_credentials", return_value=("cid", "csec"))
    @patch("f5functions.myf5_authenticate", return_value="dummy_token")
    @patch("f5functions.myf5_create_new_support_case")
    @patch("builtins.open", unittest.mock.mock_open(read_data='{"subject": "Network outage"}'))
    def test_cmd_case_create(self, mock_create, mock_auth, mock_creds):
        """Verify case creation from json file."""
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"data": {"caseNumber": "C999"}, "links": [{"href": "https://case/999"}]}
        mock_create.return_value = mock_resp

        args = MagicMock()
        args.action = "create"
        args.json_file = "case_spec.json"
        args.app_id = None
        args.client_id = None
        args.client_secret = None
        args.profile = None

        with patch("sys.stdout"):
            qkviewmgr.cmd_case(args)

        mock_create.assert_called_once_with("dummy_token", {"subject": "Network outage"})


if __name__ == "__main__":
    unittest.main()
