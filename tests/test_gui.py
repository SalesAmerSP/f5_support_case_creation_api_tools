"""Tests for the native desktop GUI module (qkviewmgr.gui)."""

import os
import signal
import sys
import unittest
from unittest.mock import MagicMock, patch

_src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

import qkviewmgr.f5functions as _f5f
import qkviewmgr.gui as gui

sys.modules['f5functions'] = _f5f
sys.modules['gui'] = gui


class DummyWidget:
    """Mock widget for Tkinter Entry and BooleanVar."""
    def __init__(self, val=""):
        self._val = val

    def get(self):
        return self._val

    def insert(self, idx, text):
        self._val = text


class DummyApp(gui.QKViewMgrApp):
    """Mock application harness simulating QKViewMgrApp without a real display."""
    def __init__(self):
        self.logs = []
        self.bigip_host = DummyWidget("192.0.2.1")
        self.bigip_user = DummyWidget("admin")
        self.bigip_pw = DummyWidget("secret123")
        self.bigip_ssl_var = DummyWidget(False)
        self.auto_host = DummyWidget("192.0.2.1")
        self.auto_user = DummyWidget("admin")
        self.auto_pw = DummyWidget("secret123")
        self.auto_ssl_var = DummyWidget(False)
        self.auto_case = DummyWidget("")
        self.destroyed = False

    def log(self, message):
        self.logs.append(message)

    def destroy(self):
        self.destroyed = True


class TestGuiFallbackAndSignals(unittest.TestCase):
    """Test GUI fallback when Tkinter is not installed and signal handling."""

    @patch('qkviewmgr.gui.TKINTER_AVAILABLE', False)
    @patch('qkviewmgr.wizard.main_menu')
    def test_launch_gui_missing_tkinter(self, mock_wizard):
        """Verify launch_gui falls back to terminal wizard when Tkinter is absent."""
        gui.launch_gui()
        mock_wizard.assert_called_once()

    @patch('qkviewmgr.gui.TKINTER_AVAILABLE', True)
    @patch('qkviewmgr.gui.QKViewMgrApp')
    @patch('signal.signal')
    def test_launch_gui_success(self, mock_signal, mock_app_cls):
        """Verify launch_gui initializes app and enters mainloop."""
        mock_app = MagicMock()
        mock_app_cls.return_value = mock_app
        gui.launch_gui()
        mock_app_cls.assert_called_once()
        mock_app.mainloop.assert_called_once()

    @patch('qkviewmgr.gui.TKINTER_AVAILABLE', True)
    @patch('qkviewmgr.gui.QKViewMgrApp')
    def test_launch_gui_keyboard_interrupt(self, mock_app_cls):
        """Verify launch_gui catches KeyboardInterrupt (Ctrl+C) and exits cleanly."""
        mock_app = MagicMock()
        mock_app.mainloop.side_effect = KeyboardInterrupt
        mock_app_cls.return_value = mock_app
        with self.assertRaises(SystemExit) as ctx:
            gui.launch_gui()
        self.assertEqual(ctx.exception.code, 0)
        mock_app.destroy.assert_called_once()


