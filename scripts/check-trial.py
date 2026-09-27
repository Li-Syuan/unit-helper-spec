"""Safe local key check; --live explicitly sends one synthetic request to Groq."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from desktop_app.trial import GroqAssistant, read_key
from desktop_app.gateways import GatewayError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    if sys.version_info[:3] != (3, 10, 4):
        raise SystemExit('Use project Python 3.10.4')
    result = {'key_configured':False, 'external_service':'not_tested'}
    try:
        read_key()
        result['key_configured'] = True
        if args.live:
            client = GroqAssistant()
            try:
                answer = client.respond([{'role':'user','content':'這是虛構測試。請只用一句繁體中文說明你可以協助整理文字。'}])
                result['external_service'] = 'external_real_passed'
                result['nonempty_response'] = bool(answer.strip())
            finally:
                client.close()
    except GatewayError as exc:
        result['error'] = str(exc)
        if args.live: result['external_service'] = 'failed'
    except Exception:
        result['error'] = 'Trial check failed; no raw provider errors recorded.'
    print(json.dumps(result, ensure_ascii=True))
    return int('error' in result)


if __name__ == '__main__':
    raise SystemExit(main())
