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
"""Decorators for use with caching library """
import json

from abc import ABC

import botocore.exceptions


class InjectSecretAbstract(ABC):
    """High-level abstraction for Secrets Manager decorators."""

    def __init__(self, secret_id, cache, caches=None):
        """
        Constructs a decorator to inject a single non-keyworded argument from a cached secret for a given function.

        :type secret_id: str
        :param secret_id: The secret identifier

        :type cache: aws_secretsmanager_caching.SecretCache
        :param cache: Secret cache

        :type cache: Optional[List[aws_secretsmanager_caching.SecretCache]]
        :param cache: Multiple additional secret caches for multiregion failover
        """

        self.cache_id = 0
        self.caches = [cache]
        if caches:
            self.caches.extend(caches)
        self.secret_id = secret_id

    def _get_cached_secret(self):
        """
        Return cached secret.

        :type cache: Union[Dict, str]
        :param cache: Plaintext secret value or object
        """

        n_caches = len(self.caches)
        # Probe each replica (including primary) starting with the current one
        replicas = [i % n_caches for i in range(self.cache_id, self.cache_id + n_caches)]
        for replica in replicas:
            try:
                secret = self.caches[replica].get_secret_string(secret_id=self.secret_id)
                self.cache_id = replica
                break
            except botocore.exceptions.ClientError as e:
                if e.response["Error"]["Code"] in {"InternalFailure", "ServiceUnavailable"}:
                    if replica == replicas[-1]:
                        # All possible replicas were probed
                        raise
                else:
                    raise
        return secret


class InjectSecretString(InjectSecretAbstract):
    """Decorator implementing high-level Secrets Manager caching client"""

    def __call__(self, func):
        """
        Return a function with cached secret injected as first argument.

        :type func: object
        :param func: The function for injecting a single non-keyworded argument too.
        :return The function with the injected argument.
        """
        secret = self._get_cached_secret()

        def _wrapped_func(*args, **kwargs):
            """
            Internal function to execute wrapped function
            """
            return func(secret, *args, **kwargs)

        return _wrapped_func


class InjectKeywordedSecretString(InjectSecretAbstract):
    """Decorator implementing high-level Secrets Manager caching client using JSON-based secrets"""

    def __init__(self, secret_id, cache, caches=None, **kwargs):
        """
        Construct a decorator to inject a variable list of keyword arguments to a given function with resolved values
        from a cached secret.

        :type kwargs: dict
        :param kwargs: dictionary mapping original keyword argument of wrapped function to JSON-encoded secret key

        :type secret_id: str
        :param secret_id: The secret identifier

        :type cache: aws_secretsmanager_caching.SecretCache
        :param cache: Secret cache

        :type cache: Optional[List[aws_secretsmanager_caching.SecretCache]]
        :param cache: Multiple secret caches for multiregion failover
        """

        super().__init__(secret_id, cache, caches)
        self.kwarg_map = kwargs

    def __call__(self, func):
        """
        Return a function with injected keyword arguments from a cached secret.

        :type func: object
        :param func: function for injecting keyword arguments.
        :return The original function with injected keyword arguments
        """

        try:
            secret = self._get_cached_secret()
            secret = json.loads(secret)
        except json.decoder.JSONDecodeError:
            raise RuntimeError('Cached secret is not valid JSON') from None

        resolved_kwargs = {}
        for orig_kwarg, secret_key in self.kwarg_map.items():
            try:
                resolved_kwargs[orig_kwarg] = secret[secret_key]
            except KeyError:
                raise RuntimeError(f'Cached secret does not contain key {secret_key}') from None

        def _wrapped_func(*args, **kwargs):
            """
            Internal function to execute wrapped function
            """
            return func(*args, **resolved_kwargs, **kwargs)

        return _wrapped_func
