"""Comprehensive unit tests for QKViewMgr terminal interactive wizard."""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

_src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

import qkviewmgr.wizard as wizard


class TestWizard(unittest.TestCase):
    """Test suite for interactive terminal wizard functions."""

    @patch("builtins.input", return_value="custom_input")
    def test_prompt_normal(self, mock_input):
        """Test _prompt with user input."""
        res = wizard._prompt("Enter host", default="default.local")
        self.assertEqual(res, "custom_input")

    @patch("builtins.input", return_value="")
    def test_prompt_default_fallback(self, mock_input):
        """Test _prompt returns default when user presses Enter."""
        res = wizard._prompt("Enter host", default="default.local")
        self.assertEqual(res, "default.local")

    @patch("getpass.getpass", return_value="secret_pass")
    def test_prompt_secret(self, mock_getpass):
        """Test _prompt secret masking."""
        res = wizard._prompt("Enter password", secret=True)
        self.assertEqual(res, "secret_pass")

    @patch("qkviewmgr.wizard.run_doctor_wizard")
    @patch("builtins.input", side_effect=["5", "6"])
    def test_main_menu_doctor_and_exit(self, mock_input, mock_doctor):
        """Test main menu navigation to doctor diagnostics and then exiting."""
        with patch("sys.stdout"):
            wizard.main_menu()
        mock_doctor.assert_called_once()

    @patch("qkviewmgr.f5functions.bigip_connectivity_test")
    @patch("builtins.input", side_effect=["2", "192.0.2.1", "admin", "y", "6"])
    @patch("getpass.getpass", return_value="secret")
    def test_main_menu_bigip_test(self, mock_getpass, mock_input, mock_test):
        """Test main menu navigation to BIG-IP connectivity test."""
        with patch("sys.stdout"):
            wizard.main_menu()
        mock_test.assert_called_once_with("192.0.2.1", "admin", "secret", verify=False)

    @patch("qkviewmgr.f5functions.get_secure_session")
    def test_run_doctor_wizard(self, mock_session):
        """Test run_doctor_wizard execution."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp
        mock_session.return_value = mock_client

        with patch("sys.stdout"):
            wizard.run_doctor_wizard()

        self.assertGreaterEqual(mock_client.get.call_count, 3)

    @patch("qkviewmgr.wizard._prompt", side_effect=[""])
    def test_run_auto_wizard_missing_host(self, mock_prompt):
        """Test run_auto_wizard aborts when host is not provided."""
        with patch("sys.stdout"):
            wizard.run_auto_wizard()
        # Should return early without error


if __name__ == "__main__":
    unittest.main()
