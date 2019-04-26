# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
"""
Unit test suite for high-level functions in aws_secretsmanager_caching
"""
import unittest

import pytest
from aws_secretsmanager_caching.cache.lru import LRUCache

pytestmark = [pytest.mark.unit, pytest.mark.local]


class TestLRUCache(unittest.TestCase):

    def test_lru_cache_max(self):
        cache = LRUCache(max_size=10)
        for n in range(100):
            cache.put_if_absent(n, n)
        for n in range(90):
            self.assertIsNone(cache.get(n))
        for n in range(91, 100):
            self.assertIsNotNone(cache.get(n))

    def test_lru_cache_none(self):
        cache = LRUCache(max_size=10)
        self.assertIsNone(cache.get(1))

    def test_lru_cache_recent(self):
        cache = LRUCache(max_size=10)
        for n in range(100):
            cache.put_if_absent(n, n)
            cache.get(0)
        for n in range(1, 91):
            self.assertIsNone(cache.get(n))
        for n in range(92, 100):
            self.assertIsNotNone(cache.get(n))
        self.assertIsNotNone(cache.get(0))

    def test_lru_cache_zero(self):
        cache = LRUCache(max_size=0)
        for n in range(100):
            cache.put_if_absent(n, n)
            self.assertIsNone(cache.get(n))
        for n in range(100):
            self.assertIsNone(cache.get(n))

    def test_lru_cache_one(self):
        cache = LRUCache(max_size=1)
        for n in range(100):
            cache.put_if_absent(n, n)
            self.assertEquals(cache.get(n), n)
        for n in range(99):
            self.assertIsNone(cache.get(n))
        self.assertEquals(cache.get(99), 99)

    def test_lru_cache_if_absent(self):
        cache = LRUCache(max_size=1)
        for n in range(100):
            cache.put_if_absent(1000, 1000)
            self.assertIsNone(cache.get(n))
        self.assertEquals(cache.get(1000), 1000)
