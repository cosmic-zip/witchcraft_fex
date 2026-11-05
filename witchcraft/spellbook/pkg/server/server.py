#!/usr/bin/env python3
"""
WitchcraftFEX Standalone Python Server with Authentication & Static File Serving.
Pure Python standard library (no external pip dependencies).
"""

import sys
import os
import json
import time
import hmac
import hashlib
import secrets
import mimetypes
import logging
import subprocess
import urllib.parse
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from http.cookies import SimpleCookie
from socketserver import ThreadingMixIn
from typing import Tuple, Optional, Dict, Any


# ----------------------------------------------------------------------
# Configuration & Constants
# ----------------------------------------------------------------------

DEFAULT_HOST = os.getenv("NT_SERVER_HOST", "0.0.0.0")
DEFAULT_PORT = int(os.getenv("NT_SERVER_PORT", "5500"))
DEFAULT_FOLDER = os.getenv("NT_SERVER_FOLDER", "spellbook/webui")
DEFAULT_ZTOKEN = os.getenv(
    "NT_COSMIC_SIGKEY",
    "b7a5f1f46944d5cc438646c547e20b177257608b5dfff41d7c5f063a6ea092fe"
)
DEFAULT_USER = os.getenv("NT_SERVER_USER", "admin")
DEFAULT_PASS = os.getenv("NT_SERVER_PASS", "cosmic")
SESSION_TIMEOUT_SEC = int(os.getenv("NT_SESSION_TIMEOUT", "86400"))  # 24 hours
EXEC_TIMEOUT_SEC = int(os.getenv("NT_EXEC_TIMEOUT", "30"))


# ----------------------------------------------------------------------
# Session & Auth Manager (HMAC Signed Tokens + Memory Cache)
# ----------------------------------------------------------------------

