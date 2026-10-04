import pathlib
import sys
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from simulator import Cache

class CacheTests(unittest.TestCase):
    def test_repeated_address_hits(self):
        cache = Cache(1, 16, 1, 'rr')
        cache.access(0, 4, True)
        cache.access(0, 4, True)
        self.assertEqual((cache.accesses, cache.hits), (2, 1))
    def test_access_spanning_two_blocks(self):
        cache = Cache(1, 16, 1, 'rr')
        cache.access(15, 2, False)
        self.assertEqual((cache.accesses, cache.hits), (2, 0))
        cache.access(15, 2, False)
        self.assertEqual(cache.hits, 2)
    def test_direct_mapped_conflict(self):
        cache = Cache(1, 16, 1, 'rr')
        for address in (0, 1024, 0):
            cache.access(address, 1, False)
        self.assertEqual(cache.hits, 0)
        self.assertEqual(cache.conflict_misses, 2)
