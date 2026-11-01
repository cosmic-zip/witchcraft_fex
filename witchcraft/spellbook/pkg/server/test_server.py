#!/usr/bin/env python3
"""
Unit tests for WitchcraftFEX Python HTTP Server (spellbook/pkg/server/server.py).
Tests pure standard library implementation: AuthManager, Handlers, Endpoints, and Security.
"""

import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

SERVER_DIR = os.path.dirname(__file__)
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

import unittest
import threading
import time
import json
import tempfile
import urllib.request
import urllib.parse
import urllib.error

from server import (
    AuthManager,
    build_command_from_form,
    build_command_from_json,
    filter_alpha,
    create_server,
    NettravelerRequestHandler
)


class TestAuthManager(unittest.TestCase):
    """Test suite for AuthManager (password hashing, HMAC tokens, revocation)."""

    def setUp(self):
        self.auth = AuthManager(username="cosmic", password="SuperSecretPassword123!")

    def test_verify_valid_credentials(self):
        self.assertTrue(self.auth.verify_credentials("cosmic", "SuperSecretPassword123!"))

    def test_verify_invalid_username(self):
        self.assertFalse(self.auth.verify_credentials("wrong_user", "SuperSecretPassword123!"))

    def test_verify_invalid_password(self):
        self.assertFalse(self.auth.verify_credentials("cosmic", "WrongPassword"))

    def test_token_lifecycle(self):
        token = self.auth.create_token("cosmic", duration_sec=60)
        self.assertTrue(token)
        is_valid, user = self.auth.validate_token(token)
        self.assertTrue(is_valid)
        self.assertEqual(user, "cosmic")

    def test_token_expiration(self):
        token = self.auth.create_token("cosmic", duration_sec=-1)  # expired
        is_valid, user = self.auth.validate_token(token)
        self.assertFalse(is_valid)
        self.assertIsNone(user)

    def test_token_tampering(self):
        token = self.auth.create_token("cosmic", duration_sec=60)
        tampered_token = token[:-4] + "abcd"
        is_valid, user = self.auth.validate_token(tampered_token)
        self.assertFalse(is_valid)

    def test_token_revocation(self):
        token = self.auth.create_token("cosmic", duration_sec=60)
        self.auth.revoke_token(token)
        is_valid, user = self.auth.validate_token(token)
        self.assertFalse(is_valid)


class TestCommandBuilders(unittest.TestCase):
    """Test command parsing from Form and JSON payloads."""

    def test_filter_alpha(self):
        self.assertEqual(filter_alpha("Net.Ping-123_"), "net.ping-123_")
        self.assertEqual(filter_alpha(";rm -rf /;"), "rm-rf")

    def test_build_command_from_form_ezec(self):
        form_data = {
            "EZECnative.net_ping": ["1"],
            "host": ["127.0.0.1"],
            "ztoken": ["secret_token"],
            "requestid": ["10293"]
        }
        cmd = build_command_from_form(form_data)
        self.assertEqual(cmd, ["net.ping", "--host", "127.0.0.1"])

    def test_build_command_from_form_empty_error(self):
        with self.assertRaises(ValueError):
            build_command_from_form({})

    def test_build_command_from_json(self):
        json_data = {
            "command": "mac.spoof",
            "arguments": {
                "interface": "wlan0"
            }
        }
        cmd = build_command_from_json(json_data)
        self.assertEqual(cmd, ["mac.spoof", "--interface", "wlan0"])

    def test_build_command_from_json_missing_command(self):
        with self.assertRaises(ValueError):
            build_command_from_json({"arguments": {}})


