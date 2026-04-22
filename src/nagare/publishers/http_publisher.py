# --
# Copyright (c) 2014-2026 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
# --

import os
import webbrowser

from webob import exc

from nagare.publishers import publisher


class Publisher(publisher.Publisher):
    CONFIG_SPEC = publisher.Publisher.CONFIG_SPEC | {
        '_app_url': 'string(default="$app_url")',
        'open_on_start': 'boolean(default=False, help="open a browser tab on startup")',
    }

    def __init__(self, name, dist, _app_url, open_on_start, **config):
        super().__init__(name, dist, open_on_start=open_on_start, **config)

        self.url = _app_url
        self.open_on_start = open_on_start

    @property
    def endpoint(self):
        return False, ''

    def launch_browser(self):
        is_url, _, _, endpoint = self.endpoint
        if self.open_on_start and is_url and (os.environ.get('nagare.reload', '1') == '1'):
            webbrowser.open(endpoint + self.url)

    def generate_banner(self):
        _, _, _, endpoint = self.endpoint
        url = endpoint + self.url
        return super().generate_banner() + ' on ' + url

    def start_handle_request(self, app, environ, start_response, services_service):
        request = app.create_request(environ)

        try:
            request.params, request.url
        except UnicodeDecodeError:
            response = exc.HTTPClientError()
        else:
            try:
                response = services_service(
                    super().start_handle_request,
                    app,
                    request=request,
                    start_response=start_response,
                    response=app.create_response(request),
                )
            except exc.HTTPException as e:
                response = e
            except Exception:
                self.logger.critical('Unhandled exception', exc_info=True)
                response = exc.HTTPInternalServerError()

        return [] if response is None else response(environ, start_response)

    def _serve(self, app, **params):
        self.launch_browser()

        super()._serve(app, **params)
