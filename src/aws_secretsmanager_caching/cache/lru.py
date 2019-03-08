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
"""LRU cache"""

import threading


class LRUCache:
    """Least recently used cache"""

    def __init__(self, max_size=1024):
        """Construct a new instance of the LRU cache

        :type max_size: int
        :param max_size: The maximum number of elements to store in the cache
        """
        self._lock = threading.RLock()
        self._cache = {}
        self._head = None
        self._tail = None
        self._max_size = max_size
        self._size = 0

    def get(self, key):
        """Get the cached item for the given key

        :type key: object
        :param key: Key of the cached item

        :rtype: object
        :return: The cached item associated with the key
        """
        with self._lock:
            if key not in self._cache:
                return None
            item = self._cache[key]
            self._update_head(item)
            return item.data

    def put_if_absent(self, key, data):
        """Associate the given item with the key if the key is not already associated with an item.

        :type key: object
        :param key: The key for the item to cache.

        :type data: object
        :param data: The item to cache if the key is not already in use.

        :rtype: bool
        :return: True if the given data was mapped to the given key.
        """
        with self._lock:
            if key in self._cache:
                return False
            item = LRUItem(key=key, data=data)
            self._cache[key] = item
            self._size += 1
            self._update_head(item)
            if self._size > self._max_size:
                del self._cache[self._tail.key]
                self._unlink(self._tail)
                self._size -= 1
            return True

    def _update_head(self, item):
        """Update the head item in the list to be the given item.

        :type item: object
        :param item: The item that should be updated as the head item.

        :rtype: None
        :return: None
        """
        if item is self._head:
            return
        self._unlink(item)
        item.next = self._head
        if self._head is not None:
            self._head.prev = item
        self._head = item
        if self._tail is None:
            self._tail = item

    def _unlink(self, item):
        """Unlink the given item from the linked list.

        :type item: object
        :param item: The item to unlink from the linked list.

        :rtype: None
        :return: None
        """
        if item is self._head:
            self._head = item.next
        if item is self._tail:
            self._tail = item.prev
        if item.prev is not None:
            item.prev.next = item.next
        if item.next is not None:
            item.next.prev = item.prev
        item.next = None
        item.prev = None


class LRUItem:
    """An item for use in the LRU cache."""

    def __init__(self, key, data=None, prev=None, nxt=None):
        """Construct an item for use within the LRU cache.

        :type key: object
        :param key: The key associated with the item.

        :type data: object
        :param data: The associated data for the key/item.

        :type prev: LRUItem
        :param prev: The previous item in the linked list.

        :type nxt: LRUItem
        :param nxt: The next item in the linked list.
        """
        self.key = key
        self.next = nxt
        self.prev = prev
        self.data = data
