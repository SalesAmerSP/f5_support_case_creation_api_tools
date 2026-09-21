"""Live integration tests for BIG-IP appliances.

These tests run against real TMOS appliances (e.g. 52.73.20.25, 44.214.252.110).
If the target device is not reachable, tests are gracefully skipped.
"""

import os
import sys
import unittest

_src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

import qkviewmgr.f5functions as f5functions


def _is_host_reachable(host, timeout=3):
    """Check if BIG-IP host responds on port 443 within timeout."""
    try:
        session = f5functions.get_secure_session(verify=False)
        r = session.get(f"https://{host}/mgmt/tm/sys/ready", timeout=timeout)
        return r.status_code in (200, 401)
    except Exception:
        return False


class TestLiveBIGIPIntegration(unittest.TestCase):
    """Integration test suite executing real API requests against lab appliances."""

    @classmethod
    def setUpClass(cls):
        cls.host_a = os.getenv("BIGIP_HOST_A", "52.73.20.25")
        cls.host_b = os.getenv("BIGIP_HOST_B", "44.214.252.110")
        cls.username = os.getenv("BIGIP_USERNAME", "admin")
        cls.password = os.getenv("BIGIP_PASSWORD", "")
        cls.host_a_reachable = bool(cls.password and _is_host_reachable(cls.host_a))
        cls.host_b_reachable = bool(cls.password and _is_host_reachable(cls.host_b))

    def test_live_bigip_a_connectivity(self):
        """Verify real HTTP 200 connectivity to BIG-IP A."""
        if not self.host_a_reachable:
            self.skipTest(f"BIG-IP A ({self.host_a}) is not reachable from this environment.")
        resp = f5functions.bigip_connectivity_test(
            self.host_a, self.username, self.password, verify=False
        )
        self.assertEqual(resp.status_code, 200)

    def test_live_bigip_a_system_info(self):
        """Verify system info querying returns valid TMOS version metadata."""
        if not self.host_a_reachable:
            self.skipTest(f"BIG-IP A ({self.host_a}) is not reachable.")
        info = f5functions.bigip_get_system_info(
            self.host_a, self.username, self.password, verify=False
        )
        self.assertEqual(info["product"], "BIG-IP")
        self.assertTrue(info["version"].startswith("17.") or len(info["version"]) > 0)
        self.assertIn("active", info["failover_state"].lower())

    def test_live_bigip_b_connectivity(self):
        """Verify real HTTP 200 connectivity to BIG-IP B."""
        if not self.host_b_reachable:
            self.skipTest(f"BIG-IP B ({self.host_b}) is not reachable.")
        resp = f5functions.bigip_connectivity_test(
            self.host_b, self.username, self.password, verify=False
        )
        self.assertEqual(resp.status_code, 200)

    def test_live_bigip_b_system_info(self):
        """Verify system info querying returns valid TMOS version metadata for BIG-IP B."""
        if not self.host_b_reachable:
            self.skipTest(f"BIG-IP B ({self.host_b}) is not reachable.")
        info = f5functions.bigip_get_system_info(
            self.host_b, self.username, self.password, verify=False
        )
        self.assertEqual(info["product"], "BIG-IP")
        self.assertTrue(len(info["version"]) > 0)

    def test_live_bigip_a_list_qkviews(self):
        """Verify querying autodeploy QKViews on BIG-IP A."""
        if not self.host_a_reachable:
            self.skipTest(f"BIG-IP A ({self.host_a}) is not reachable.")
        resp = f5functions.bigip_list_qkviews(
            self.host_a, self.username, self.password, verify=False
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("items", data)


if __name__ == "__main__":
    unittest.main()
