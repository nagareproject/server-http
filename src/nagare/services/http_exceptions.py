# --
# Copyright (c) 2008-2025 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
# --

from os import path

from webob import exc

from nagare.services import base_exceptions_handler


def exception_handler(exception, exceptions_service, **context):
    if not isinstance(exception, exc.WSGIHTTPException):
        exceptions_service.log_exception()
        exception = exc.HTTPInternalServerError()

    return exception


def http_exception_handler(http_exception, exceptions_service, **context):
    return (
        exceptions_service.http_exception_handler(http_exception, **context)
        if http_exception.status_code // 100 in (4, 5)
        else http_exception
    )


class ExceptionsService(base_exceptions_handler.ExceptionsService):
    LOAD_PRIORITY = base_exceptions_handler.ExceptionsService.LOAD_PRIORITY + 2
    CONFIG_SPEC = dict(
        base_exceptions_handler.ExceptionsService.CONFIG_SPEC,
        exception_handlers="""string_list(default=list(
            'nagare.services.http_exceptions:exception_handler',
            'nagare.services.http_exceptions:http_exception_handler'
        ))""",
        commit_exceptions="string_list(default=list('webob.exc:HTTPOk'))",
        http_errors_path='string(default="$data/http_errors")',
    )

    def __init__(self, name, dist, services_service, http_errors_path, **config):
        services_service(super().__init__, name, dist, http_errors_path=http_errors_path, **config)
        self.http_errors_path = http_errors_path.replace('/', path.sep)

    def http_exception_handler(self, http_exception, app, **context):
        status = str(http_exception.status_code)

        for filename in [status, status[:-1] + 'x', status[:-2] + 'xx', 'xxx', 'default']:
            fullname = path.join(self.http_errors_path, filename)
            if path.isfile(fullname):
                with open(fullname) as f:
                    http_exception.text = f.read()
                break

        return http_exception
