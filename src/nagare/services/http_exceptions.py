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
    )

    @staticmethod
    def http_exception_handler(http_exception, app, **context):
        if app.data_path:
            status = str(http_exception.status_code)

            for filename in [status, status[:-1] + 'x', status[:-2] + 'xx', 'xxx', 'default']:
                fullname = path.join(app.data_path, 'http_errors', filename)
                if path.isfile(fullname):
                    with open(fullname) as f:
                        http_exception.text = f.read()
                    break

        return http_exception
