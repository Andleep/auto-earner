import os
import socket
import unittest
from unittest.mock import patch

os.environ.setdefault("PAY_TO", "0x0000000000000000000000000000000000000001")

import company_api


class SecurityRegressionTests(unittest.TestCase):
    def test_blocks_private_ipv4(self):
        for url in (
            "http://127.0.0.1",
            "http://10.0.0.1",
            "http://192.168.1.1",
        ):
            with self.subTest(url=url):
                with self.assertRaisesRegex(ValueError, "private_host_blocked"):
                    company_api._resolve_public_endpoint(url)

    def test_blocks_private_ipv6(self):
        with patch.object(
            socket,
            "getaddrinfo",
            return_value=[(socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("::1", 80, 0, 0))],
        ):
            with self.assertRaisesRegex(ValueError, "private_host_blocked"):
                company_api._resolve_public_endpoint("http://[::1]")

    def test_blocks_local_hostnames_and_userinfo(self):
        for url, error in (
            ("http://localhost", "private_host_blocked"),
            ("http://service.local", "private_host_blocked"),
            ("http://service.internal", "private_host_blocked"),
            ("https://user:pass@example.com", "userinfo_not_allowed"),
        ):
            with self.subTest(url=url):
                with self.assertRaisesRegex(ValueError, error):
                    company_api._resolve_public_endpoint(url)

    def test_rejects_invalid_port(self):
        with self.assertRaisesRegex(ValueError, "invalid_port"):
            company_api._resolve_public_endpoint("https://example.com:99999")

    def test_returns_all_validated_public_ips(self):
        infos = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("151.101.1.69", 443)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
        ]
        with patch.object(socket, "getaddrinfo", return_value=infos):
            _, host, port, ips = company_api._resolve_public_endpoint("https://example.com")
        self.assertEqual(host, "example.com")
        self.assertEqual(port, 443)
        self.assertEqual(ips, ["93.184.216.34", "151.101.1.69"])

    def test_dns_failure_is_explicit(self):
        with patch.object(socket, "getaddrinfo", side_effect=socket.gaierror("no dns")):
            with self.assertRaisesRegex(ValueError, "dns_failed"):
                company_api._resolve_public_endpoint("https://does-not-exist.invalid")

    def test_batch_rejects_more_than_five_without_truncation(self):
        client = company_api.app.test_client()
        response = client.post(
            "/v1/company/batch",
            json={"urls": [f"https://example{i}.com" for i in range(6)]},
        )
        # x402 protects the public route; call the underlying Flask view as a
        # request-context regression check as well.
        if response.status_code == 402:
            with company_api.app.test_request_context(
                "/v1/company/batch",
                method="POST",
                json={"urls": [f"https://example{i}.com" for i in range(6)]},
            ):
                direct = company_api.company_batch()
                payload = direct[0].get_json() if isinstance(direct, tuple) else direct.get_json()
                self.assertEqual(direct[1], 400)
                self.assertEqual(payload["error"], "too_many_urls")
                self.assertEqual(payload["requested"], 6)
        else:
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.get_json()["error"], "too_many_urls")


if __name__ == "__main__":
    unittest.main()
