# --
# Copyright (c) 2014-2026 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
# --

from urllib.parse import urlsplit, urlencode, urlunsplit

import webob
from webob import exc

from nagare.server import base_application


def livereload(event, dirname, filename, reloader, url):
    if filename.endswith(('.css', '.js', '.gif', '.png', '.jpeg', '.jpg')):
        reloader.reload_asset(url + '/' + filename)

    return None


class Url:
    def __init__(self, url):
        self.url = url

    @staticmethod
    def is_absolute(scheme, path, fragment):
        return path.startswith('/') or (scheme == 'data') or (not path and fragment)

    @classmethod
    def absolute_url(cls, url, base_url, always_relative=False, base='', **params):
        """Convert a relative URL of a static content to an absolute one.

        In:
        - ``url`` -- url to convert
        - ``base_url`` -- URL prefix

        Return:
        - an absolute URL
        """
        scheme, netloc, path, query, fragment = urlsplit(url)
        default_scheme, default_netloc, path_prefix, _, _ = urlsplit(base_url or '')

        if not scheme and (always_relative or not cls.is_absolute(scheme, path, fragment)):
            path = path_prefix.rstrip('/') + '/' + path.lstrip('/')

        if params:
            query += ('&' if query and params else '') + urlencode(params)

        return urlunsplit((scheme or default_scheme, netloc or default_netloc, path, query, fragment))

    def absolute(self, base_url, always_relative=False, base='', **params):
        return self.absolute_url(self.url, base_url, always_relative, base, **params)


class Request(webob.Request):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.is_authenticated = False

    @property
    def scheme_hostname_port(self):
        url = urlsplit(super().host_url)

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

    CONFIG_SPEC = base_application.App.CONFIG_SPEC | {
        'url': 'string(default="")',
        'static_url': 'string(default="/static$app_url")',
        'static': 'string(default="$_static_path")',
        'gzip_static': 'boolean(default=True)',
    }

    def __init__(self, name_, dist_, url, static_url, static, gzip_static, services_service, **config):
        services_service(
            super().__init__,
            name_,
            dist_,
            url=url,
            static_url=static_url,
            static=static,
            gzip_static=gzip_static,
            **config,
        )

        url = url.strip('/')
        self.url = url and ('/' + url)
        self.static_url = static_url.rstrip('/')
        self.static_path = static.rstrip('/')
        self.gzip_static = gzip_static
        self.service_url = self.url + '/service'

    @staticmethod
    def absolute_url(url, base_url, always_relative=False, **params):
        return Url.absolute_url(url, base_url, always_relative, **params)

    def absolute_asset_url(self, url, always_relative=False, **params):
        return self.absolute_url(url, self.static_url, always_relative, **params)

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

    def handle_start(self, app, statics_service, services_service, reloader_service=None):
        services_service(super().handle_start, app)

        if self.static_url:
            statics_service.register_dir(self.static_url, self.static_path, self.gzip_static)

        if (reloader_service is not None) and (self.static_path):
            reloader_service.watch_dir(
                self.static_path, livereload, recursive=True, reloader=reloader_service, url=self.static_url
            )

        statics_service.register_app(self.url)

    def handle_request(self, chain, request, response, **params):
        return response


# ---------------------------------------------------------------------------


class RESTApp(App):
    CONFIG_SPEC = App.CONFIG_SPEC | {'default_content_type': 'string(default="application/json")'}

    def __init__(self, name_, dist_, default_content_type, router_service, services_service, **config):
        services_service(super().__init__, name_, dist_, default_content_type=default_content_type, **config)

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
