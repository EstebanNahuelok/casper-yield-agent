#!/usr/bin/env python3
"""
Transparent HTTP proxy that adds CSPR.cloud auth headers.
- Port 7777 → https://node.testnet.cspr.cloud        (JSON-RPC)
- Port 9999 → https://node-sse.testnet.cspr.cloud    (SSE events)

Auth format per docs: Authorization: <token>  (no "Bearer" prefix)

Usage:
    export CSPR_CLOUD_AUTH_TOKEN=your_token_here
    python3 scripts/cspr_proxy.py
"""
import http.server
import urllib.request
import urllib.error
import os
import sys
import threading

RPC_UPSTREAM  = "https://node.testnet.cspr.cloud"
SSE_UPSTREAM  = "https://node-sse.testnet.cspr.cloud"
RPC_PORT      = 7777
EVENTS_PORT   = 9999
TOKEN         = os.environ.get("CSPR_CLOUD_AUTH_TOKEN", "")


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    upstream_host = RPC_UPSTREAM   # overridden per subclass

    def log_message(self, fmt, *args):
        print(f"[proxy:{self.server.server_port}] {fmt % args}", flush=True)

    def _auth_header(self):
        # CSPR.cloud: raw token, no "Bearer" prefix
        return {"Authorization": TOKEN} if TOKEN else {}

    def do_GET(self):
        upstream_url = f"{self.upstream_host}{self.path}"
        headers = {k: v for k, v in self.headers.items()
                   if k.lower() not in ("host", "connection")}
        headers.update(self._auth_header())

        req = urllib.request.Request(upstream_url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=None) as resp:
                self.send_response(resp.status)
                for k, v in resp.headers.items():
                    if k.lower() not in ("transfer-encoding", "connection"):
                        self.send_header(k, v)
                self.end_headers()
                while True:
                    chunk = resp.read(4096)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
        except urllib.error.HTTPError as e:
            body = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            self.send_error(502, str(e))

    def do_POST(self):
        upstream_url = f"{self.upstream_host}{self.path}"
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        headers = {
            "Content-Type": self.headers.get("Content-Type", "application/json"),
            "Content-Length": str(len(body)),
        }
        headers.update(self._auth_header())

        req = urllib.request.Request(upstream_url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
                self.send_response(resp.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            data = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_error(502, str(e))


class RpcProxyHandler(ProxyHandler):
    upstream_host = RPC_UPSTREAM


class SseProxyHandler(ProxyHandler):
    upstream_host = SSE_UPSTREAM


def run_server(handler_class, port):
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler_class)
    server.server_port = port
    print(f"[proxy] :{port} → {handler_class.upstream_host}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    if not TOKEN:
        print("ERROR: CSPR_CLOUD_AUTH_TOKEN not set", file=sys.stderr)
        print("  export CSPR_CLOUD_AUTH_TOKEN=your_token_here", file=sys.stderr)
        sys.exit(1)

    print(f"[proxy] Token: {TOKEN[:8]}... ({len(TOKEN)} chars)", flush=True)
    print(f"[proxy] Auth:  Authorization: {TOKEN[:6]}...  (no Bearer prefix)", flush=True)

    t1 = threading.Thread(target=run_server, args=(RpcProxyHandler, RPC_PORT), daemon=True)
    t2 = threading.Thread(target=run_server, args=(SseProxyHandler, EVENTS_PORT), daemon=True)
    t1.start()
    t2.start()

    print("[proxy] Running. Ctrl+C to stop.", flush=True)
    try:
        t1.join()
    except KeyboardInterrupt:
        print("\n[proxy] Stopped.")
