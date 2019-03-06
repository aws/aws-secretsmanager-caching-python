# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
"""Secret cache configuration object."""

from copy import deepcopy
from datetime import timedelta


class SecretCacheConfig:

    """Advanced configuration for SecretCache clients.

    :type max_cache_size: int
    :param max_cache_size: The maximum number of secrets to cache.

    :type exception_retry_delay_base: int
    :param exception_retry_delay_base: The number of seconds to wait
        after an exception is encountered and before retrying the request.

    :type exception_retry_growth_factor: int
    :param exception_retry_growth_factor: The growth factor to use for
        calculating the wait time between retries of failed requests.

    :type exception_retry_delay_max: int
    :param exception_retry_delay_max: The maximum amount of time in
        seconds to wait between failed requests.

    :type default_version_stage: str
    :param default_version_stage: The default version stage to request.

    :type secret_refresh_interval: int
    :param secret_refresh_interval: The number of seconds to wait between
        refreshing cached secret information.

    """

    OPTION_DEFAULTS = {
        "max_cache_size": 1024,
        "exception_retry_delay_base": 1,
        "exception_retry_growth_factor": 2,
        "exception_retry_delay_max": 3600,
        "default_version_stage": "AWSCURRENT",
        "secret_refresh_interval": timedelta(hours=1).total_seconds(),
    }

    def __init__(self, **kwargs):
        options = deepcopy(self.OPTION_DEFAULTS)

        # Set config options based on given values
        if kwargs:
            for key, value in kwargs.items():
                if key in options:
                    options[key] = value
                # The key must exist in the available options
                else:
                    raise TypeError("Unexpected keyword argument '%s'" % key)

        # Set the attributes based on the config options
        for key, value in options.items():
            setattr(self, key, value)
