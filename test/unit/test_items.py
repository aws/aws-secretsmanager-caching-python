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
    def test_datetime_fix_is_refresh_needed(self):
        sco = TestSecretCacheObject.TestObject(SecretCacheConfig(), None, None)

        # Used to pass branching requirements (False is not None)
        sco._next_retry_time = datetime.now(tz=timezone.utc)
        sco._refresh_needed = False
        sco._exception = not None

        self.assertTrue(sco._is_refresh_needed())

    def test_datetime_fix__refresh(self):
        exp_factor = 11

        sco = SecretCacheObject(
            SecretCacheConfig(exception_retry_delay_base=1, exception_retry_growth_factor=2),
            None, None
        )
        sco._set_result = Mock(side_effect=Exception("exception used for test"))
        sco._refresh_needed = True
        sco._exception_count = exp_factor  # delay = min(1*(2^exp_factor) = 2048, 3600)

        t_before = datetime.now(tz=timezone.utc)
        sco._SecretCacheObject__refresh()
        t_after = datetime.now(tz=timezone.utc)

        t_before_delay = t_before + timedelta(
            milliseconds=sco._config.exception_retry_delay_base * (
                    sco._config.exception_retry_growth_factor ** exp_factor
            )
        )
        self.assertLessEqual(t_before_delay, sco._next_retry_time)

        t_after_delay = t_after + timedelta(
            milliseconds=sco._config.exception_retry_delay_base * (
                    sco._config.exception_retry_growth_factor ** exp_factor
            )
        )
        self.assertGreaterEqual(t_after_delay, sco._next_retry_time)
class TestSecretCacheItem(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_datetime_fix_SCI_init(self):
        config = SecretCacheConfig()
        t_before = datetime.now(tz=timezone.utc)
        sci = SecretCacheItem(config, None, None)
        t_after = datetime.now(tz=timezone.utc)

        self.assertGreaterEqual(sci._next_refresh_time, t_before)
        self.assertLessEqual(sci._next_refresh_time, t_after)
    def test_datetime_fix_refresh_needed(self):
        config = SecretCacheConfig()
        sci = SecretCacheItem(config, None, None)

        # Used to pass branching requirements (False is not None)
        sci._refresh_needed = False
        sci._exception = False
        sci._next_retry_time = None

        self.assertTrue(sci._is_refresh_needed())

    def test_datetime_fix_execute_refresh(self):
        client_mock = Mock()
        client_mock.describe_secret = Mock()
        client_mock.describe_secret.return_value = "test"

        config = SecretCacheConfig()
        sci = SecretCacheItem(config, client_mock, None)

        t_before = datetime.now(tz=timezone.utc)
        sci._execute_refresh()
        t_after = datetime.now(tz=timezone.utc)

        # Make sure that the timezone is correctly set
        self.assertEqual(sci._next_refresh_time.tzinfo, timezone.utc)

        # Check that secret_refresh_interval addition works as intended
        self.assertGreaterEqual(sci._next_refresh_time, t_before)
        t_max_after = t_after + timedelta(seconds=config.secret_refresh_interval)
        self.assertLessEqual(sci._next_refresh_time, t_max_after)
