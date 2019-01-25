# Encoding: utf-8

# --
# Copyright (c) 2008-2019 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
# --

from webob import exc
from nagare.services import base_exceptions_handler


def default_handler(exception, exceptions_service, **context):
    if not isinstance(exception, exc.HTTPException):
        exceptions_service.log_exception()
        exception = exc.HTTPInternalServerError()

    return exception


class ExceptionService(base_exceptions_handler.Handler):
    LOAD_PRIORITY = base_exceptions_handler.Handler.LOAD_PRIORITY + 2
    CONFIG_SPEC = dict(
        base_exceptions_handler.Handler.CONFIG_SPEC,
        handler='string(default="nagare.services.http_exceptions:default_handler")'
    )