class TestGuiLogic(unittest.TestCase):
    """Test GUI methods, error trapping, and thread resilience."""

    def setUp(self):
        self.app = DummyApp()

    def test_test_bigip_validation_missing_host(self):
        """Verify _test_bigip rejects blank host without raising an unhandled exception."""
        self.app.bigip_host = DummyWidget("")
        self.app._test_bigip()
        self.assertTrue(any("ERROR: BIG-IP Host / IP is required" in msg for msg in self.app.logs))

    def test_test_bigip_validation_missing_password(self):
        """Verify _test_bigip rejects blank password without raising an unhandled exception."""
        self.app.bigip_pw = DummyWidget("")
        self.app._test_bigip()
        self.assertTrue(any("ERROR: Password is required" in msg for msg in self.app.logs))

    @patch('qkviewmgr.f5functions.bigip_connectivity_test')
    def test_test_bigip_success_200(self, mock_test):
        """Verify _test_bigip reports success when BIG-IP responds HTTP 200."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_test.return_value = mock_resp

        self.app._test_bigip()
        self.assertTrue(any("✓ Connection to 192.0.2.1 succeeded" in msg for msg in self.app.logs))

    @patch('qkviewmgr.f5functions.bigip_connectivity_test')
    def test_test_bigip_auth_failure_401(self, mock_test):
        """Verify _test_bigip reports 401 Unauthorized accurately."""
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_test.return_value = mock_resp

        self.app._test_bigip()
        self.assertTrue(any("HTTP 401 Unauthorized" in msg for msg in self.app.logs))

    @patch('qkviewmgr.f5functions.bigip_connectivity_test')
    def test_test_bigip_auth_failure_403(self, mock_test):
        """Verify _test_bigip reports 403 Forbidden accurately."""
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_test.return_value = mock_resp

        self.app._test_bigip()
        self.assertTrue(any("HTTP 403 Forbidden" in msg for msg in self.app.logs))

    @patch('qkviewmgr.f5functions.bigip_connectivity_test')
    def test_test_bigip_connection_systemexit(self, mock_test):
        """Verify _test_bigip catches SystemExit and writes error message to log."""
        mock_test.side_effect = SystemExit("Connection refused by appliance")

        self.app._test_bigip()
        self.assertTrue(any("✗ Connection to 192.0.2.1 failed: Connection refused by appliance" in msg for msg in self.app.logs))

    @patch('qkviewmgr.f5functions.bigip_connectivity_test')
    def test_test_bigip_generic_exception(self, mock_test):
        """Verify _test_bigip catches general Exception and writes error message to log."""
        mock_test.side_effect = ConnectionResetError("Socket reset by peer")

        self.app._test_bigip()
        self.assertTrue(any("Socket reset by peer" in msg for msg in self.app.logs))

    def test_run_threaded_catches_systemexit(self):
        """Verify _run_threaded catches SystemExit in worker threads and logs it."""
        def faulty_worker():
            raise SystemExit("Fatal thread exit")

        with patch('threading.Thread') as mock_thread_cls:
            self.app._run_threaded(faulty_worker)
            mock_thread_cls.assert_called_once()
            target = mock_thread_cls.call_args[1]['target']
            target()

        self.assertTrue(any("✗ Operation encountered an error: Fatal thread exit" in msg for msg in self.app.logs))

    def test_run_threaded_catches_runtime_error(self):
        """Verify _run_threaded catches RuntimeError in worker threads and logs it."""
        def faulty_worker():
            raise RuntimeError("Unexpected thread crash")

        with patch('threading.Thread') as mock_thread_cls:
            self.app._run_threaded(faulty_worker)
            mock_thread_cls.assert_called_once()
            target = mock_thread_cls.call_args[1]['target']
            target()

        self.assertTrue(any("✗ Operation encountered an error: Unexpected thread crash" in msg for msg in self.app.logs))

    @patch('qkviewmgr.f5functions.resolve_ihealth_credentials')
    def test_test_ihealth_missing_credentials(self, mock_creds):
        """Verify _test_ihealth logs missing credentials error without crashing."""
        mock_creds.return_value = (None, None)
        self.app._test_ihealth()
        self.assertTrue(any("ERROR: Missing F5 Client ID or Secret" in msg for msg in self.app.logs))

    @patch('qkviewmgr.f5functions.resolve_ihealth_credentials')
    @patch('qkviewmgr.f5functions.myf5_authenticate')
    @patch('qkviewmgr.f5functions.ihealth_connectivity_test')
    def test_test_ihealth_success_bool(self, mock_test, mock_auth, mock_creds):
        """Verify _test_ihealth reports success on boolean True return value."""
        mock_creds.return_value = ("client_id", "client_secret")
        mock_auth.return_value = "token_abc"
        mock_test.return_value = True

        self.app._test_ihealth()
        self.assertTrue(any("✓ iHealth API connection and token verified" in msg for msg in self.app.logs))

    @patch('qkviewmgr.f5functions.resolve_ihealth_credentials')
    @patch('qkviewmgr.f5functions.myf5_authenticate')
    @patch('qkviewmgr.f5functions.myf5_connectivity_test')
    def test_test_myf5_success_bool(self, mock_test, mock_auth, mock_creds):
        """Verify _test_myf5 reports success on boolean True return value."""
        mock_creds.return_value = ("client_id", "client_secret")
        mock_auth.return_value = "token_abc"
        mock_test.return_value = True

        self.app._test_myf5()
        self.assertTrue(any("✓ MyF5 Support API connection and token verified" in msg for msg in self.app.logs))


if __name__ == '__main__':
    unittest.main()