class AuthManager:
    """Manages authentication, passwords, and HMAC signed session tokens."""

    def __init__(self, username: str = DEFAULT_USER, password: str = DEFAULT_PASS, secret_key: str = None):
        self.username = username
        self.password = password
        self.secret_key = secret_key.encode("utf-8") if secret_key else secrets.token_bytes(32)
        # Salt and hash password in memory
        self._salt = secrets.token_hex(16)
        self._password_hash = self._hash_password(password, self._salt)
        self._revoked_tokens = set()

    def _hash_password(self, password: str, salt: str) -> str:
        return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()

    def verify_credentials(self, username: str, password: str) -> bool:
        """Verify username and password in constant time."""
        if not hmac.compare_digest(username, self.username):
            return False
        expected = self._hash_password(password, self._salt)
        return hmac.compare_digest(expected, self._password_hash)

    def create_token(self, username: str, duration_sec: int = SESSION_TIMEOUT_SEC) -> str:
        """Create an HMAC-SHA256 signed session token."""
        expires_at = int(time.time()) + duration_sec
        nonce = secrets.token_hex(8)
        payload = f"{username}:{expires_at}:{nonce}"
        signature = hmac.new(self.secret_key, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        token = f"{payload}:{signature}"
        return token

    def validate_token(self, token: str) -> Tuple[bool, Optional[str]]:
        """Validate HMAC signed token. Returns (is_valid, username)."""
        if not token or token in self._revoked_tokens:
            return False, None
        try:
            parts = token.split(":")
            if len(parts) != 4:
                return False, None
            username, expires_str, nonce, signature = parts
            expires_at = int(expires_str)
            if time.time() > expires_at:
                return False, None
            payload = f"{username}:{expires_str}:{nonce}"
            expected_sig = hmac.new(self.secret_key, payload.encode("utf-8"), hashlib.sha256).hexdigest()
            if hmac.compare_digest(expected_sig, signature):
                return True, username
        except Exception:
            return False, None
        return False, None

    def revoke_token(self, token: str):
        """Revoke a session token on logout."""
        if token:
            self._revoked_tokens.add(token)


# ----------------------------------------------------------------------
# Command Builder (Parses WebUI Form & JSON payloads)
# ----------------------------------------------------------------------

def filter_alpha(s: str) -> str:
    """Filter string to only contain lowercase alphanumeric characters, dots, hyphens, and underscores."""
    return "".join(c for c in s.lower() if c.isalnum() or c in ".-_")


def build_command_from_form(form_data: Dict[str, list]) -> list:
    """Build CLI command arguments from WebUI form data."""
    args = []

    # First pass: extract command names (EZEC prefixed keys)
    for key, values in form_data.items():
        if "EZEC" in key:
            cmd_name = ""
            # Prefer value if provided (e.g. value="bash" or value="mac.spoof")
            if values and str(values[0]).strip() and str(values[0]).strip() not in ("1", "true", "on"):
                cmd_name = str(values[0]).strip()
            else:
                # Extract from key: remove EZEC, native., and trailing digits (requestid)
                k = key.replace("EZEC", "").replace("native.", "").replace("native_", "").replace("_", ".")
                cmd_name = re.sub(r"\d+$", "", k)

            cmd_name = cmd_name.replace("native.", "").replace("_", ".")
            cmd_name = filter_alpha(cmd_name)
            if cmd_name and cmd_name not in args:
                args.append(cmd_name)

    # Second pass: extract flags and values
    for key, values in form_data.items():
        lower_key = key.lower()
        if (
            lower_key == "ztoken"
            or lower_key.startswith("requestid")
            or "ezec" in lower_key
            or lower_key.startswith("csrf")
        ):
            continue
        flag = filter_alpha(key)
        if not flag or not values:
            continue
        val = str(values[0]).replace("%2F", "/")
        args.extend([f"--{flag}", val])

    if not args:
        raise ValueError("no command arguments constructed")

    return args


def build_command_from_json(data: Dict[str, Any]) -> list:
    """Build CLI command arguments from JSON payload."""
    args = []
    command = data.get("command") or data.get("name")
    if not command:
        raise ValueError("missing command name in JSON payload")

    args.append(filter_alpha(command))

    arguments = data.get("arguments") or data.get("args") or {}
    if isinstance(arguments, dict):
        for flag, val in arguments.items():
            clean_flag = filter_alpha(str(flag))
            if clean_flag:
                args.extend([f"--{clean_flag}", str(val)])
    elif isinstance(arguments, list):
        for item in arguments:
            args.append(str(item))

    return args


# ----------------------------------------------------------------------
# Request Handler
# ----------------------------------------------------------------------

class WitchcraftRequestHandler(BaseHTTPRequestHandler):
    """Robust HTTP Request Handler supporting Static Files, Auth, and Command Execution."""

    server_folder: str = DEFAULT_FOLDER
    ztoken: str = DEFAULT_ZTOKEN
    auth_manager: AuthManager = None
    logger: logging.Logger = None
    project_root: str = "."

    # ------------------------------------------------------------------
    # Helper Utilities
    # ------------------------------------------------------------------

    def send_json(self, status_code: int, data: Dict[str, Any], headers: Optional[Dict[str, str]] = None):
        """Send a JSON response."""
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        if headers:
            for k, v in headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(payload)

    def send_text(self, status_code: int, text: str, content_type: str = "text/plain; charset=utf-8"):
        """Send a plain text or HTML response."""
        payload = text.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def get_cookie(self, name: str) -> Optional[str]:
        """Extract a cookie by name from request headers."""
        cookie_header = self.headers.get("Cookie")
        if not cookie_header:
            return None
        cookie = SimpleCookie()
        try:
            cookie.load(cookie_header)
            if name in cookie:
                return cookie[name].value
        except Exception:
            return None
        return None

    def is_authenticated(self, body_token: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Check if the request is authenticated via:
        1. Valid session cookie (nt_session)
        2. Bearer token in Authorization header
        3. Custom header X-Auth-Token
        4. Legacy ztoken parameter (body_token)
        """
        # 1. Session cookie
        session_token = self.get_cookie("nt_session")
        if session_token and self.auth_manager:
            is_valid, user = self.auth_manager.validate_token(session_token)
            if is_valid:
                return True, user

        # 2. Authorization header: Bearer <token>
        auth_header = self.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            bearer = auth_header.split(" ", 1)[1].strip()
            if self.auth_manager:
                is_valid, user = self.auth_manager.validate_token(bearer)
                if is_valid:
                    return True, user
            if hmac.compare_digest(bearer, self.ztoken):
                return True, "ztoken_user"

        # 3. X-Auth-Token header
        x_token = self.headers.get("X-Auth-Token")
        if x_token:
            if self.auth_manager:
                is_valid, user = self.auth_manager.validate_token(x_token)
                if is_valid:
                    return True, user
            if hmac.compare_digest(x_token, self.ztoken):
                return True, "ztoken_user"

        # 4. Legacy ztoken matching
        if body_token and hmac.compare_digest(body_token, self.ztoken):
            return True, "ztoken_user"

        return False, None

    # ------------------------------------------------------------------
    # HTTP Method Handlers
    # ------------------------------------------------------------------

    def do_GET(self):
        """Handle GET requests."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        # API: Auth status
        if path in ("/api/auth/status", "/api/me"):
            is_auth, user = self.is_authenticated()
            self.send_json(200, {
                "authenticated": is_auth,
                "user": user or None
            })
            return

        # API: Health check
        if path in ("/api/health", "/health"):
            self.send_json(200, {"status": "healthy", "service": "witchcraftfex-server"})
            return

        # API: Real-time System Statistics Dashboard
        if path in ("/api/system/stats", "/api/stats"):
            try:
                from witchcraft.modules.system.nt_stats import get_system_metrics
                stats = get_system_metrics()
                self.send_json(200, stats)
            except Exception as e:
                self.send_json(500, {"error": f"Failed to get stats: {str(e)}"})
            return

        # API: Harpia MCP Tools List
        if path == "/api/harpia/tools":
            try:
                if self.project_root not in sys.path:
                    sys.path.insert(0, self.project_root)
                from witchcraft.interface.mcp.mcp_server import WitchcraftMCPServer
                mcp = WitchcraftMCPServer()
                self.send_json(200, {"tools": mcp.get_tools()})
            except Exception as e:
                self.send_json(500, {"error": f"Failed to list MCP tools: {str(e)}"})
            return

        # Static file serving
        self.serve_file(path)

    def do_POST(self):
        """Handle POST requests (Login, Logout, Exec, Harpia Chat)."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        # Read body with safety limit (64 KB)
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 65536:
            self.send_json(413, {"error": "Payload too large"})
            return

        body = self.rfile.read(content_length).decode("utf-8", errors="replace") if content_length > 0 else ""

        # Route: Login (/api/login or /login)
        if path in ("/api/login", "/login"):
            self.handle_login(body)
            return

        # Route: Logout (/api/logout or /logout)
        if path in ("/api/logout", "/logout"):
            self.handle_logout()
            return

        # Route: Harpia AI + MCP Chat (/api/harpia/chat)
        if path == "/api/harpia/chat":
            self.handle_harpia_chat(body)
            return

        # Route: Command Execution (/api/exec or root /)
        if path in ("/api/exec", "/"):
            self.handle_exec(body)
            return

        self.send_json(404, {"error": "Not Found"})

    # ------------------------------------------------------------------
    # Feature Handlers
    # ------------------------------------------------------------------

    def handle_login(self, body: str):
        """Authenticate user and return session token / cookie."""
        username = ""
        password = ""

        content_type = self.headers.get("Content-Type", "")
        if "application/json" in content_type:
            try:
                data = json.loads(body)
                username = data.get("username", "")
                password = data.get("password", "")
            except Exception:
                self.send_json(400, {"error": "Invalid JSON payload"})
                return
        else:
            form = urllib.parse.parse_qs(body)
            username = form.get("username", [""])[0]
            password = form.get("password", [""])[0]

        if not username or not password:
            self.send_json(400, {"error": "Username and password required"})
            return

        if not self.auth_manager or not self.auth_manager.verify_credentials(username, password):
            if self.logger:
                self.logger.warning(f"Failed login attempt for user: {username} from {self.client_address[0]}")
            self.send_json(401, {"error": "Invalid username or password"})
            return

        # Generate signed session token
        token = self.auth_manager.create_token(username)
        cookie_header = f"nt_session={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={SESSION_TIMEOUT_SEC}"

        if self.logger:
            self.logger.info(f"Successful login for user: {username} from {self.client_address[0]}")

        self.send_json(200, {
            "status": "success",
            "message": "Authenticated successfully",
            "user": username,
            "token": token,
            "expires_in": SESSION_TIMEOUT_SEC
        }, headers={"Set-Cookie": cookie_header})

    def handle_logout(self):
        """Invalidate session and clear cookie."""
        session_token = self.get_cookie("nt_session")
        if session_token and self.auth_manager:
            self.auth_manager.revoke_token(session_token)

        clear_cookie = "nt_session=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"
        self.send_json(200, {
            "status": "success",
            "message": "Logged out successfully"
        }, headers={"Set-Cookie": clear_cookie})

    def handle_harpia_chat(self, body: str):
        """Handle Harpia AI chat and MCP tool execution requests."""
        try:
            data = json.loads(body) if body else {}
        except Exception:
            self.send_json(400, {"error": "Invalid JSON payload"})
            return

        body_ztoken = data.get("ztoken")
        is_auth, _ = self.is_authenticated(body_token=body_ztoken)
        if not is_auth:
            self.send_json(401, {"error": "Unauthorized: valid session or ztoken required"})
            return

        prompt = str(data.get("prompt", "")).strip()
        history = data.get("history") or []
        direct_tool = data.get("tool")

        if not prompt and not direct_tool:
            self.send_json(400, {"error": "Prompt or tool is required"})
            return

        try:
            if self.project_root not in sys.path:
                sys.path.insert(0, self.project_root)
            from witchcraft.interface.ai.harpia_agent import harpia_chat
            result = harpia_chat(prompt=prompt, history=history, direct_tool=direct_tool)
            self.send_json(200, result)
        except Exception as e:
            self.send_json(500, {"error": f"Harpia execution failed: {str(e)}"})

    def handle_exec(self, body: str):
        """Execute WitchcraftFEX command with authentication check."""
        content_type = self.headers.get("Content-Type", "")
        cmdline = []
        body_ztoken = None

        if "application/json" in content_type:
            try:
                data = json.loads(body)
                body_ztoken = data.get("ztoken")
                cmdline = build_command_from_json(data)
            except Exception as e:
                self.send_json(400, {"error": f"Bad Request: {str(e)}"})
                return
        else:
            form_data = urllib.parse.parse_qs(body)
            for tok in form_data.get("ztoken", []):
                if tok and str(tok).strip():
                    body_ztoken = str(tok).strip()
                    break
            try:
                cmdline = build_command_from_form(form_data)
            except Exception as e:
                self.send_json(400, {"error": f"Bad Request: {str(e)}"})
                return

        # Auth validation
        is_auth, user = self.is_authenticated(body_token=body_ztoken)
        if not is_auth:
            if self.logger:
                self.logger.warning(f"Unauthorized command execution attempt from {self.client_address[0]}")
            self.send_json(401, {"error": "Unauthorized: valid session or ztoken required"})
            return

        # Run command via main.py
        main_script = os.path.join(self.project_root, "main.py")
        exec_args = [sys.executable, main_script] + cmdline + ["--output_mode_html"]

        if self.logger:
            self.logger.info(f"Executing: {' '.join(cmdline)} (by {user})")

        try:
            result = subprocess.run(
                exec_args,
                capture_output=True,
                text=True,
                timeout=EXEC_TIMEOUT_SEC,
                cwd=self.project_root
            )

            output = result.stdout
            if result.stderr:
                output += f"\n{result.stderr}"

            if result.returncode == 0:
                self.send_text(200, output, content_type="text/html; charset=utf-8")
            else:
                exit_notice = ""
                if result.returncode == 2:
                    exit_notice = "\n[Notice] Exited with code 2: possible invalid arguments or parser error."
                error_msg = f"Exec Error (status {result.returncode}):\n{output}{exit_notice}"
                self.send_text(500, error_msg, content_type="text/plain; charset=utf-8")

        except subprocess.TimeoutExpired:
            self.send_json(504, {"error": f"Command timed out after {EXEC_TIMEOUT_SEC} seconds"})
        except FileNotFoundError:
            self.send_json(500, {"error": "main.py script not found"})
        except Exception as e:
            self.send_json(500, {"error": f"Internal execution error: {str(e)}"})

    def serve_file(self, req_path: str):
        """Safely serve static files from configured folder."""
        clean_path = os.path.normpath(req_path)
        if clean_path in ("/", "."):
            clean_path = "/index.html"

        clean_path = clean_path.lstrip("/")
        full_path = os.path.join(self.server_folder, clean_path)

        # Path traversal protection
        real_folder = os.path.realpath(self.server_folder)
        real_target = os.path.realpath(full_path)

        try:
            common = os.path.commonpath([real_folder, real_target])
            if common != real_folder:
                self.send_json(403, {"error": "Access Denied"})
                return
        except ValueError:
            self.send_json(403, {"error": "Access Denied"})
            return

        if not os.path.exists(real_target) or os.path.isdir(real_target):
            self.send_json(404, {"error": f"File not found: {clean_path}"})
            return

        try:
            with open(real_target, "rb") as f:
                content = f.read()

            content_type, _ = mimetypes.guess_type(real_target)
            if not content_type:
                content_type = "application/octet-stream"

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_json(500, {"error": f"Error reading file: {str(e)}"})

    def log_message(self, format, *args):
        """Override to use configured logger."""
        if self.logger:
            self.logger.info(f"{self.client_address[0]} - {format % args}")


# ----------------------------------------------------------------------
# Threaded Server Factory & Runner
# ----------------------------------------------------------------------

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Multi-threaded HTTP Server."""
    daemon_threads = True
    allow_reuse_address = True


def create_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    folder: str = DEFAULT_FOLDER,
    ztoken: str = DEFAULT_ZTOKEN,
    username: str = DEFAULT_USER,
    password: str = DEFAULT_PASS,
    project_root: str = "."
) -> Tuple[ThreadedHTTPServer, WitchcraftRequestHandler]:
    """Create and configure a threaded WitchcraftFEX HTTP Server."""

    # Set up logger
    logger = logging.getLogger("witchcraftfex.server")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
        logger.addHandler(handler)

    # Configure handler class
    handler_class = WitchcraftRequestHandler
    handler_class.server_folder = os.path.abspath(folder)
    handler_class.ztoken = ztoken
    handler_class.auth_manager = AuthManager(username=username, password=password)
    handler_class.logger = logger
    handler_class.project_root = os.path.abspath(project_root)

    server = ThreadedHTTPServer((host, port), handler_class)
    return server, handler_class


def run_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    folder: str = DEFAULT_FOLDER,
    ztoken: str = DEFAULT_ZTOKEN,
    username: str = DEFAULT_USER,
    password: str = DEFAULT_PASS,
    project_root: str = "."
):
    """Start and run the HTTP server indefinitely."""
    httpd, _ = create_server(
        host=host,
        port=port,
        folder=folder,
        ztoken=ztoken,
        username=username,
        password=password,
        project_root=project_root
    )

    print(f"[*] WitchcraftFEX Python Server listening on http://{host}:{port}")
    print(f"[*] Serving static files from: {os.path.abspath(folder)}")
    print(f"[*] Default Admin User: {username}")
    print(f"[*] Press Ctrl+C to terminate.")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Shutting down server gracefully...")
        httpd.shutdown()
        httpd.server_close()


