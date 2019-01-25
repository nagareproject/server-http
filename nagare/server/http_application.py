# Encoding: utf-8

# --
# Copyright (c) 2008-2019 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
# --

import webob
from webob import exc

from nagare.server import base_application


class Request(webob.Request):

    @property
    def is_xhr(self):
        return super(Request, self).is_xhr or ('_a' in self.params)

    def create_redirect_response(self, location=None, **params):
        location = location or self.path_url.rstrip('/')
        if params:
            location += '?' + '&'.join('%s=%s' % param for param in params.items())

        return (exc.HTTPServiceUnavailable if self.is_xhr else exc.HTTPSeeOther)(location=location)


class Response(webob.Response):
    default_content_type = ''


class App(base_application.App):
    """Application to handle a HTTP request"""

    CONFIG_SPEC = dict(
        base_application.App.CONFIG_SPEC,
        url='string(default=None)',
    )

    def __init__(
        self,
        name, dist,
        url,
        statics_service, services_service,
        **config
    ):
        """Initialization

        In:
          - ``services_service`` -- the services repository
        """
        services_service(super(App, self).__init__, name, dist, **config)

        self.url = (url if url is not None else name).rstrip('/')
        statics_service.register(self.url)

    @staticmethod
    def create_request(environ, *args, **kw):
        """Parse the REST environment received

        In:
          - ``environ`` -- the WSGI environment

        Return:
          - a ``WebOb`` Request object
        """
        return Request(environ, charset='utf-8', *args, **kw)

    @staticmethod
    def create_response(request, *args, **kw):
        """Return a response to the client

        In:
          - ``request`` -- the ``WebOb`` Request object

        Return:
          - a ``WebOb`` Response object
        """
        return Response(*args, **kw)

    def handle_request(self, chain, request, response, **params):
        return response

# ---------------------------------------------------------------------------


class RESTApp(App):

    CONFIG_SPEC = dict(
        App.CONFIG_SPEC,
        default_content_type='string(default="application/json")'
    )

    def __init__(self, name, dist, default_content_type, router_service, services_service, **config):
        services_service(super(RESTApp, self).__init__, name, dist, **config)

        self.default_content_type = default_content_type
        self.router = router_service

    def route(self, args):
        while isinstance(args, tuple):
            args = self.router(*args)

        return args

    def create_dispatch_args(self, **params):
        return (self,) + self.router.create_dispatch_args(**params)

    def set_body(self, response, body):
        if not response.content_type:
            response.content_type = self.default_content_type or 'application/octet-stream'

        if response.content_type == 'application/json':
            response.json_body = body or ''
        else:
            response.body = body or ''

        return response

    def handle_request(self, chain, response, **params):
        args = self.create_dispatch_args(response=response, **params)
        data = self.route(args)

        return self.set_body(response, data)
