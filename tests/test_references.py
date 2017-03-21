# -*- coding: utf-8 -*-

import sys
from collections import OrderedDict
import json
from sphinxcontrib.jsonschema import resolve_all_refs, resolve_ref

if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest


class TestJSONReference(unittest.TestCase):
    def test_resolve_ref(self):
        thing = OrderedDict({"title": "stuff"})
        ref = {"$ref": "#/definitions/somename/0"}
        data = {"definitions": {"somename": [thing]}}
        resolved = resolve_ref(ref, data)
        self.assertEqual(resolved, thing)

    def test_resolve_all_refs(self):
        data1 = json.loads("""{
            "definitions": {
                "thing": {
                    "title": "stuff"
                }
            },
            "properties": {
                "a": {"$ref": "#/definitions/thing"}
            }
        }""", object_pairs_hook=OrderedDict)
        data2 = json.loads("""{
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
        resolved = resolve_all_refs(data1, data1)
        self.assertEqual(resolved, data2)
