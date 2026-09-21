"""Comprehensive test suite for qkviewmgr CLI parser and entrypoints."""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

_src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

import qkviewmgr.qkviewmgr as qkviewmgr


class TestCLIParser(unittest.TestCase):
    """Test CLI argument parsing for all subcommands and flags."""

    @patch.object(qkviewmgr, "cmd_doctor")
    def test_cli_doctor(self, mock_cmd):
        """Test 'qkviewmgr doctor' dispatch."""
        with patch.object(sys, "argv", ["qkviewmgr", "doctor"]):
            qkviewmgr.main()
        mock_cmd.assert_called_once()

    @patch.object(qkviewmgr, "cmd_bigip")
    def test_cli_bigip_test(self, mock_cmd):
        """Test 'qkviewmgr bigip --host 10.0.0.1 test' dispatch."""
        with patch.object(sys, "argv", ["qkviewmgr", "bigip", "--host", "10.0.0.1", "test"]):
            qkviewmgr.main()
        mock_cmd.assert_called_once()
        args = mock_cmd.call_args[0][0]
        self.assertEqual(args.host, "10.0.0.1")
        self.assertEqual(args.action, "test")

    @patch.object(qkviewmgr, "cmd_bigip")
    def test_cli_bigip_status(self, mock_cmd):
        """Test 'qkviewmgr bigip --host 10.0.0.1 status' dispatch."""
        with patch.object(sys, "argv", ["qkviewmgr", "bigip", "--host", "10.0.0.1", "status", "--no-ssl-verify"]):
            qkviewmgr.main()
        mock_cmd.assert_called_once()
        args = mock_cmd.call_args[0][0]
        self.assertEqual(args.host, "10.0.0.1")
        self.assertEqual(args.action, "status")
        self.assertTrue(args.no_ssl_verify)

    @patch.object(qkviewmgr, "cmd_bigip")
    def test_cli_bigip_generate_wait(self, mock_cmd):
        """Test 'qkviewmgr bigip --host 10.0.0.1 generate --wait' dispatch."""
        with patch.object(
            sys, "argv",
            ["qkviewmgr", "bigip", "--host", "10.0.0.1", "generate", "--filename", "my.qkview", "--wait", "--wait-timeout", "120"]
        ):
            qkviewmgr.main()
        mock_cmd.assert_called_once()
        args = mock_cmd.call_args[0][0]
        self.assertEqual(args.action, "generate")
        self.assertEqual(args.filename, "my.qkview")
        self.assertTrue(args.wait)
        self.assertEqual(args.wait_timeout, 120)

    @patch.object(qkviewmgr, "cmd_ihealth")
    def test_cli_ihealth_list(self, mock_cmd):
        """Test 'qkviewmgr ihealth list' dispatch."""
        with patch.object(sys, "argv", ["qkviewmgr", "ihealth", "list"]):
            qkviewmgr.main()
        mock_cmd.assert_called_once()
        args = mock_cmd.call_args[0][0]
        self.assertEqual(args.action, "list")

    @patch.object(qkviewmgr, "cmd_case")
    def test_cli_case_list(self, mock_cmd):
        """Test 'qkviewmgr case list' dispatch."""
        with patch.object(sys, "argv", ["qkviewmgr", "case", "list"]):
            qkviewmgr.main()
        mock_cmd.assert_called_once()
        args = mock_cmd.call_args[0][0]
        self.assertEqual(args.action, "list")

    @patch.object(qkviewmgr, "cmd_auto_pilot")
    def test_cli_run_auto(self, mock_cmd):
        """Test 'qkviewmgr run --host 10.0.0.1' dispatch."""
        with patch.object(sys, "argv", ["qkviewmgr", "run", "--host", "10.0.0.1", "--no-upload"]):
            qkviewmgr.main()
        mock_cmd.assert_called_once()
        args = mock_cmd.call_args[0][0]
        self.assertEqual(args.host, "10.0.0.1")
        self.assertTrue(args.no_upload)


if __name__ == "__main__":
    unittest.main()
