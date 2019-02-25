# --
# Copyright (c) 2008-2019 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
# --

from webob import exc
from ws4py.server.wsgiutils import WebSocketWSGIApplication

from nagare.server import publisher


class Publisher(publisher.Publisher):
    CONFIG_SPEC = dict(
        publisher.Publisher.CONFIG_SPEC,
        _app_url='string(default=$app_url)'
    )

    def __init__(self, name, dist, _app_url, **config):
        super(Publisher, self).__init__(name, dist, **config)
        self.url = _app_url or self.app_name

    def generate_banner(self):
        url = self.endpoint[1] + '/' + self.url
        return super(Publisher, self).generate_banner() + ' on ' + url

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
