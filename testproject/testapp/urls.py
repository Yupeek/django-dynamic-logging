# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django.conf.urls import url, include

from . import views
import debug_toolbar

urlpatterns = [
    url(r'^error401/$', views.error401),
    url(r'^error500/$', views.raise_view),
    url(r'^ok/$', views.page_200),
    url(r'^log/(?P<level>\w+)/((?P<loggername>[a-z.]+)/)?$', views.log_somthing),
    url(r'^__debug__/', include(debug_toolbar.urls)),
]
