# -*- coding: utf-8 -*-
from __future__ import absolute_import

import debug_toolbar
from django.conf.urls import include, url

from . import views

urlpatterns = [
    url(r'^error401/$', views.error401),
    url(r'^error500/$', views.raise_view),
    url(r'^ok/$', views.page_200),
    url(r'^log/(?P<level>\w+)/((?P<loggername>[a-z.]+)/)?$', views.log_somthing),
    url(r'^__debug__/', include(debug_toolbar.urls)),
]
