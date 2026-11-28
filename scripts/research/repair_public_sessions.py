"""Targeted public-history repairs. Never interpolate absent prices.

A complete regular hourly grid is a disclosed reconstruction input, not an official
closing-auction certification. Acquisition success does not approve a backtest.
"""
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json
import math
import sys
import time
from collect_public_history import chart_url, fetch, write_json, digest


def complete_observation_on(payload, day, zone):
    result = json.loads(payload)['chart']['result'][0]
    quote = result['indicators']['quote'][0]
    return any(datetime.fromtimestamp(ts, zone).date() == day and
               all(quote[k][i] is not None for k in ['open','high','low','close'])
               for i, ts in enumerate(result['timestamp']))


def complete_hourly_grid_on(payload, day, zone):
    """Reject missing intervals/invalid prices; ignore out-of-session tail points."""
    try:
        r = json.loads(payload)['chart']['result'][0]
        if r['meta']['dataGranularity'] not in ('1h','60m'):
            return False
        periods = [p for group in r['meta']['tradingPeriods'] for p in group
                   if datetime.fromtimestamp(p['start'], zone).date() == day]
        if len(periods) != 1:
            return False
        p = periods[0]
        expected = list(range(p['start'], p['end'], 3600))
        if not expected:
            return False
        rows = [(ts, i) for i, ts in enumerate(r['timestamp']) if p['start'] <= ts < p['end']]
        if [ts for ts, i in rows] != expected:
            return False
        q = r['indicators']['quote'][0]
        for ts, i in rows:
            values = [q[k][i] for k in ('open','high','low','close')]
            if any(v is None or not math.isfinite(v) or v <= 0 for v in values):
                return False
            o,h,l,c = values
            if l > min(o,c) or h < max(o,c) or l > h:
                return False
        return True
    except (KeyError, TypeError, ValueError, IndexError):
        return False


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
                hourly['regular_grid_complete'] = hourly['status'] == 'FETCHED' and complete_hourly_grid_on(hourly_path.read_bytes(), day, zone)
                hourly['aggregation_review_required'] = True
                hourly['certified_daily_close'] = False
                record['intraday_attempt'] = hourly
                time.sleep(1)
            records.append(record)
            write_json(root / 'repair_manifest.json', records)
            print(symbol, day, 'daily_repaired=', record['repair_verified'], 'complete_hourly_grid=', record.get('intraday_attempt', {}).get('regular_grid_complete'), flush=True)
            time.sleep(1)
    children = []
    for symbol in ['HONA','MBGL']:
        path = root / 'children' / (symbol + '.json')
        rec = fetch(chart_url(symbol, '2026-06-01', manifest['end']), path, 'yahoo', symbol)
        children.append(rec)
        time.sleep(1)
    write_json(root / 'child_manifest.json', children)
    daily = sum(r['repair_verified'] for r in records)
    hourly = sum(r.get('intraday_attempt', {}).get('regular_grid_complete', False) for r in records)
    summary = {'null_session_requests':len(records),'daily_repairs':daily,'complete_hourly_grids':hourly,
               'reconstructed_sessions_require_review':hourly,'certified_daily_close_claim':False}
    write_json(root / 'repair_summary.json', summary)
    print(json.dumps(summary))
    return 0 if daily + hourly == len(records) and all(c['status']=='FETCHED' for c in children) else 2


if __name__ == '__main__':
    raise SystemExit(main())
