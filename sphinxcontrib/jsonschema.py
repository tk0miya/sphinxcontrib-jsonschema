"""
    sphinxcontrib.jsonschema
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: Copyright 2014 by Takeshi KOMIYA <i.tkomiya@gmail.com>
    :license: BSD, see LICENSE for details.
"""
import io
import os
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
        env = self.state.document.settings.env
        try:
            if self.arguments and self.content:
                raise self.warning('both argument and content. it is invalid')
            if self.arguments:
                dirname = os.path.dirname(env.doc2path(env.docname, base=None))
                relpath = os.path.join(dirname, self.arguments[0])
                if not os.access(os.path.join(env.srcdir, relpath), os.R_OK):
                    raise self.warning('JSON Schema file not readable: %s' %
                                       self.arguments[0])
                env.note_dependency(relpath)

                schema = JSONSchema.loadfromfile(relpath)
            else:
                schema = JSONSchema.loadfromfile(''.join(self.content))
        except ValueError as exc:
            raise self.error('Failed to parse JSON Schema: %s' % exc)

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
        for prop in schema:
            row = nodes.row()
            row += self.cell(prop.name)
            if prop.required:
                row += self.cell(prop.type + " (required)")
            else:
                row += self.cell(prop.type)
            row += self.cell(prop.description or '')
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


def get_class_for(obj):
    mapping = {
        'null': Null,
        'boolean': Boolean,
        'integer': Integer,
        'number': Number,
        'string': String,
        'array': Array,
        'object': Object,
    }
    if isinstance(obj, string_types):
        type = obj
    else:
        type = obj.get('type')
    return mapping.get(type, Object)


def simplify(obj):
    if isinstance(obj, dict) and obj.keys() == ['type']:
        type = obj.get('type')
        if type is None:
            return 'null'
        elif isinstance(type, string_types):
            return json.dumps(type)
        else:
            return str(type)
    else:
        return json.dumps(obj)


class JSONSchema(object):
    @classmethod
    def load(cls, reader):
        obj = json.load(reader, object_pairs_hook=OrderedDict)
        return cls.instantiate(None, obj)

    @classmethod
    def loads(cls, string):
        obj = json.loads(string, object_pairs_hook=OrderedDict)
        return cls.instantiate(None, obj)

    @classmethod
    def loadfromfile(cls, filename):
        with io.open(filename, 'rt', encoding='utf-8') as reader:
            return cls.load(reader)

    @classmethod
    def instantiate(cls, name, obj, required=False):
        return get_class_for(obj)(name, obj, required)


class JSONData(object):
    def __init__(self, name, attributes, required=False):
        self.name = name
        self.attributes = attributes
        self.required = required

    def __getattr__(self, name):
        if isinstance(self.attributes, dict):
            return self.attributes.get(name)
        else:
            return None

    def __iter__(self):
        return iter([])

    def get_typename(self):
        return self.type

    def stringify(self):
        return json.dumps(self.attributes)

    @property
    def validations(self):
        rules = []
        if 'enum' in self.attributes:
            enums = []
            for enum_type in self.enum:
                enums.append(simplify(enum_type))
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
        return rules


class Null(JSONData):
    type = "null"


class Boolean(JSONData):
    type = 'boolean'


class Integer(JSONData):
    type = 'integer'

    @property
    def validations(self):
        rules = super(Integer, self).validations
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
        return rules


class Number(Integer):
    type = 'number'


class String(JSONData):
    type = "string"

    @property
    def validations(self):
        rules = super(String, self).validations
        if 'maxLength' in self.attributes:
            rules.append('Its length must be less than or equal to %s' % self.maxLength)
        if 'minLength' in self.attributes:
            rules.append('Its length must be greater than or equal to %s' % self.minLength)
        if 'pattern' in self.attributes:
            rules.append('It must match to regexp "%s"' % self.pattern)
        if 'format' in self.attributes:
            rules.append('It must be formatted as %s' % self.format)
        return rules


class Array(JSONData):
    type = "array"

    def __init__(self, name, attributes, required=False):
        if name:
            name += '[]'
        else:
            name = '[]'
        super(Array, self).__init__(name, attributes, required)

    @property
    def validations(self):
        rules = super(Array, self).validations
        if self.additionalItems is True:
            rules.append('It allows additional items')
        if 'maxItems' in self.attributes:
            rules.append('Its size must be less than or equal to %s' % self.maxItems)
        if 'minItems' in self.attributes:
            rules.append('Its size must be greater than or equal to %s' % self.minItems)
        if 'uniqueItems' in self.attributes:
            if self.uniqueItems:
                rules.append('Its elements must be unique')
        if isinstance(self.items, dict):
            item = JSONSchema.instantiate(self.name, self.items)
            if item.type not in ('array', 'object'):
                rules.extend(item.validations)

        return rules

    def __iter__(self):
        if isinstance(self.items, dict):
            item = JSONSchema.instantiate(self.name, self.items)

            # array object itself
            array = JSONSchema.instantiate(self.name[:-2], self.attributes)
            array.type = 'array[%s]' % item.get_typename()
            yield array

            # properties of items
            for prop in item:
                yield prop
        else:
            # create items and additionalItems objects
            items = []
            types = []
            for i, item in enumerate(self.items):
                name = '%s[%d]' % (self.name[:-2], i)
                items.append(JSONSchema.instantiate(name, item))
                types.append(items[-1].get_typename())

            if isinstance(self.additionalItems, dict):
                name = '%s[%d+]' % (self.name[:-2], len(items))
                additional = JSONSchema.instantiate(name, self.additionalItems)
                types.append(additional.get_typename() + '+')
            else:
                additional = None

            # array object itself
            array = JSONSchema.instantiate(self.name[:-2], self.attributes)
            array.type = 'array[%s]' % ','.join(types)
            yield array

            # properties of items
            for item in items:
                yield item
                for prop in item:
                    yield prop

            # additionalItems
            if additional:
                yield additional

                for prop in additional:
                    yield prop


class Object(JSONData):
    type = "object"

    def get_typename(self):
        if self.title:
            return self.title
        else:
            return self.type

    @property
    def validations(self):
        rules = super(Object, self).validations
        if 'maxProperties' in self.attributes:
            rules.append('Its numbers of properties must be less than or equal to %s' % self.maxProperties)
        if 'minProperties' in self.attributes:
            rules.append('Its numbers of properties must be greater than or equal to %s' % self.minProperties)
        if 'required' in self.attributes:
            rules.append('Its property set must contains all elements in %s' % self.required)
        if 'dependencies' in self.attributes:
            for name, attr in self.dependencies.items():
                if isinstance(attr, dict):
                    rules.append('The "%s" property must match to %s' % (name, simplify(attr)))
                else:
                    attr = (simplify(name) for name in attr)
                    rules.append('The "%s" property depends on [%s]' % (name, ', '.join(attr)))
        return rules

    def __iter__(self):
        for prop in self.get_properties():
            yield prop

            if prop.type == "object":
                for subprop in prop:
                    yield subprop

    def get_properties(self):
        if self.name:
            prefix = self.name + '.'
        else:
            prefix = ''
        required = self.attributes.get('required', [])

        for name, attr in self.attributes.get('properties', {}).items():
            yield JSONSchema.instantiate(prefix + name, attr, name in required)

        for name, attr in self.attributes.get('patternProperties', {}).items():
            yield JSONSchema.instantiate(prefix + name, attr)

        if isinstance(self.additionalProperties, dict):
            yield JSONSchema.instantiate(prefix + '*', attr)


def setup(app):
    app.add_directive('jsonschema', JSONSchemaDirective)
