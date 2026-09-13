"""Targeted public-history repairs. Never interpolate absent prices.

Hourly fallback is evidence for a separate, locally reviewed session aggregation,
not automatically a certified daily bar or an official closing-auction price.
"""
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json
import sys
import time
from collect_public_history import chart_url, fetch, write_json, digest


def complete_observation_on(payload, day, zone):
    result = json.loads(payload)['chart']['result'][0]
    quote = result['indicators']['quote'][0]
    return any(datetime.fromtimestamp(ts, zone).date() == day and
               all(quote[k][i] is not None for k in ['open','high','low','close'])
               for i, ts in enumerate(result['timestamp']))


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
            if all(quote[k][i] is not None for k in ['open','high','low','close']):
                continue
            start = (day - timedelta(days=1)).isoformat()
            end = min((day + timedelta(days=1)).isoformat(), manifest['end'])
            path = root / 'repairs' / symbol / (day.isoformat() + '.json')
            record = fetch(chart_url(symbol, start, end), path, 'yahoo', symbol)
            record.update(missing_date=day.isoformat(), original_raw_sha256=rec['sha256'], repair_verified=False)
            if record['status'] == 'FETCHED':
                record['repair_verified'] = complete_observation_on(path.read_bytes(), day, zone)
            if not record['repair_verified']:
                hourly_path = root / 'intraday' / symbol / (day.isoformat() + '.json')
                url = chart_url(symbol, day.isoformat(), day.isoformat()).replace('interval=1d', 'interval=60m') + '&includePrePost=false'
                hourly = fetch(url, hourly_path, 'yahoo', symbol)
                hourly['contains_missing_day'] = hourly['status'] == 'FETCHED' and complete_observation_on(hourly_path.read_bytes(), day, zone)
                hourly['aggregation_review_required'] = True
                record['intraday_attempt'] = hourly
                time.sleep(1)
            records.append(record)
            write_json(root / 'repair_manifest.json', records)
            print(symbol, day, 'daily_repaired=', record['repair_verified'], 'hourly_day_available=', record.get('intraday_attempt', {}).get('contains_missing_day'), flush=True)
            time.sleep(1)
    children = []
    for symbol in ['HONA','MBGL']:
        path = root / 'children' / (symbol + '.json')
        rec = fetch(chart_url(symbol, '2026-06-01', manifest['end']), path, 'yahoo', symbol)
        children.append(rec)
        time.sleep(1)
    write_json(root / 'child_manifest.json', children)
    daily = sum(r['repair_verified'] for r in records)
    hourly = sum(r.get('intraday_attempt', {}).get('contains_missing_day', False) for r in records)
    print(json.dumps({'null_session_requests':len(records), 'daily_repairs':daily, 'hourly_evidence':hourly}))
    return 0 if daily == len(records) else 2


if __name__ == '__main__':
    raise SystemExit(main())
