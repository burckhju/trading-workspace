"""Targeted, read-only repair attempts. Missing observations are never interpolated."""
from pathlib import Path
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import json
import sys
import time
from collect_public_history import chart_url, fetch, write_json, digest


def main():
    root = Path(sys.argv[1])
    manifest = json.loads((root / 'manifest.json').read_text())
    records = []
    for rec in manifest['records']:
        if rec['status'] != 'FETCHED':
            continue
        symbol = rec['symbol']
        payload = (root / 'raw' / (symbol + '.json')).read_bytes()
        if digest(payload) != rec['sha256']:
            raise ValueError('Source artifact hash mismatch')
        result = json.loads(payload)['chart']['result'][0]
        zone = ZoneInfo(result['meta']['exchangeTimezoneName'])
        quote = result['indicators']['quote'][0]
        for i, timestamp in enumerate(result['timestamp']):
            day = datetime.fromtimestamp(timestamp, zone).date()
            if day.isoformat() > manifest['end']:
                continue
            if all(quote[k][i] is not None for k in ['open', 'high', 'low', 'close']):
                continue
            start = (day - timedelta(days=1)).isoformat()
            end = min((day + timedelta(days=1)).isoformat(), manifest['end'])
            path = root / 'repairs' / symbol / (day.isoformat() + '.json')
            result_record = fetch(chart_url(symbol, start, end), path, 'yahoo', symbol)
            result_record['missing_date'] = day.isoformat()
            result_record['original_raw_sha256'] = rec['sha256']
            result_record['repair_verified'] = False
            if result_record['status'] == 'FETCHED':
                new = json.loads(path.read_bytes())['chart']['result'][0]
                nq = new['indicators']['quote'][0]
                for j, ts in enumerate(new['timestamp']):
                    observed = datetime.fromtimestamp(ts, zone).date()
                    if observed == day and all(nq[k][j] is not None for k in ['open', 'high', 'low', 'close']):
                        result_record['repair_verified'] = True
            records.append(result_record)
            write_json(root / 'repair_manifest.json', records)
            print(symbol, day, result_record['status'], 'actual_missing_day_present=', result_record['repair_verified'], flush=True)
            time.sleep(1)
    # Public child-company data only. Entitlement/valuation decisions remain local.
    children = []
    for symbol in ['HONA', 'MBGL']:
        path = root / 'children' / (symbol + '.json')
        rec = fetch(chart_url(symbol, '2026-06-01', manifest['end']), path, 'yahoo', symbol)
        children.append(rec)
        time.sleep(1)
    write_json(root / 'child_manifest.json', children)
    print(json.dumps({'null_session_requests': len(records), 'actual_repairs_obtained': sum(r['repair_verified'] for r in records)}))
    return 0 if all(r['repair_verified'] for r in records) else 2


if __name__ == '__main__':
    raise SystemExit(main())
