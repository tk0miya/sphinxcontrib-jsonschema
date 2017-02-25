# -*- coding: utf-8 -*-

import sys
from sphinx_testing import with_app

if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest


class TestJsonSchema(unittest.TestCase):
    @with_app(srcdir='tests/examples/basic')
    def test_basic(self, app, status, warning):
        app.build()  # succeeded!
