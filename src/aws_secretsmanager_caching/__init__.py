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
"""High level AWS Secrets Manager caching client."""

from aws_secretsmanager_caching.config import SecretCacheConfig
from aws_secretsmanager_caching.decorators import (
    InjectKeywordedSecretString,
    InjectSecretString,
)
from aws_secretsmanager_caching.secret_cache import SecretCache

__all__ = [
    "SecretCache",
    "SecretCacheConfig",
    "InjectSecretString",
    "InjectKeywordedSecretString",
]
