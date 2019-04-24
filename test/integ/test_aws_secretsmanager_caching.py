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
import pytest
import botocore
import botocore.session
from aws_secretsmanager_caching.config import SecretCacheConfig
from aws_secretsmanager_caching.secret_cache import SecretCache


class TestAwsSecretsManagerCachingInteg:

    @pytest.fixture(scope='module')
    def client(self):
        session = botocore.session.get_session()
        yield session.create_client('secretsmanager', region_name='us-west-2')

    @pytest.fixture(scope='module')
    def secret_string(self, client):
        secret = client.create_secret(Name='secret_string',
                                      SecretString='test')
        yield secret
        client.delete_secret(SecretId=secret['ARN'], ForceDeleteWithoutRecovery=True)

    @pytest.fixture(scope='module')
    def secret_binary(self, client):
        secret = client.create_secret(Name='secret_binary',
                                      SecretBinary=b'01010101')
        yield secret
        client.delete_secret(SecretId=secret['ARN'], ForceDeleteWithoutRecovery=True)

    def test_get_secret_string(self, client, secret_string):
        cache = SecretCache(client=client)
        secret = client.get_secret_value(SecretId=secret_string['ARN'])['SecretString']

        for _ in range(10):
            assert cache.get_secret_string('secret_string') == secret

    def test_get_secret_string_empty(self, client, secret_binary):
        cache = SecretCache(client=client)
        assert cache.get_secret_string('secret_binary') is None

    def test_get_secret_string_stage(self, client, secret_string):
        cache = SecretCache(client=client)
        secret = client.get_secret_value(SecretId=secret_string['ARN'])['SecretString']

        for _ in range(10):
            assert cache.get_secret_string('secret_string', 'AWSCURRENT') == secret

    def test_get_secret_string_refresh(self, client, secret_string):
        cache = SecretCache(config=SecretCacheConfig(secret_refresh_interval=1),
                            client=client)
        secret = client.get_secret_value(SecretId=secret_string['ARN'])['SecretString']

        for _ in range(10):
            assert cache.get_secret_string('secret_string') == secret

    def test_get_secret_binary(self, client, secret_binary):
        cache = SecretCache(client=client)
        secret = client.get_secret_value(SecretId=secret_binary['ARN'])['SecretBinary']

        for _ in range(10):
            assert cache.get_secret_binary('secret_binary') == secret

    def test_get_secret_binary_empty(self, client, secret_string):
        cache = SecretCache(client=client)
        assert cache.get_secret_binary('secret_string') is None
