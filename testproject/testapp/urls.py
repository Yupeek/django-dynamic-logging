# -*- coding: utf-8 -*-
from __future__ import absolute_import

import debug_toolbar
from django.urls import include, path, re_path

from . import views

urlpatterns = [
    path('error401/', views.error401),
    path('error500/', views.raise_view),
    path('ok/', views.page_200),
    re_path(r'^log/(?P<level>\w+)/((?P<loggername>[a-z.]+)/)?', views.log_somthing),
    path('__debug__/', include(debug_toolbar.urls)),
]
