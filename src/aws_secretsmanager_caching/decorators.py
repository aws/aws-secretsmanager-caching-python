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
"""Decorators for use with caching library"""

import json
from functools import wraps


class InjectSecretString:
    """Decorator implementing high-level Secrets Manager caching client"""

    def __init__(self, secret_id, cache):
        """
        Constructs a decorator to inject a single non-keyworded argument from a cached secret for a given function.

        :type secret_id: str
        :param secret_id: The secret identifier

        :type cache: aws_secretsmanager_caching.SecretCache
        :param cache: Secret cache
        """

        self.cache = cache
        self.secret_id = secret_id

    def __call__(self, func):
        """
        Return a function with cached secret injected as first argument.

        :type func: object
        :param func: The function for injecting a single non-keyworded argument too.
        :return The function with the injected argument.
        """

        # Using functools.wraps preserves the metadata of the wrapped function
        @wraps(func)
        def _wrapped_func(*args, **kwargs):
            """
            Internal function to execute wrapped function
            """
            secret = self.cache.get_secret_string(secret_id=self.secret_id)

            # Prevent clobbering self arg in class methods
            if args and hasattr(args[0].__class__, func.__name__):
                new_args = (args[0], secret) + args[1:]
            else:
                new_args = (secret,) + args

            return func(*new_args, **kwargs)

        return _wrapped_func


class InjectKeywordedSecretString:
    """Decorator implementing high-level Secrets Manager caching client using JSON-based secrets"""

    def __init__(self, secret_id, cache, **kwargs):
        """
        Construct a decorator to inject a variable list of keyword arguments to a given function with resolved values
        from a cached secret.

        :type kwargs: dict
        :param kwargs: dictionary mapping original keyword argument of wrapped function to JSON-encoded secret key

        :type secret_id: str
        :param secret_id: The secret identifier

        :type cache: aws_secretsmanager_caching.SecretCache
        :param cache: Secret cache
        """

        self.cache = cache
        self.kwarg_map = kwargs
        self.secret_id = secret_id

    def __call__(self, func):
        """
        Return a function with injected keyword arguments from a cached secret.

        :type func: object
        :param func: function for injecting keyword arguments.
        :return The original function with injected keyword arguments
        """

        @wraps(func)
        def _wrapped_func(*args, **kwargs):
            """
            Internal function to execute wrapped function
            """
            try:
                secret = json.loads(
                    self.cache.get_secret_string(secret_id=self.secret_id)
                )
            except json.decoder.JSONDecodeError:
                raise RuntimeError("Cached secret is not valid JSON") from None

            resolved_kwargs = {}
            for orig_kwarg, secret_key in self.kwarg_map.items():
                try:
                    resolved_kwargs[orig_kwarg] = secret[secret_key]
                except KeyError:
                    raise RuntimeError(
                        f"Cached secret does not contain key {secret_key}"
                    ) from None

            return func(*args, **resolved_kwargs, **kwargs)

        return _wrapped_func
