# Encoding: utf-8

# --
# Copyright (c) 2008-2018 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
# --

import webob
from webob import exc

from nagare.server import application


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

    # def start_response(self, start_response):
    #    start_response(self.status, self.headerlist)(self.body)

# ---------------------------------------------------------------------------


class App(application.App):
    """Application to handle a HTTP request"""

    CONFIG_SPEC = dict(
        application.App.CONFIG_SPEC,
        url='string(default=None)',
        static_url='string(default="/static")',
        static='string(default="$static_path")'
    )

    def __init__(self, name, dist, url, static_url, static, statics_service=None, **config):
        """Initialization

        In:
          - ``services_service`` -- the services repository
        """
        super(App, self).__init__(name, dist, **config)

        if url is None:
            url = name

        if statics_service is not None:
            statics_service.register(url)

            if static:
                statics_service.register(static_url, static)
        else:
            if url:
                raise ValueError('"statics" service must be installed to serve on the url "%s"' % url)

            if static:
                raise ValueError('"statics" service must be installed to serve static contents on the url "%s"' % static)

        self.url = url.rstrip('/')
        self.static_url = static_url.rstrip('/')
        self.static_path = static.rstrip('/')

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

    CONFIG_SPEC = dict(App.CONFIG_SPEC, json='boolean(default=True)')

    def __init__(self, name, dist, json, router_service, services_service, **config):
        services_service(super(RESTApp, self).__init__, name, dist, **config)

        self.json = json
        self.router = router_service

    def route(self, args):
        while isinstance(args, tuple):
            args = self.router(*args)

        return args

    def handle_request(self, chain, request, response, **params):
        args = self.router.create_dispatch_args(request, response, **params)
        data = self.route((self,) + args) or ''

        if not response.content_type:
            response.content_type = 'application/json' if self.json else 'application/octet-stream'

        if response.content_type == 'application/json':
            response.json_body = data
        else:
            response.body = data

        return response
