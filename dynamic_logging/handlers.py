# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class MockHandler(logging.Handler):
    """Mock logging handler to check for expected logs."""
    messages = defaultdict(list)

    def emit(self, record):
        self.messages[record.levelname.lower()].append(record.getMessage())
