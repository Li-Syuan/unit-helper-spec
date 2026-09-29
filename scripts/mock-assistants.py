"""Run the synthetic Assistants protocol fixture on loopback only."""
import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_support.assistants_mock import AssistantsMock


def main():
    parser = argparse.ArgumentParser(description='QA agent 協定模擬服務：僅合成資料，未連公司')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('port must be 1024..65535')
    fixture = AssistantsMock()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.respond()

        def do_POST(self):
            self.respond()

        def log_message(self, *args):
            pass  # No headers, credentials or request bodies in logs.

        def respond(self):
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 <= length <= 1000000:
                    raise ValueError()
                body = json.loads(self.rfile.read(length)) if length else {}
                url = urlsplit(self.path)
                status, value = fixture.dispatch(self.command, url.path, body, parse_qs(url.query))
            except (ValueError, KeyError, TypeError):
                status, value = 400, {'error': {'message': 'invalid synthetic request'}}
            encoded = json.dumps(value, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print('QA agent SYNTHETIC ONLY http://127.0.0.1:' + str(args.port) + '/v1')
    print('供 SDK 測試使用；正式 App 保持 HTTPS 檢查，不把本服務當成公司連線。')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
