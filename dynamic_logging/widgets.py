# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import json
import logging
import random

from django.conf import settings
from django.forms.widgets import Widget, Textarea
from django.utils.encoding import force_text
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from dynamic_logging.models import Config

logger = logging.getLogger(__name__)


class JsonLoggerWidget(Textarea):
    class Media:
        js = (
            'admin/js/minimal.js',
            # 'admin/js/jquery-2.2.4.min.js',
            # 'admin/js/select2.min.js',
            # 'admin/js/jquerymy-1.2.8.js',
            'admin/js/logging_widget.js',
        )

    def render(self, name, value, attrs=None):
        attrs = attrs or {}
        attrs['style'] = attrs.get('style', '') + ' display: none;'
        res = super(JsonLoggerWidget, self).render(name, value, attrs)

        return res + format_html(
            '<div id="{anchorid}"></div>'
            '<script type="application/javascript">'
            '(function ($) {{$(function() {{logging_widget($("#{anchorid}"), $("#{areaid}"), {handlers});}});}}(jQuery));'
            '</script>',
            anchorid=attrs.get('id', name) + '_display',
            areaid=attrs.get('id', name),
            handlers=mark_safe(json.dumps(list(Config.get_all_handlers().keys())))
        )
