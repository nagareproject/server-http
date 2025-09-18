# --
# Copyright (c) 2008-2025 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
# --

try:
    from urllib.parse import urlparse, urlencode
except ImportError:
    from urllib import urlencode

    from urlparse import urlparse

import webob
from webob import exc

from nagare.server import base_application


class Request(webob.Request):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.is_authenticated = False

    @property
    def scheme_hostname_port(self):
        url = urlparse(super().host_url)

        schemes = self.headers.get('X-Forwarded-Proto', url.scheme)
        scheme = schemes.split(',', 1)[0].strip()

        hosts = self.headers.get('X-Forwarded-Host') or self.headers.get('Host')
        if hosts:
            host = hosts.split(',', 1)[0].strip()
            host_name, _, host_port = host.partition(':')
            host_port = int(host_port) if host_port.isdigit() else None
        else:
            host_name = url.hostname
            host_port = url.port

        ports = self.headers.get('X-Forwarded-Port', '')
        port = ports.split(',', 1)[0].strip()
        port = int(port) if port.isdigit() else None

        return scheme, host_name, port or host_port

    @property
    def host_port(self):
        return self.scheme_hostname_port[2] or ''

    @property
    def host_url(self):
        scheme, hostname, port = self.scheme_hostname_port
        if (scheme == 'http' and port == 80) or (scheme == 'https' and port == 443):
            port = None

        return scheme + '://' + hostname + ((':' + str(port)) if port else '')

    @property
    def is_xhr(self):
        return super().is_xhr or ('_a' in self.params)

    def create_redirect_url(self, location=None, add_slash=True, **params):
        redirect_url = location or self.path_url

        if add_slash and not redirect_url.endswith('/'):
            redirect_url += '/'

        if params:
            redirect_url += '?' + urlencode(params)

        return redirect_url

    def create_redirect_response(
        self,
        location=None,
        response=None,
        redirect_exc=exc.HTTPSeeOther,
        commit_transaction=False,
        add_slash=True,
        **params,
    ):
        redirect_url = self.create_redirect_url(location, add_slash, **params)
        redirect = (exc.HTTPServiceUnavailable if self.is_xhr else redirect_exc)(location=redirect_url)
        redirect.commit_transaction = commit_transaction
        if response is not None:
            response.merge_cookies(redirect)

        return redirect


class Response(webob.Response):
    default_content_type = ''


class App(base_application.App):
    """Application to handle a HTTP request."""

    CONFIG_SPEC = dict(base_application.App.CONFIG_SPEC, url='string(default="")')

    def __init__(self, name, dist, url, services_service, **config):
        services_service(super().__init__, name, dist, url=url, **config)

        url = url.strip('/')
        self.url = url and ('/' + url)
        self.service_url = self.url + '/service'

    @staticmethod
    def create_request(environ, *args, **kw):
        """Parse the REST environment received.

        In:
          - ``environ`` -- the WSGI environment

        Return:
          - a ``WebOb`` Request object
        """
        return Request(environ, charset='utf-8', *args, **kw)

    @staticmethod
    def create_response(request, *args, **kw):
        """Return a response to the client.

        In:
          - ``request`` -- the ``WebOb`` Request object

        Return:
          - a ``WebOb`` Response object
        """
        return Response(*args, **kw)

    def handle_start(self, app, statics_service, services_service):
        services_service(super().handle_start, app)
        statics_service.register_app(self.url)

    def handle_request(self, chain, request, response, **params):
        return response


# ---------------------------------------------------------------------------


class RESTApp(App):
    CONFIG_SPEC = dict(App.CONFIG_SPEC, default_content_type='string(default="application/json")')

    def __init__(self, name, dist, default_content_type, router_service, services_service, **config):
        services_service(super().__init__, name, dist, default_content_type=default_content_type, **config)

        self.default_content_type = default_content_type
        self.router = router_service

    def route(self, args):
        while isinstance(args, tuple):
            args = self.router(*args)

        return args

    def create_dispatch_args(self, **params):
        return (self,) + self.router.create_dispatch_args(**params)

    def set_response_body(self, response, body):
        if not response.content_type:
            response.content_type = self.default_content_type or 'application/octet-stream'

        if body is not None:
            if response.content_type == 'application/json':
                response.json_body = body
            else:
                response.body = body

        return response

    def handle_request(self, chain, response, **params):
        args = self.create_dispatch_args(response=response, **params)
        data = self.route(args)

        return self.set_response_body(response, data)
