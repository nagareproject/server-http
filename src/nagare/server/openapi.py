# Encoding: utf-8

# --
# Copyright (c) 2008-2023 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
# --

import json
import os
import re

from nagare.server import reference
from nagare.services import statics
from webob.exc import HTTPOk

CONFIG_SPEC = {
    'title': 'string(default="API documentation")',
    'url': 'string(default=None)',
    'directory': 'string(default="$static/openapi")',
    'default_document': 'string(default="")',
    'template': 'string(default="redoc")',
    # Redoc
    'disable_search': 'boolean(default=None)',
    'min_character_length_to_init_search': 'integer(default=None)',
    'expand_default_server_variables': 'boolean(default=None)',
    'expand_responses': 'string(default=None)',
    'expand_single_schema_fields': 'boolean(default=None)',
    'hide_download_button': 'boolean(default=None)',
    'hide_hostname': 'boolean(default=None)',
    'hide_loading': 'boolean(default=None)',
    'hide_request_payload_sample': 'boolean(default=None)',
    'hide_schema_pattern': 'boolean(default=None)',
    'hide_one_of_description': 'boolean(default=None)',
    'hide_schema_titles': 'boolean(default=None)',
    'hide_single_request_sample_tab': 'boolean(default=None)',
    'show_object_schema_examples': 'boolean(default=None)',
    'html_template': 'string(default=None)',
    'max_displayed_enum_values': 'integer(default=None)',
    'menu_toggle': 'boolean(default=None)',
    'native_scrollbars': 'boolean(default=None)',
    'only_required_in_samples': 'boolean(default=None)',
    'path_in_middle_panel': 'boolean(default=None)',
    'payload_sample_idx': 'integer(default=None)',
    'required_props_first': 'boolean(default=None)',
    'scroll_y_offset': 'string(default=None)',
    'show_webhook_verbs': 'boolean(default=None)',
    'show_extensions': 'boolean(default=None)',
    'hide_security_section': 'boolean(default=None)',
    'simple_one_of_type_label': 'boolean(default=None)',
    'sort_enum_values_alphabetically': 'boolean(default=None)',
    'sort_props_alphabetically': 'boolean(default=None)',
    'untrusted_definition': 'boolean(default=None)',
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
}

REDOC_TEMPLATE = """<!doctype html>
<html>
    <head>
        <title>{title}</title>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">

        <script src="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js"></script>
    </head>

    <body style="margin: 0; padding: 0">
        <redoc/>
        <script>Redoc.init("{yaml_url}", {config});</script>
    </body>
</html>
"""

SWAGGERUI_TEMPLATE = """<!doctype html>
<html>
    <head>
        <title>{title}</title>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">

        <link type="text/css" rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
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
    def __init__(self, title, directory, default_document, template, config):
        super(OpenAPIDirHandler, self).__init__(directory)

        self.title = title
        self.default_document = default_document
        self.template = template
        self.config = {re.sub('_(.)', lambda m: m.group(1).upper(), k): v for k, v in config.items() if v is not None}

    def generate_file_response(self, request, response, filename):
        url = request.path_url
        if filename == self.dirname:
            filename = os.path.join(self.dirname, self.default_document)
            url = url.rstrip('/') + '/' + self.default_document

        if not os.path.isfile(filename + '.yaml'):
            return super(OpenAPIDirHandler, self).generate_file_response(request, response, filename)

        response = HTTPOk(
            content_type='text/html',
            text=self.template.format(
                title=self.title,
                yaml_url=url + '.yaml' + (('?' + request.query_string) if request.query_string else ''),
                config=json.dumps(self.config),
            ),
        )

        return response


def create_handler(title, directory, default_document='', template='redoc', url=None, **config):
    if template == 'redoc':
        template = 'nagare.server.openapi:REDOC_TEMPLATE'
    if template == 'swagger-ui':
        template = 'nagare.server.openapi:SWAGGERUI_TEMPLATE'

    return OpenAPIDirHandler(title, directory, default_document, reference.load_object(template)[0], config)


def register_handler(url, statics_service, **config):
    if url:
        statics_service.register(url, create_handler(**config))
