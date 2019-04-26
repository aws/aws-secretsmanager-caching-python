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

from aws_secretsmanager_caching.cache.items import SecretCacheObject
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
