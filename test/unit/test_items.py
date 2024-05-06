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
Unit test suite for items module
"""
import unittest
from datetime import timezone, datetime, timedelta
from unittest.mock import Mock

from aws_secretsmanager_caching.cache.items import SecretCacheObject, SecretCacheItem
from aws_secretsmanager_caching.config import SecretCacheConfig


class TestSecretCacheObject(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    class TestObject(SecretCacheObject):

        def __init__(self, config, client, secret_id):
            super(TestSecretCacheObject.TestObject, self).__init__(config, client, secret_id)

        def _execute_refresh(self):
            super(TestSecretCacheObject.TestObject, self)._execute_refresh()

        def _get_version(self, version_stage):
            return super(TestSecretCacheObject.TestObject, self)._get_version(version_stage)

    def test_simple(self):
        sco = TestSecretCacheObject.TestObject(SecretCacheConfig(), None, None)
        self.assertIsNone(sco.get_secret_value())

    def test_simple_2(self):
        sco = TestSecretCacheObject.TestObject(SecretCacheConfig(), None, None)
        self.assertIsNone(sco.get_secret_value())
        sco._exception = Exception("test")
        self.assertRaises(Exception, sco.get_secret_value)

    def test_refresh_now(self):
        config = SecretCacheConfig()

        client_mock = Mock()
        client_mock.describe_secret = Mock()
        client_mock.describe_secret.return_value = "test"
        secret_cache_item = SecretCacheItem(config, client_mock, None)
        secret_cache_item._next_refresh_time = datetime.now(timezone.utc) + timedelta(days=30)
        secret_cache_item._refresh_needed = False
        self.assertFalse(secret_cache_item._is_refresh_needed())

        old_refresh_time = secret_cache_item._next_refresh_time
        self.assertTrue(old_refresh_time > datetime.now(timezone.utc) + timedelta(days=29))

        secret_cache_item.refresh_secret_now()
        new_refresh_time = secret_cache_item._next_refresh_time

        ttl = config.secret_refresh_interval

        # New refresh time will use the ttl and will be less than the old refresh time that was artificially set a month ahead
        # The new refresh time will be between now + ttl and now + (ttl / 2) if the secret was immediately refreshed
        self.assertTrue(new_refresh_time < old_refresh_time and new_refresh_time < datetime.now(timezone.utc) + timedelta(ttl))

        
    def test_datetime_fix_is_refresh_needed(self):
        secret_cached_object = TestSecretCacheObject.TestObject(SecretCacheConfig(), None, None)

        # Variable values set in order to be able to test modified line with assert statement (False is not None)
        secret_cached_object._next_retry_time = datetime.now(tz=timezone.utc)
        secret_cached_object._refresh_needed = False
        secret_cached_object._exception = not None

        self.assertTrue(secret_cached_object._is_refresh_needed())

    def test_datetime_fix_refresh(self):
        exp_factor = 11

        secret_cached_object = SecretCacheObject(
            SecretCacheConfig(exception_retry_delay_base=1, exception_retry_growth_factor=2),
            None, None
        )
        secret_cached_object._set_result = Mock(side_effect=Exception("exception used for test"))
        secret_cached_object._refresh_needed = True
        secret_cached_object._exception_count = exp_factor  # delay = min(1*(2^exp_factor) = 2048, 3600)

        t_before = datetime.now(tz=timezone.utc)
        secret_cached_object._SecretCacheObject__refresh()
        t_after = datetime.now(tz=timezone.utc)

        t_before_delay = t_before + timedelta(
            milliseconds=secret_cached_object._config.exception_retry_delay_base * (
                secret_cached_object._config.exception_retry_growth_factor ** exp_factor
            )
        )
        self.assertLessEqual(t_before_delay, secret_cached_object._next_retry_time)

        t_after_delay = t_after + timedelta(
            milliseconds=secret_cached_object._config.exception_retry_delay_base * (
                secret_cached_object._config.exception_retry_growth_factor ** exp_factor
            )
        )
        self.assertGreaterEqual(t_after_delay, secret_cached_object._next_retry_time)


class TestSecretCacheItem(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_datetime_fix_SCI_init(self):
        config = SecretCacheConfig()
        t_before = datetime.now(tz=timezone.utc)
        secret_cache_item = SecretCacheItem(config, None, None)
        t_after = datetime.now(tz=timezone.utc)

        self.assertGreaterEqual(secret_cache_item._next_refresh_time, t_before)
        self.assertLessEqual(secret_cache_item._next_refresh_time, t_after)

    def test_datetime_fix_refresh_needed(self):
        config = SecretCacheConfig()
        secret_cache_item = SecretCacheItem(config, None, None)

        # Variable values set in order to be able to test modified line with assert statement (False is not None)
        secret_cache_item._refresh_needed = False
        secret_cache_item._exception = False
        secret_cache_item._next_retry_time = None

        self.assertTrue(secret_cache_item._is_refresh_needed())

    def test_datetime_fix_execute_refresh(self):
        client_mock = Mock()
        client_mock.describe_secret = Mock()
        client_mock.describe_secret.return_value = "test"

        config = SecretCacheConfig()
        secret_cache_item = SecretCacheItem(config, client_mock, None)

        t_before = datetime.now(tz=timezone.utc)
        secret_cache_item._execute_refresh()
        t_after = datetime.now(tz=timezone.utc)

        # Make sure that the timezone is correctly set
        self.assertEqual(secret_cache_item._next_refresh_time.tzinfo, timezone.utc)

        # Check that secret_refresh_interval addition works as intended
        self.assertGreaterEqual(secret_cache_item._next_refresh_time, t_before)
        t_max_after = t_after + timedelta(seconds=config.secret_refresh_interval)
        self.assertLessEqual(secret_cache_item._next_refresh_time, t_max_after)
