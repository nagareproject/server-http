# --
# Copyright (c) 2008-2018 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
# --

from functools import partial

from webob import exc
from ws4py.server.wsgiutils import WebSocketWSGIApplication

from nagare.server import publisher


class Publisher(publisher.Publisher):

    def _create_app(self, services_service):
        app = services_service(self.create_app)
        return partial(self.start_handle_request, app)

    def create_websocket(self, environ):
        raise NotImplementedError()

    def start_handle_request(self, app, environ, start_response):
        websocket = self.create_websocket(environ)
        environ.pop('set_websocket')(websocket, environ)

        request = app.create_request(environ)

        try:
            request.params, request.url
        except UnicodeDecodeError:
            response = exc.HTTPClientError()
        else:
            try:
                if websocket is not None:
                    def start_response(status, headers, sr=start_response):
                        sr(status, headers + [('Content-length', '0')])

                response = super(Publisher, self).start_handle_request(
                    app,
                    request=request,
                    start_response=start_response,
                    response=app.create_response(request),
                    websocket=websocket
                )

                if websocket is not None:
                    environ['ws4py.socket'] = None
                    response = WebSocketWSGIApplication(['binary'])
            except exc.HTTPException as e:
                response = e
            except Exception:
                self.logger.critical('Unhandled exception', exc_info=True)
                response = exc.HTTPInternalServerError()

        return response(environ, start_response)
