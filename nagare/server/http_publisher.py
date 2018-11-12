# --
# Copyright (c) 2008-2018 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
# --

from webob import exc
from nagare.server import publisher


class Publisher(publisher.Publisher):

    def start_handle_request(self, app, environ, start_response):
        request = app.create_request(environ)

        try:
            request.params, request.url
        except UnicodeDecodeError:
            response = exc.HTTPClientError()
        else:
            try:
                response = super(Publisher, self).start_handle_request(
                    app,
                    request=request,
                    start_response=start_response,
                    response=app.create_response(request)
                )
            except exc.HTTPException as e:
                response = e
            except Exception:
                self.logger.critical('Unhandled exception', exc_info=True)
                response = exc.HTTPInternalServerError()

        return response(environ, start_response)
