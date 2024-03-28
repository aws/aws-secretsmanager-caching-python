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

from aws_secretsmanager_caching.config import SecretCacheConfig


class TestSecretCacheConfig(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_simple_config(self):
        self.assertRaises(TypeError, SecretCacheConfig, no='one')

    def test_config_default_version_stage(self):
        stage = 'nothing'
        config = SecretCacheConfig(default_version_stage=stage)
        self.assertEqual(config.default_version_stage, stage)

    def test_default_secret_refresh_interval_typing(self):
        config = SecretCacheConfig()
        self.assertIsInstance(config.secret_refresh_interval, int)
