# --
# Copyright (c) 2008-2019 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
# --

import os
import webbrowser

from webob import exc
from ws4py.websocket import WebSocket
from ws4py.server.wsgiutils import WebSocketWSGIApplication

from nagare.server import publisher


class Publisher(publisher.Publisher):
    CONFIG_SPEC = dict(
        publisher.Publisher.CONFIG_SPEC,
        _app_url='string(default=$app_url)',
        open_on_start='boolean(default=True, help="open a browser tab on startup")'
    )
    websocket_app = WebSocketWSGIApplication
    websocket_handler = WebSocket

    def __init__(self, name, dist, _app_url, open_on_start, **config):
        super(Publisher, self).__init__(name, dist, **config)
        self.url = _app_url
        self.open_on_start = open_on_start

    @property
    def endpoint(self):
        return False, ''

    def launch_browser(self):
        is_url, endpoint = self.endpoint
        if self.open_on_start and is_url and (os.environ.get('nagare.reload', '1') == '1'):
            webbrowser.open(endpoint + '/' + self.url)

    def generate_banner(self):
        url = self.endpoint[1] + '/' + self.url
        return super(Publisher, self).generate_banner() + ' on ' + url

    def create_websocket(self, environ):
        raise NotImplementedError()

    def start_handle_request(self, app, environ, start_response):
        websocket = self.create_websocket(environ)
        if websocket is not None:
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
                    response = self.websocket_app(['binary'], handler_cls=self.websocket_handler)
            except exc.HTTPException as e:
                response = e
            except Exception:
                self.logger.critical('Unhandled exception', exc_info=True)
                response = exc.HTTPInternalServerError()

        return response(environ, start_response)

    def _serve(self, app, **params):
        self.launch_browser()

        super(Publisher, self)._serve(app, **params)
