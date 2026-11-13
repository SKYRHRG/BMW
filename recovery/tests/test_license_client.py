"""Offline tests for reconstructed BMW license client: no real network calls."""
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "step2_src"))
from license_client import check_license, resolve_license_url


FAUTH_URL = "https://lic.example.test/api/app/fauth/license/check"
ALT_URL = "https://lic.example.test/v1/validate"


def responder(status, data):
    response = Mock()
    response.status_code = status
    response.json.return_value = data
    sess = Mock()
    sess.post.return_value = response
    return sess


class LicenseClientRecoveryTests(unittest.TestCase):
    def test_fauth_valid_and_request_shape(self):
        sess = responder(200, {"success": True, "leftDays": "28", "message": "OK"})
        result = check_license(FAUTH_URL, " LK ", " DEVICE ", session=sess)
        self.assertEqual(result[:4], (True, 28, "UPSTREAM-VALID", "OK"))
        sess.post.assert_called_once_with(
            FAUTH_URL,
            json={"Key": "LK", "Machine": "DEVICE"},
            headers={"Content-Type": "application/json"},
            timeout=15,
        )

    def test_other_url_uses_alternate_request_keys(self):
        sess = responder(200, {"success": True, "leftDays": 14, "mode": "ONLINE"})
        result = check_license(ALT_URL, "L1", "M1", session=sess)
        self.assertEqual(result[:3], (True, 14, "ONLINE"))
        self.assertEqual(sess.post.call_args.kwargs["json"],
                         {"licenseKey": "L1", "deviceId": "M1"})

    def test_false_or_truthy_string_is_not_valid(self):
        for success in [False, "true", "yes", 1, None]:
            with self.subTest(success=success):
                self.assertFalse(check_license(FAUTH_URL, "L", "M",
                                 session=responder(200, {"success": success}))[0])

    def test_unauthorized(self):
        result = check_license(FAUTH_URL, "L", "M", session=responder(401, {"error": "expired"}))
        self.assertEqual(result[:4], (False, None, "", "expired"))

    def test_rate_limit(self):
        result = check_license(FAUTH_URL, "L", "M", session=responder(429, {}))
        self.assertEqual(result[3], "Too many attempts. Please try later.")

    def test_server_error(self):
        result = check_license(FAUTH_URL, "L", "M", session=responder(503, {}))
        self.assertIn("503", result[3])

    def test_bad_json(self):
        sess = responder(200, {})
        sess.post.return_value.json.side_effect = ValueError("invalid")
        self.assertFalse(check_license(FAUTH_URL, "L", "M", session=sess)[0])

    def test_missing_input(self):
        self.assertFalse(check_license(FAUTH_URL, "", "M", session=responder(200, {}))[0])

    def test_non_https_refused(self):
        sess = responder(200, {"success": True})
        result = check_license("http://example.test/validate", "L", "M", session=sess)
        self.assertFalse(result[0])
        sess.post.assert_not_called()

    def test_timeout(self):
        sess = Mock()
        import requests
        sess.post.side_effect = requests.exceptions.Timeout()
        result = check_license(FAUTH_URL, "L", "M", session=sess)
        self.assertFalse(result[0])
        self.assertIn("timeout", result[3])

    def test_configurable_endpoint(self):
        with patch.dict("os.environ", {"LICENSE_API_URL": ALT_URL}):
            self.assertEqual(resolve_license_url(), ALT_URL)


if __name__ == "__main__":
    unittest.main()
