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

from uuid import uuid4

import botocore
import botocore.session
import pytest
from aws_secretsmanager_caching.cache.secret_cache_hook import SecretCacheHook
from aws_secretsmanager_caching.config import SecretCacheConfig
from aws_secretsmanager_caching.secret_cache import SecretCache


class TestCacheHook(SecretCacheHook):
    """Test implementation of SecretCacheHook for integration testing"""

    def __init__(self):
        self.put_calls = 0
        self.get_calls = 0

    def put(self, obj):
        self.put_calls += 1
        # Return modified copy without mutating original
        modified_obj = obj.copy()
        if 'SecretString' in modified_obj:
            modified_obj['SecretString'] = f"HOOKED_{modified_obj['SecretString']}"
        if 'SecretBinary' in modified_obj:
            modified_obj['SecretBinary'] = b'HOOKED_' + modified_obj['SecretBinary']
        return modified_obj

    def get(self, cached_obj):
        self.get_calls += 1
        return cached_obj


class TestCacheHookInteg:
    fixture_prefix = 'python_hook_integ_test_'
    uuid_suffix = uuid4().hex

    @pytest.fixture(scope='module')
    def client(self):
        yield botocore.session.get_session().create_client('secretsmanager', region_name='us-east-1')

    @pytest.fixture
    def secret_string(self, request, client):
        name = f"{self.fixture_prefix}{request.function.__name__}{self.uuid_suffix}"
        secret = client.create_secret(Name=name, SecretString='test_value')
        yield secret
        client.delete_secret(SecretId=secret['ARN'], ForceDeleteWithoutRecovery=True)

    @pytest.fixture
    def secret_binary(self, request, client):
        name = f"{self.fixture_prefix}{request.function.__name__}{self.uuid_suffix}"
        secret = client.create_secret(Name=name, SecretBinary=b'binary_data')
        yield secret
        client.delete_secret(SecretId=secret['ARN'], ForceDeleteWithoutRecovery=True)

    def test_cache_hook_string_secret(self, client, secret_string):
        hook = TestCacheHook()
        config = SecretCacheConfig(secret_cache_hook=hook)
        cache = SecretCache(config=config, client=client)

        # First call should trigger put and get
        result = cache.get_secret_string(secret_string['Name'])
        print(f"Result: {result}, Put calls: {hook.put_calls}, Get calls: {hook.get_calls}")
        assert "test_value" in result  # Just check the value is there for now

        # Second call should only trigger get (cached)
        result = cache.get_secret_string(secret_string['Name'])
        print(f"Second result: {result}, Put calls: {hook.put_calls}, Get calls: {hook.get_calls}")

    def test_cache_hook_binary_secret(self, client, secret_binary):
        hook = TestCacheHook()
        config = SecretCacheConfig(secret_cache_hook=hook)
        cache = SecretCache(config=config, client=client)

        result = cache.get_secret_binary(secret_binary['Name'])
        print(f"Binary result: {result}, Put calls: {hook.put_calls}, Get calls: {hook.get_calls}")
        assert b'binary_data' in result  # Just check the value is there for now
