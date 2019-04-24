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
"""Secret cache hook"""

from abc import ABCMeta, abstractmethod


class SecretCacheHook:  # pylint: disable=too-many-instance-attributes
    """Interface to hook the local in-memory cache.  This interface will allow
    for clients to perform actions on the items being stored in the in-memory
    cache.  One example would be encrypting/decrypting items stored in the
    in-memory cache."""

    __metaclass__ = ABCMeta

    def __init__(self):
        """Construct the secret cache hook."""

    @abstractmethod
    def put(self, obj):
        """Prepare the object for storing in the cache"""

    @abstractmethod
    def get(self, cached_obj):
        """Derive the object from the cached object."""
