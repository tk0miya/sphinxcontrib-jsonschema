"""
    sphinxcontrib.jsonschema
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: Copyright 2014 by Takeshi KOMIYA <i.tkomiya@gmail.com>
    :license: BSD, see LICENSE for details.
"""
import io
import sys
from six import string_types
from docutils import nodes
from docutils.statemachine import ViewList
from docutils.parsers.rst import Directive

if sys.version_info < (2, 7):
    import simplejson as json
    from ordereddict import OrderedDict
else:
    import json
    from collections import OrderedDict


class JSONSchemaDirective(Directive):
    has_content = True
    required_arguments = 1

    def run(self):
        if self.arguments and self.content:
            raise self.warning('both argument and content. it is invalid')
        if self.arguments:
            schema = JSONSchemaObject.loadfromfile(self.arguments[0])
        else:
            schema = JSONSchemaObject.loadfromfile(''.join(self.content))
        if schema.type != 'object':
            raise NotImplemented
        headers = ['Name', 'Type', 'Description', 'Validations']
        widths = [1, 1, 1, 2]
        tgroup = nodes.tgroup(cols=len(headers))
        for width in widths:
            tgroup += nodes.colspec(colwidth=width)

        table = nodes.table('', tgroup)
        header_row = nodes.row()
        for header in headers:
            entry = nodes.entry('', nodes.paragraph(text=header))
            header_row += entry

        tgroup += nodes.thead('', header_row)
        tbody = nodes.tbody()
        tgroup += tbody
        for name, prop in schema.properties.items():
            row = nodes.row()
            row += self.cell(name)
            row += self.cell(prop.type)
            row += self.cell(prop.description)
            row += self.cell('\n'.join(('* %s' % v for v in prop.validations)))
            tbody += row

        return [table]

    def cell(self, text):
        entry = nodes.entry()
        if not isinstance(text, string_types):
            text = str(text)
        viewlist = ViewList(text.split('\n'), source=text)
        self.state.nested_parse(viewlist, 0, entry)
        return entry


class JSONSchemaObject(object):

    @classmethod
    def load(cls, reader):
        obj = json.load(reader, object_pairs_hook=OrderedDict)
        return cls(obj)

    @classmethod
    def loads(cls, string):
        obj = json.loads(string, object_pairs_hook=OrderedDict)
        return cls(obj)

    @classmethod
    def loadfromfile(cls, filename):
        with io.open(filename, 'rt', encoding='utf-8') as reader:
            return cls.load(reader)

    def __init__(self, attributes):
        if isinstance(attributes, (string_types, int, float)) or attributes is None:
            self.attributes = {'type': attributes}
        else:
            self.attributes = attributes
        return

    def __getattr__(self, name):
        return self.attributes.get(name, '')

    def stringify(self):
        keys = list(self.attributes.keys())
        if keys == ['type']:
            if self.type is None:
                return 'null'
            elif isinstance(self.type, string_types):
                return '"%s"' % self.type
            else:
                return str(self.type)
        else:
            return json.dumps(self.attributes)
        return

    @property
    def properties(self):
        props = []
        for name, attr in self.attributes.get('properties', {}):
            props.append((name, JSONSchemaObject(attr)))

        for name, attr in self.attributes.get('patternProperties', {}):
            props.append((name, JSONSchemaObject(attr)))

        if isinstance(self.additionalProperties, dict):
            props.append(('.*', JSONSchemaObject(attr)))
        return dict(props)

    @property
    def validations(self):
        rules = []
        if 'multipleOf' in self.attributes:
            rules.append('It must be multiple of %s' % self.multipleOf)
        if 'maximum' in self.attributes:
            if self.exclusiveMaximum:
                rules.append('It must be lower than or equal to %s' % self.maximum)
            else:
                rules.append('It must be lower than %s' % self.maximum)
        if 'minimum' in self.attributes:
            if self.exclusiveMinimum:
                rules.append('It must be greater than or equal to %s' % self.minimum)
            else:
                rules.append('It must be greater than %s' % self.minimum)
        if 'maxLength' in self.attributes:
            rules.append('Its length must be less than or equal to %s' % self.maxLength)
        if 'minLength' in self.attributes:
            rules.append('Its length must be greater than or equal to %s' % self.minLength)
        if 'pattern' in self.attributes:
            rules.append('It must match to regexp "%s"' % self.pattern)
        if 'items' in self.attributes:
            if isinstance(self.items, dict):
                items = JSONSchemaObject(self.items)
                rules.append('All items must match to %s' % items.stringify())
            else:
                items = [JSONSchemaObject(o).stringify() for o in self.items]
                if self.additionalItems is True:
                    rules.append('First %d items must match to [%s]' % (len(items), ', '.join(items)))
                elif self.additionalItems:
                    additional = JSONSchemaObject(self.additionalItems)
                    rules.append('First %d items must match to [%s] and others must match to %s' %
                                 (len(items), ', '.join(items), additional.stringify()))
                else:
                    rules.append('All items must match to [%s]' % ', '.join(items))
        if 'maxItems' in self.attributes:
            rules.append('Its size must be less than or equal to %s' % self.maxItems)
        if 'minItems' in self.attributes:
            rules.append('Its size must be greater than or equal to %s' % self.minItems)
        if 'uniqueItems' in self.attributes:
            if self.uniqueItems:
                rules.append('Its elements must be unique')
        if 'maxProperties' in self.attributes:
            rules.append('Its numbers of properties must be less than or equal to %s' % self.maxProperties)
        if 'minProperties' in self.attributes:
            rules.append('Its numbers of properties must be greater than or equal to %s' % self.minProperties)
        if 'required' in self.attributes:
            rules.append('Its property set must contains all elements in %s' % self.required)
        if 'dependencies' in self.attributes:
            for name, attr in self.dependencies.items():
                if isinstance(attr, dict):
                    depends = JSONSchemaObject(attr).stringify()
                    rules.append('The "%s" property must match to %s' % (name, depends))
                else:
                    attr = (JSONSchemaObject(name).stringify() for name in attr)
                    rules.append('The "%s" property depends on [%s]' % (name, ', '.join(attr)))

        if 'enum' in self.attributes:
            enums = []
            for enum_type in self.enum:
                enums.append(JSONSchemaObject(enum_type).stringify())

            rules.append('It must be equal to one of the elements in [%s]' % ', '.join(enums))
        if 'allOf' in self.attributes:
            pass
        if 'anyOf' in self.attributes:
            pass
        if 'oneOf' in self.attributes:
            pass
        if 'not' in self.attributes:
            pass
        if 'definitions' in self.attributes:
            pass
        if 'format' in self.attributes:
            rules.append('It must be formatted as %s' % self.format)
        return rules


def setup(app):
    app.add_directive('json-schema', JSONSchemaDirective)
