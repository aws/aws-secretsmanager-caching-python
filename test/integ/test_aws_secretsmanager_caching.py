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
import time
import inspect
from aws_secretsmanager_caching.config import SecretCacheConfig
from aws_secretsmanager_caching.secret_cache import SecretCache


class TestAwsSecretsManagerCachingInteg:
    fixture_prefix = 'python_caching_integ_test_'

    @pytest.fixture(scope='module')
    def client(self):
        yield botocore.session.get_session().create_client('secretsmanager')

    @pytest.fixture(scope='module', autouse=True)
    def pre_test_cleanup(self, client):
        old_secrets = []
        list_result = client.list_secrets()
        while True:
            for secret in list_result['SecretList']:
                if secret['Name'].startswith(TestAwsSecretsManagerCachingInteg.fixture_prefix):
                    old_secrets.append(secret)
            if 'NextToken' in list_result:
                next_token = list_result['NextToken']
                list_result = client.list_secrets(NextToken=next_token)
                time.sleep(0.5)
            else:
                break
        for secret in old_secrets:
            print("Scheduling deletion of secret {}".format(secret['Name']))
            client.delete_secret(SecretId=secret['Name'])
            time.sleep(0.5)

        yield None

    @pytest.fixture
    def secret_string(self, request, client):
        secret = client.create_secret(Name="{0}{1}".format(TestAwsSecretsManagerCachingInteg.fixture_prefix,
                                                           request.function.__name__),
                                      SecretString='test')
        yield secret
        client.delete_secret(SecretId=secret['ARN'], ForceDeleteWithoutRecovery=True)

    def test_get_secret_string(self, client, secret_string):
        cache = SecretCache(client=client)
        secret = client.get_secret_value(SecretId=secret_string['ARN'])['SecretString']

        for _ in range(10):
            assert cache.get_secret_string("{0}{1}".format(TestAwsSecretsManagerCachingInteg.fixture_prefix,
                                                           inspect.stack()[0][3])) == secret

    def test_get_secret_string_refresh(self, client, secret_string):
        cache = SecretCache(config=SecretCacheConfig(secret_refresh_interval=1),
                            client=client)
        secret = client.get_secret_value(SecretId=secret_string['ARN'])['SecretString']

        for _ in range(10):
            assert cache.get_secret_string("{0}{1}".format(TestAwsSecretsManagerCachingInteg.fixture_prefix,
                                                           inspect.stack()[0][3])) == secret

        client.put_secret_value(SecretId=secret_string['ARN'],
                                SecretString='test2', VersionStages=['AWSCURRENT'])

        time.sleep(2)
        secret = client.get_secret_value(SecretId=secret_string['ARN'])['SecretString']
        for _ in range(10):
            assert cache.get_secret_string("{0}{1}".format(TestAwsSecretsManagerCachingInteg.fixture_prefix,
                                                           inspect.stack()[0][3])) == secret

    def test_get_secret_binary_empty(self, client, secret_string):
        cache = SecretCache(client=client)
        assert cache.get_secret_binary("{0}{1}".format(TestAwsSecretsManagerCachingInteg.fixture_prefix,
                                                       inspect.stack()[0][3])) is None

    @pytest.fixture
    def secret_string_stage(self, request, client):
        secret = client.create_secret(Name="{0}{1}".format(TestAwsSecretsManagerCachingInteg.fixture_prefix,
                                                           request.function.__name__),
                                      SecretString='test')

        client.put_secret_value(SecretId=secret['ARN'], SecretString='test2',
                                VersionStages=['AWSCURRENT'])

        yield client.describe_secret(SecretId=secret['ARN'])
        client.delete_secret(SecretId=secret['ARN'], ForceDeleteWithoutRecovery=True)

    def test_get_secret_string_stage(self, client, secret_string_stage):
        cache = SecretCache(client=client)
        secret = client.get_secret_value(SecretId=secret_string_stage['ARN'],
                                         VersionStage='AWSPREVIOUS')['SecretString']

        for _ in range(10):
            assert cache.get_secret_string("{0}{1}".format(TestAwsSecretsManagerCachingInteg.fixture_prefix,
                                                           inspect.stack()[0][3]), 'AWSPREVIOUS') == secret

    @pytest.fixture
    def secret_binary(self, request, client):
        secret = client.create_secret(Name="{0}{1}".format(TestAwsSecretsManagerCachingInteg.fixture_prefix,
                                                           request.function.__name__),
                                      SecretBinary=b'01010101')
        yield secret
        client.delete_secret(SecretId=secret['ARN'], ForceDeleteWithoutRecovery=True)

    def test_get_secret_binary(self, client, secret_binary):
        cache = SecretCache(client=client)
        secret = client.get_secret_value(SecretId=secret_binary['ARN'])['SecretBinary']

        for _ in range(10):
            assert cache.get_secret_binary("{0}{1}".format(TestAwsSecretsManagerCachingInteg.fixture_prefix,
                                                           inspect.stack()[0][3])) == secret

    def test_get_secret_string_empty(self, client, secret_binary):
        cache = SecretCache(client=client)
        assert cache.get_secret_string("{0}{1}".format(TestAwsSecretsManagerCachingInteg.fixture_prefix,
                                                       inspect.stack()[0][3])) is None