class TestServerIntegration(unittest.TestCase):
    """Integration test suite for the HTTP server instance."""

    @classmethod
    def setUpClass(cls):
        # Create a temporary directory for static files
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.index_file = os.path.join(cls.temp_dir.name, "index.html")
        with open(cls.index_file, "w") as f:
            f.write("<html><body><h1>WitchcraftFEX WebUI</h1></body></html>")

        cls.css_file = os.path.join(cls.temp_dir.name, "style.css")
        with open(cls.css_file, "w") as f:
            f.write("body { background: #000; }")

        # Start test server on random local port
        cls.ztoken = "test_ztoken_12345"
        cls.username = "test_admin"
        cls.password = "test_password_pass"

        cls.httpd, cls.handler_class = create_server(
            host="127.0.0.1",
            port=0,
            folder=cls.temp_dir.name,
            ztoken=cls.ztoken,
            username=cls.username,
            password=cls.password,
            project_root=PROJECT_ROOT
        )

        cls.port = cls.httpd.server_port
        cls.base_url = f"http://127.0.0.1:{cls.port}"

        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.temp_dir.cleanup()

    def test_health_check(self):
        req = urllib.request.Request(f"{self.base_url}/api/health")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode())
            self.assertEqual(data.get("status"), "healthy")

    def test_system_stats_endpoint(self):
        req = urllib.request.Request(f"{self.base_url}/api/system/stats")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode())
            self.assertIn("cpu", data)
            self.assertIn("memory", data)
            self.assertIn("os", data)

    def test_static_file_serving_index(self):
        req = urllib.request.Request(f"{self.base_url}/")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("text/html", resp.headers.get("Content-Type", ""))
            content = resp.read().decode()
            self.assertIn("WitchcraftFEX WebUI", content)

    def test_static_file_serving_css(self):
        req = urllib.request.Request(f"{self.base_url}/style.css")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("text/css", resp.headers.get("Content-Type", ""))
            content = resp.read().decode()
            self.assertIn("background", content)

    def test_static_file_not_found(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(f"{self.base_url}/nonexistent.html")
        self.assertEqual(ctx.exception.code, 404)

    def test_path_traversal_blocked(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(f"{self.base_url}/../../../../etc/passwd")
        # Either 403 Forbidden or 404 Not Found (blocked safely)
        self.assertIn(ctx.exception.code, (403, 404))

    def test_auth_status_unauthenticated(self):
        req = urllib.request.Request(f"{self.base_url}/api/auth/status")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode())
            self.assertFalse(data.get("authenticated"))

    def test_login_invalid_credentials(self):
        payload = json.dumps({"username": self.username, "password": "wrong"}).encode()
        req = urllib.request.Request(
            f"{self.base_url}/api/login",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code, 401)

    def test_login_success_json_and_authenticated_requests(self):
        # 1. Login with JSON
        payload = json.dumps({"username": self.username, "password": self.password}).encode()
        req = urllib.request.Request(
            f"{self.base_url}/api/login",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode())
            self.assertEqual(data.get("status"), "success")
            token = data.get("token")
            self.assertTrue(token)
            cookie = resp.headers.get("Set-Cookie")
            self.assertIn("nt_session=", cookie)

        # 2. Check auth status using Bearer token
        status_req = urllib.request.Request(
            f"{self.base_url}/api/auth/status",
            headers={"Authorization": f"Bearer {token}"}
        )
        with urllib.request.urlopen(status_req) as resp:
            self.assertEqual(resp.status, 200)
            status_data = json.loads(resp.read().decode())
            self.assertTrue(status_data.get("authenticated"))
            self.assertEqual(status_data.get("user"), self.username)

        # 3. Check auth status using Cookie
        status_req_cookie = urllib.request.Request(
            f"{self.base_url}/api/auth/status",
            headers={"Cookie": f"nt_session={token}"}
        )
        with urllib.request.urlopen(status_req_cookie) as resp:
            self.assertEqual(resp.status, 200)
            status_data = json.loads(resp.read().decode())
            self.assertTrue(status_data.get("authenticated"))

        # 4. Logout
        logout_req = urllib.request.Request(
            f"{self.base_url}/api/logout",
            data=b"",
            headers={"Cookie": f"nt_session={token}"}
        )
        with urllib.request.urlopen(logout_req) as resp:
            self.assertEqual(resp.status, 200)

        # 5. Check auth status after logout (should be unauthenticated)
        with urllib.request.urlopen(status_req_cookie) as resp:
            status_data = json.loads(resp.read().decode())
            self.assertFalse(status_data.get("authenticated"))

    def test_exec_endpoint_unauthorized(self):
        payload = json.dumps({"command": "version"}).encode()
        req = urllib.request.Request(
            f"{self.base_url}/api/exec",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code, 401)

    def test_exec_endpoint_with_ztoken(self):
        # Legacy form submission with ztoken
        form_data = urllib.parse.urlencode({
            "EZECversion": "1",
            "ztoken": self.ztoken
        }).encode()

        req = urllib.request.Request(
            f"{self.base_url}/api/exec",
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            content = resp.read().decode()
            self.assertIn("WitchcraftFEX", content)

    def test_exec_endpoint_webui_random_seed_and_multiple_ztokens(self):
        # Exact WebUI payload structure
        raw_body = f"ztoken={self.ztoken}&ztoken=&ztoken=&command=echo%20%22hello%22&requestid845524=845524&EZECbash845524=bash".encode()

        req = urllib.request.Request(
            f"{self.base_url}/",
            data=raw_body,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            content = resp.read().decode()
            self.assertIn("hello", content)


if __name__ == "__main__":
    unittest.main()

