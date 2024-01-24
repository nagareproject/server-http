# Encoding: utf-8

# --
# Copyright (c) 2008-2024 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
# --

from os import path

from webob import exc

from nagare.server import reference
from nagare.services import base_exceptions_handler


def default_exception_handler(exception, exceptions_service, services_service, **context):
    if isinstance(exception, exc.HTTPOk):
        return exception

    if not isinstance(exception, exc.WSGIHTTPException):
        exceptions_service.log_exception()
        exception = exc.HTTPInternalServerError()

    exception = services_service(exceptions_service.handle_exception, exception, **context)

    if getattr(exception, 'commit_transaction', False):
        return exception
    else:
        raise exception


def default_http_exception_handler(http_exception, exceptions_service, **context):
    if http_exception.status_code // 100 in (4, 5):
        http_exception = exceptions_service.default_http_exception_handler(http_exception, **context)

    return http_exception


class ExceptionsService(base_exceptions_handler.ExceptionsService):
    LOAD_PRIORITY = base_exceptions_handler.ExceptionsService.LOAD_PRIORITY + 2
    CONFIG_SPEC = dict(
        base_exceptions_handler.ExceptionsService.CONFIG_SPEC,
        exception_handler='string(default="nagare.services.http_exceptions:default_exception_handler")',
        http_exception_handler='string(default="nagare.services.http_exceptions:default_http_exception_handler")',
    )

    def __init__(self, name, dist, http_exception_handler, services_service, **config):
        services_service(
            super(ExceptionsService, self).__init__, name, dist, http_exception_handler=http_exception_handler, **config
        )

        self.add_exception_handler(reference.load_object(http_exception_handler)[0])

    @staticmethod
    def default_http_exception_handler(http_exception, app, **context):
        if app.data_path:
            status = str(http_exception.status_code)

            for filename in [status, status[:-1] + 'x', status[:-2] + 'xx', 'xxx', 'default']:
                fullname = path.join(app.data_path, 'http_errors', filename)
                if path.isfile(fullname):
                    with open(fullname) as f:
                        http_exception.text = f.read()
                    break

        return http_exception
