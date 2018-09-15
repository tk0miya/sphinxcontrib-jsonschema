# -*- coding: utf-8 -*-

import sys
from collections import OrderedDict
import json
from sphinxcontrib.jsonschema import JSONSchema

if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest


class TestJSONReference(unittest.TestCase):
    def test_jsonschema_loads(self):
        resolved = JSONSchema.loads("""{
            "definitions": {
                "thing": {
                    "title": "stuff"
                }
            },
            "properties": {
                "a": {"$ref": "#/definitions/thing"}
            }
        }""").attributes
        expected = json.loads("""{
            "definitions": {
                "thing": {
                    "title": "stuff"
                }

            },
            "properties": {
                "a": {
                    "title": "stuff"
                }
            }
        }""", object_pairs_hook=OrderedDict)
        self.assertEqual(resolved, expected)
