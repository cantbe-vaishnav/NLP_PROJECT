"""Inspect public metadata and a bounded preview; never accepts dataset labels."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import ssl
import urllib.error
import urllib.request

from task_a.audit import summarize_sample


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='configs/task_a_source_audit.json')
    parser.add_argument('--ca-file', default=None)
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text())
    context = ssl.create_default_context(cafile=args.ca_file)
    results = {}
    for name, spec in config['sources'].items():
        item = {'url': spec['url'], 'method': spec['method']}
        try:
            request = urllib.request.Request(spec['url'], method=spec['method'])
            with urllib.request.urlopen(request, timeout=config['timeout_seconds'],
                                        context=context) as response:
                raw = response.read() if spec['method'] != 'HEAD' else b''
                item.update(status=response.status, bytes_received=len(raw),
                            sha256=hashlib.sha256(raw).hexdigest())
                if raw:
                    payload = json.loads(raw)
                    if spec['kind'] == 'metadata':
                        item.update({k: payload.get(k) for k in
                                     ['id', 'sha', 'gated', 'cardData', 'siblings']})
                    elif spec['kind'] == 'samples':
                        item['features'] = payload.get('features')
                        item['rows'] = payload['rows']
                        item['summary'] = summarize_sample(payload['rows'])
                        item['revision_binding'] = 'preview API is not revision-pinned'
        except urllib.error.HTTPError as error:
            item.update(status=error.code, error='HTTP access failure')
        except (OSError, ValueError, KeyError) as error:
            item.update(status=None, error=str(error))
        results[name] = item
    report = {'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
              'config': config, 'sources': results}
    output = Path(config['output'])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n')
    summary = {**report, 'sources': {
        name: {k: v for k, v in item.items() if k not in ['rows', 'cardData', 'siblings']}
        for name, item in results.items()}}
    path = Path(config['summary'])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))
    # Access denials are observations; other fetch errors must fail the audit.
    if any(item.get('status') not in {200, 401, 403} for item in results.values()):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
