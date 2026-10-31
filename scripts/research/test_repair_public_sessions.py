import copy
import json
import unittest
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from repair_public_sessions import complete_hourly_grid_on


def payload():
    start = int(datetime(2026,9,7,7,tzinfo=timezone.utc).timestamp())
    timestamps = list(range(start,start+9*3600,3600))
    r = {'meta':{'dataGranularity':'1h','tradingPeriods':[[{'start':start,'end':start+8*3600+1800}]]},
         'timestamp':timestamps,'indicators':{'quote':[{'open':[100.]*9,'high':[101.]*9,'low':[99.]*9,'close':[100.]*9}]}}
    return {'chart':{'result':[r]}}


def check(obj):
    return complete_hourly_grid_on(json.dumps(obj).encode(),date(2026,9,7),ZoneInfo('Europe/Berlin'))


class HourlyGridTests(unittest.TestCase):
    def test_complete_regular_grid(self):
        self.assertTrue(check(payload()))
    def test_missing_hour_rejected(self):
        obj=payload();obj['chart']['result'][0]['timestamp'].pop(3)
        self.assertFalse(check(obj))
    def test_null_price_rejected(self):
        obj=payload();obj['chart']['result'][0]['indicators']['quote'][0]['low'][4]=None
        self.assertFalse(check(obj))
    def test_invalid_price_order_rejected(self):
        obj=payload();obj['chart']['result'][0]['indicators']['quote'][0]['low'][4]=102
        self.assertFalse(check(obj))
    def test_wrong_granularity_rejected(self):
        obj=payload();obj['chart']['result'][0]['meta']['dataGranularity']='1d'
        self.assertFalse(check(obj))
    def test_outside_tail_point_not_used(self):
        obj=payload();r=obj['chart']['result'][0];r['timestamp'].append(r['timestamp'][-1]+86400)
        for k in ('open','high','low','close'):r['indicators']['quote'][0][k].append(99999.)
        self.assertTrue(check(obj))


if __name__=='__main__':
    unittest.main()