# ----------------------------------------------------------------------
# CLI Entry Point
# ----------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="WitchcraftFEX Python HTTP Server")
    parser.add_argument("pos_host", nargs="?", default=None, help="Host address")
    parser.add_argument("pos_port", nargs="?", default=None, help="Port number")
    parser.add_argument("pos_folder", nargs="?", default=None, help="Static files folder")
    parser.add_argument("pos_ztoken", nargs="?", default=None, help="Signature token (ztoken)")

    parser.add_argument("--host", default=None, help="Host address")
    parser.add_argument("--port", type=int, default=None, help="Port number")
    parser.add_argument("--folder", default=None, help="Folder to serve")
    parser.add_argument("--ztoken", default=None, help="Signature token")
    parser.add_argument("--user", default=DEFAULT_USER, help="Admin username for login")
    parser.add_argument("--password", default=DEFAULT_PASS, help="Admin password for login")
    parser.add_argument("--root", default=".", help="Project root directory containing main.py")

    args = parser.parse_args()

    host = args.host or args.pos_host or DEFAULT_HOST
    port = args.port or (int(args.pos_port) if args.pos_port else DEFAULT_PORT)
    folder = args.folder or args.pos_folder or DEFAULT_FOLDER
    ztoken = args.ztoken or args.pos_ztoken or DEFAULT_ZTOKEN

    run_server(
        host=host,
        port=port,
        folder=folder,
        ztoken=ztoken,
        username=args.user,
        password=args.password,
        project_root=args.root
    )
