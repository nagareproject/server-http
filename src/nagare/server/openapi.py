# --
# Copyright (c) 2014-2026 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
# --

import os
import re
import json

from webob.exc import HTTPOk

from nagare.server import reference
from nagare.services import statics

CONFIG_SPEC = {
    'title': 'string(default="API documentation")',
    'url': 'string(default=None)',
    'directory': 'string(default="$static/openapi")',
    'default_document': 'string(default="")',
    'template': 'string(default="redoc")',
    # Redoc
    'disable_telemetry': 'boolean(default=True)',
    'generated_samples_max_depth': 'integer(default=None)',
    'hide_download_buttons': 'boolean(default=None)',
    'hide_properties_prefix': 'boolean(default=None)',
    'hide_schema_titles': 'boolean(default=None)',
    'json_samples_sxpandLevel': 'integer(default=None)',
    'layout': 'option("three-panel", "stacked", default=None)',
    'max_displayed_enum_values': 'integer(default=None)',
    'only_required_in_samples': 'boolean(default=None)',
    'sanitize': 'boolean(default=None)',
    'schema_definitions_tag_name': 'string(default=None)',
    'schemas_expansion_level': 'integer(default=None)',
    'show_extensions': 'boolean(default=None)',
    'sort_required_props_first': 'boolean(default=None)',
    'hide_loading': 'boolean(default=None)',
    'hide_schema_pattern': 'boolean(default=None)',
    'scroll_y_offset': 'integer(default=None)',
    'theme': 'option("light", "dark", default="light")',
    # Swagger-ui
    'deep_linking': 'boolean(default=None)',
    'display_operation_id': 'boolean(default=None)',
    'default_models_expand_depth': 'integer(default=None)',
    'default_model_expand_depth': 'integer(default=None)',
    'display_request_duration': 'boolean(default=None)',
    'filter': 'boolean(default=None)',
    'max_displayed_tags': 'integer(default=None)',
    'show_common_extensions': 'boolean(default=None)',
    'syntax_highlight': 'boolean(default=None)',
    'syntax_highlight.activated': 'boolean(default=None)',
    'try_it_out_enabled': 'boolean(default=None)',
    'request_snippets_enabled': 'boolean(default=None)',
    'validator_url': 'string(default=None)',
    'persist_authorization': 'boolean(default=None)',
    'tags_sorter': 'string(default=None, help="`alpha` or name of a js function")',
}

REDOC_TEMPLATE = """<!doctype html>
<html class="{theme}">
    <head>
        <title>{title}</title>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
    </head>

    <body style="margin: 0; padding: 0">
        <redoc/>
        <script type="module">
            import {{ init }} from "https://cdn.redoc.ly/redoc/v3.x/bundles/redoc.standalone.js";

            init("{yaml_url}", {config})
        </script>
    </body>
</html>
"""

SWAGGERUI_TEMPLATE = """<!doctype html>
<html>
    <head>
        <title>{title}</title>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">

        <link type="text/css" rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.11.0/swagger-ui.css">
        <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    </head>

    <body style="margin: 0; padding: 0">
        <div id="openapi"/>

        <script>
            SwaggerUIBundle({{
                ...{{
                    "url": "{yaml_url}",
                    "dom_id": "#openapi",
                    "presets": [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIBundle.SwaggerUIStandalonePreset
                    ]
                }},
                ...{config}
            }});
        </script>
    </body>
</html>
"""


class OpenAPIDirHandler(statics.DirHandler):
    def __init__(self, title, directory, default_document, template, theme, config):
        super().__init__(directory)

        self.title = title
        self.default_document = default_document
        self.template = template
        self.theme = theme
        self.config = {re.sub('_(.)', lambda m: m.group(1).upper(), k): v for k, v in config.items() if v is not None}

    def generate_file_response(self, request, response, filename):
        url = request.path_url
        if filename == self.dirname:
            filename = os.path.join(self.dirname, self.default_document)
            url = url.rstrip('/') + '/' + self.default_document

        if not os.path.isfile(filename + '.yaml'):
            return super().generate_file_response(request, response, filename)

        response = HTTPOk(
            content_type='text/html',
            text=self.template.format(
                title=self.title,
                yaml_url=url + '.yaml' + (('?' + request.query_string) if request.query_string else ''),
                theme=self.theme,
                config=json.dumps(self.config),
            ),
        )

        return response


def create_handler(title, directory, default_document='', template='redoc', url=None, theme=None, **config):
    if template == 'redoc':
        template = 'nagare.server.openapi:REDOC_TEMPLATE'
    if template == 'swagger-ui':
        template = 'nagare.server.openapi:SWAGGERUI_TEMPLATE'

    return OpenAPIDirHandler(title, directory, default_document, reference.load_object(template)[0], theme, config)


def register_handler(url, statics_service, **config):
    if url:
        statics_service.register(url, create_handler(**config))
