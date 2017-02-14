# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import logging
from logging import Filter

logger = logging.getLogger(__name__)


class PoliteFilter(Filter):

    def filter(self, record):
        return record.msg.startswith('hello')
