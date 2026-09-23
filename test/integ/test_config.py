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

import time
from uuid import uuid4

import botocore
import botocore.session
import pytest
from aws_secretsmanager_caching.config import SecretCacheConfig
from aws_secretsmanager_caching.secret_cache import SecretCache


class TestConfigInteg:
    fixture_prefix = 'python_config_integ_test_'
    uuid_suffix = uuid4().hex

    @pytest.fixture(scope='module')
    def client(self):
        yield botocore.session.get_session().create_client('secretsmanager', region_name='us-east-1')

    @pytest.fixture
    def secret_with_versions(self, request, client):
        name = f"{self.fixture_prefix}{request.function.__name__}{self.uuid_suffix}"

        # Create secret with initial version
        secret = client.create_secret(Name=name, SecretString='version1')

        # Add a new version
        client.put_secret_value(
            SecretId=secret['ARN'],
            SecretString='version2',
            VersionStages=['AWSCURRENT']
        )

        yield secret
        client.delete_secret(SecretId=secret['ARN'], ForceDeleteWithoutRecovery=True)

    def test_custom_version_stage(self, client, secret_with_versions):
        config = SecretCacheConfig(default_version_stage='AWSPREVIOUS')
        cache = SecretCache(config=config, client=client)

        result = cache.get_secret_string(secret_with_versions['Name'])
        assert result == 'version1'  # Should get the previous version

    def test_fast_refresh_interval(self, client, secret_with_versions):
        config = SecretCacheConfig(secret_refresh_interval=1)  # 1 second refresh
        cache = SecretCache(config=config, client=client)

        # Get initial value
        result1 = cache.get_secret_string(secret_with_versions['Name'])
        assert result1 == 'version2'

        # Update secret
        client.put_secret_value(
            SecretId=secret_with_versions['ARN'],
            SecretString='version3',
            VersionStages=['AWSCURRENT']
        )

        # Wait for refresh interval
        time.sleep(2)

        # Should get updated value
        result2 = cache.get_secret_string(secret_with_versions['Name'])
        assert result2 == 'version3'

    def test_max_cache_size(self, client):
        config = SecretCacheConfig(max_cache_size=2)
        cache = SecretCache(config=config, client=client)

        # Create multiple secrets to test cache eviction
        secrets = []
        for i in range(3):
            name = f"{self.fixture_prefix}cache_size_{i}_{self.uuid_suffix}"
            secret = client.create_secret(Name=name, SecretString=f'value{i}')
            secrets.append(secret)

        try:
            # Access secrets to fill cache beyond limit
            for i, secret in enumerate(secrets):
                result = cache.get_secret_string(secret['Name'])
                assert result == f'value{i}'

            # Cache should still work despite size limit
            result = cache.get_secret_string(secrets[0]['Name'])
            assert result == 'value0'

        finally:
            # Cleanup
            for secret in secrets:
                client.delete_secret(SecretId=secret['ARN'], ForceDeleteWithoutRecovery=True)
