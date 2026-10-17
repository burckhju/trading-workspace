import importlib.util
import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path

MODULE = Path(__file__).with_name('collect_public_history.py')
spec = importlib.util.spec_from_file_location('collector', MODULE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def sample(symbol='TEST'):
    return json.dumps({'chart': {'error': None, 'result': [{'meta': {'symbol': symbol, 'currency': 'USD'}, 'timestamp': [1, 2], 'indicators': {'quote': [{k: [10, 11] for k in ['open', 'high', 'low', 'close', 'volume']}]}}]}}).encode()


class Response(io.BytesIO):
    status = 200


class Opener:
    def __init__(self, value):
        self.value = value
        self.calls = 0
    def open(self, request, timeout):
        self.calls += 1
        if isinstance(self.value, Exception):
            raise self.value
        return Response(self.value)


class Tests(unittest.TestCase):
    def test_symbol_sort(self):
        self.assertEqual(m.validate_symbols(['MSFT', 'AAPL']), ['AAPL', 'MSFT'])
    def test_reject_path(self):
        with self.assertRaises(ValueError): m.validate_symbols(['../secret'])
    def test_reject_duplicates(self):
        with self.assertRaises(ValueError): m.validate_symbols(['AAPL', 'AAPL'])
    def test_reject_empty(self):
        with self.assertRaises(ValueError): m.validate_symbols([])
    def test_reject_large(self):
        with self.assertRaises(ValueError): m.validate_symbols([str(i) for i in range(151)])
    def test_inclusive_end(self):
        url = m.chart_url('AAPL', '2026-01-01', '2026-01-02')
        self.assertIn('period2=1767398400', url)
    def test_reject_future(self):
        with self.assertRaises(ValueError): m.chart_url('AAPL', '2026-01-01', '2099-01-01')
    def test_payload(self):
        self.assertEqual(m.validate_payload(sample(), 'yahoo', 'TEST')['records'], 2)
    def test_identity_mismatch(self):
        with self.assertRaises(ValueError): m.validate_payload(sample(), 'yahoo', 'OTHER')
    def test_misaligned_arrays(self):
        p = json.loads(sample()); p['chart']['result'][0]['timestamp'].append(3)
        with self.assertRaises(ValueError): m.validate_payload(json.dumps(p).encode(), 'yahoo', 'TEST')
    def test_sorted_timestamps(self):
        p = json.loads(sample()); p['chart']['result'][0]['timestamp'] = [2, 1]
        with self.assertRaises(ValueError): m.validate_payload(json.dumps(p).encode(), 'yahoo', 'TEST')
    def test_ecb(self):
        p = b'<Envelope><Cube><Cube time="2026-01-02"><Cube currency="USD" rate="1.2"/></Cube></Cube></Envelope>'
        self.assertEqual(m.validate_payload(p, 'ecb')['observation_days'], 1)
    def test_preserves_bytes_and_cache(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'raw.json'; op = Opener(sample())
            url = m.chart_url('TEST', '2026-01-01', '2026-01-02')
            result = m.fetch(url, path, 'yahoo', 'TEST', opener=op, sleeper=lambda n: None)
            self.assertEqual(result['status'], 'FETCHED'); self.assertEqual(path.read_bytes(), sample())
            cached = m.fetch(url, path, 'yahoo', 'TEST', opener=op, sleeper=lambda n: None)
            self.assertTrue(cached['cache_hit']); self.assertEqual(op.calls, 1)
    def test_tamper_forces_refetch(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'raw.json'; op = Opener(sample())
            url = m.chart_url('TEST', '2026-01-01', '2026-01-02')
            m.fetch(url, path, 'yahoo', 'TEST', opener=op, sleeper=lambda n: None)
            path.write_bytes(b'bad')
            m.fetch(url, path, 'yahoo', 'TEST', opener=op, sleeper=lambda n: None)
            self.assertEqual(op.calls, 2)
    def test_forbidden_not_retried(self):
        with tempfile.TemporaryDirectory() as d:
            url = m.chart_url('TEST', '2026-01-01', '2026-01-02')
            op = Opener(urllib.error.HTTPError(url, 403, 'forbidden', {}, None))
            result = m.fetch(url, Path(d)/'raw.json', 'yahoo', 'TEST', opener=op, sleeper=lambda n: None)
            self.assertEqual(op.calls, 1); self.assertEqual(result['status'], 'FAILED')
            self.assertFalse((Path(d)/'raw.json').exists())
    def test_allowlist(self):
        with self.assertRaises(ValueError): m.fetch('https://example.com/private', Path('/tmp/no-file'), 'yahoo')
    def test_long_retry_after_not_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            url = m.chart_url('TEST', '2026-01-01', '2026-01-02')
            op = Opener(urllib.error.HTTPError(url, 429, 'rate limited', {'Retry-After': '300'}, None))
            m.fetch(url, Path(d)/'raw.json', 'yahoo', 'TEST', opener=op, sleeper=lambda n: None)
            self.assertEqual(op.calls, 1)


if __name__ == '__main__':
    unittest.main()
