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
import inspect
import logging
import time
from datetime import datetime, timedelta
from uuid import uuid4

import botocore
import botocore.session
import pytest
from botocore.exceptions import ClientError, HTTPClientError, NoCredentialsError

from aws_secretsmanager_caching.config import SecretCacheConfig
from aws_secretsmanager_caching.secret_cache import SecretCache

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TestAwsSecretsManagerCachingInteg:
    fixture_prefix = 'python_caching_integ_test_'
    uuid_suffix = uuid4().hex

    @pytest.fixture(scope='module')
    def client(self):
        yield botocore.session.get_session().create_client('secretsmanager')

    @pytest.fixture(scope='module', autouse=True)
    def pre_test_cleanup(self, client):
        logger.info('Starting cleanup operation of previous test secrets...')
        old_secrets = []
        two_days_ago = datetime.now() - timedelta(days=2)

        paginator = client.get_paginator('list_secrets')
        paginator_config = {'PageSize': 10, 'StartingToken': None}
        iterator = paginator.paginate(PaginationConfig=paginator_config)
        try:
            for page in iterator:
                logger.info('Fetching results from ListSecretValue...')
                for secret in page['SecretList']:
                    if secret['Name'].startswith(TestAwsSecretsManagerCachingInteg.fixture_prefix) and \
                            (secret['LastChangedDate'] > two_days_ago) and (secret['LastAccessedDate'] > two_days_ago):
                        old_secrets.append(secret)
                try:
                    paginator_config['StartingToken'] = page['NextToken']
                except KeyError:
                    logger.info('reached end of list')
                    break
                time.sleep(0.5)
        except ClientError as e:
            logger.error("Got ClientError {0} while calling ListSecrets".format(e.response['Error']['Code']))
        except HTTPClientError:
            logger.error("Got HTTPClientError while calling ListSecrets")
        except NoCredentialsError:
            logger.fatal("Got NoCredentialsError while calling ListSecrets.")
            raise

        if len(old_secrets) == 0:
            logger.info("No previously configured test secrets found")

        for secret in old_secrets:
            logger.info("Scheduling deletion of secret {}".format(secret['Name']))
            try:
                client.delete_secret(SecretId=secret['Name'])
            except ClientError as e:
                logger.error("Got ClientError {0} while calling "
                             "DeleteSecret for secret {1}".format(e.response['Error']['Code'], secret['Name']))
            except HTTPClientError:
                logger.error("Got HTTPClientError while calling DeleteSecret for secret {0}".format(secret['Name']))
            time.sleep(0.5)

        yield None

    @pytest.fixture
    def secret_string(self, request, client):
        name = "{0}{1}{2}".format(TestAwsSecretsManagerCachingInteg.fixture_prefix, request.function.__name__,
                                  TestAwsSecretsManagerCachingInteg.uuid_suffix)

        secret = client.create_secret(Name=name, SecretString='test')
        yield secret
        client.delete_secret(SecretId=secret['ARN'], ForceDeleteWithoutRecovery=True)

    def test_get_secret_string(self, client, secret_string):
        cache = SecretCache(client=client)
        secret = client.get_secret_value(SecretId=secret_string['ARN'])['SecretString']

        for _ in range(10):
            assert cache.get_secret_string("{0}{1}{2}".format(TestAwsSecretsManagerCachingInteg.fixture_prefix,
                                                              inspect.stack()[0][3],
                                                              TestAwsSecretsManagerCachingInteg.uuid_suffix)) == secret

    def test_get_secret_string_refresh(self, client, secret_string):
        cache = SecretCache(config=SecretCacheConfig(secret_refresh_interval=1),
                            client=client)
        secret = client.get_secret_value(SecretId=secret_string['ARN'])['SecretString']

        for _ in range(10):
            assert cache.get_secret_string("{0}{1}{2}".format(TestAwsSecretsManagerCachingInteg.fixture_prefix,
                                                              inspect.stack()[0][3],
                                                              TestAwsSecretsManagerCachingInteg.uuid_suffix)) == secret

        client.put_secret_value(SecretId=secret_string['ARN'],
                                SecretString='test2', VersionStages=['AWSCURRENT'])

        time.sleep(2)
        secret = client.get_secret_value(SecretId=secret_string['ARN'])['SecretString']
        for _ in range(10):
            assert cache.get_secret_string("{0}{1}{2}".format(TestAwsSecretsManagerCachingInteg.fixture_prefix,
                                                              inspect.stack()[0][3],
                                                              TestAwsSecretsManagerCachingInteg.uuid_suffix)) == secret

    def test_get_secret_binary_empty(self, client, secret_string):
        cache = SecretCache(client=client)
        assert cache.get_secret_binary("{0}{1}{2}".format(TestAwsSecretsManagerCachingInteg.fixture_prefix,
                                                          inspect.stack()[0][3],
                                                          TestAwsSecretsManagerCachingInteg.uuid_suffix)) is None

    @pytest.fixture
    def secret_string_stage(self, request, client):
        name = "{0}{1}{2}".format(TestAwsSecretsManagerCachingInteg.fixture_prefix, request.function.__name__,
                                  TestAwsSecretsManagerCachingInteg.uuid_suffix)

        secret = client.create_secret(Name=name, SecretString='test')
        client.put_secret_value(SecretId=secret['ARN'], SecretString='test2',
                                VersionStages=['AWSCURRENT'])

        yield client.describe_secret(SecretId=secret['ARN'])
        client.delete_secret(SecretId=secret['ARN'], ForceDeleteWithoutRecovery=True)

    def test_get_secret_string_stage(self, client, secret_string_stage):
        cache = SecretCache(client=client)
        secret = client.get_secret_value(SecretId=secret_string_stage['ARN'],
                                         VersionStage='AWSPREVIOUS')['SecretString']

        for _ in range(10):
            assert cache.get_secret_string("{0}{1}{2}".format(TestAwsSecretsManagerCachingInteg.fixture_prefix,
                                                              inspect.stack()[0][3],
                                                              TestAwsSecretsManagerCachingInteg.uuid_suffix),
                                           'AWSPREVIOUS') == secret

    @pytest.fixture
    def secret_binary(self, request, client):
        name = "{0}{1}{2}".format(TestAwsSecretsManagerCachingInteg.fixture_prefix, request.function.__name__,
                                  TestAwsSecretsManagerCachingInteg.uuid_suffix)

        secret = client.create_secret(Name=name, SecretBinary=b'01010101')
        yield secret
        client.delete_secret(SecretId=secret['ARN'], ForceDeleteWithoutRecovery=True)

    def test_get_secret_binary(self, client, secret_binary):
        cache = SecretCache(client=client)
        secret = client.get_secret_value(SecretId=secret_binary['ARN'])['SecretBinary']

        for _ in range(10):
            assert cache.get_secret_binary("{0}{1}{2}".format(TestAwsSecretsManagerCachingInteg.fixture_prefix,
                                                              inspect.stack()[0][3],
                                                              TestAwsSecretsManagerCachingInteg.uuid_suffix)) == secret

    def test_get_secret_string_empty(self, client, secret_binary):
        cache = SecretCache(client=client)
        assert cache.get_secret_string("{0}{1}{2}".format(TestAwsSecretsManagerCachingInteg.fixture_prefix,
                                                          inspect.stack()[0][3],
                                                          TestAwsSecretsManagerCachingInteg.uuid_suffix)) is None
