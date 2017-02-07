import logging

from django.http.response import HttpResponse


def error401(request):
    return HttpResponse(status=401)


def page_200(request):
    return HttpResponse('response ok', status=200)


def raise_view(request):
    raise Exception("oops error in raise_view")


def log_somthing(request, level='debug', loggername=__name__):
    level = level.upper()
    if level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
        raise Exception("error: level not valid")
    level = getattr(logging, level)
    logger = logging.getLogger(loggername)
    logger.log(level, "message from view", extra={'level': level, 'loggername': loggername})
    return HttpResponse("ok. logged to %s" % loggername)
