# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import logging
import threading
from collections import defaultdict
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class MockHandler(logging.Handler):
    """Mock logging handler to check for expected logs."""

    _messages_by_thread = defaultdict(list)

    @classmethod
    @contextmanager
    def capture(cls):
        current = defaultdict(list)
        cls._messages_by_thread[threading.current_thread()].append(current)
        try:
            yield current
        finally:
            cls._messages_by_thread[threading.current_thread()].remove(current)

    def emit(self, record):
        for messages_list in self._messages_by_thread[threading.current_thread()]:
            messages_list[record.levelname.lower()].append(record.getMessage())
