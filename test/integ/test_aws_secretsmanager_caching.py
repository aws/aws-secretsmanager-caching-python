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
import os
from botocore.credentials import (
    AssumeRoleCredentialFetcher,
    CredentialResolver,
    DeferredRefreshableCredentials,
    JSONFileCache
)
from botocore.session import Session
from aws_secretsmanager_caching.config import SecretCacheConfig
from aws_secretsmanager_caching.secret_cache import SecretCache


class AssumeRoleProvider(object):
    METHOD = 'assume-role'

    def __init__(self, fetcher):
        self._fetcher = fetcher

    def load(self):
        return DeferredRefreshableCredentials(
            self._fetcher.fetch_credentials,
            self.METHOD
        )


def assume_role(session: Session, role_arn: str, duration: int = 3600,
                session_name: str = None, serial_number: str = None) -> Session:

    fetcher = AssumeRoleCredentialFetcher(session.create_client,
                                          session.get_credentials(),
                                          role_arn,
                                          extra_args={
                                            'DurationSeconds': duration,
                                            'RoleSessionName': session_name,
                                            'SerialNumber': serial_number
                                          },
                                          cache=JSONFileCache())
    role_session = Session()
    role_session.register_component(
        'credential_provider',
        CredentialResolver([AssumeRoleProvider(fetcher)])
    )
    return role_session


class TestAwsSecretsManagerCachingInteg:

    @pytest.fixture(scope='module')
    def client(self):
        region = os.getenv('AWS_REGION', 'us-west-2')
        base_session = botocore.session.get_session()
        if os.environ.get('IAM_ROLE_ARN') is not None:
            role_session = assume_role(base_session, role_arn=os.environ.get('IAM_ROLE_ARN'))
            yield role_session.create_client('secretsmanager', region_name=region)
        else:
            yield base_session.create_client('secretsmanager', region_name=region)

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
