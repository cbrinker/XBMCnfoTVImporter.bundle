#!/usr/bin/env python

import unittest
from mock import Mock, MagicMock, patch

from lxml import etree as ET

class AnyStringWith(str):
    def __eq__(self, other):
        return self in other
def arg_should_contain(x):
    def wrapper(arg):
        assert str(x) in arg, "'%s' does not contain '%s'" % (arg, x)
    return wrapper

class TestSearch(unittest.TestCase):
    def setUp(self):

        for name in ['Log', 'Locale', 'Prefs', 'Agent', 'Platform', 'MetadataSearchResult', 'XML','String']:
                patcher = patch("__builtin__."+name, create=True)
                setattr(self, name, patcher.start())
                self.addCleanup(patcher.stop)
        self.Agent.TV_Shows = object

        patch('Code.parallelize', create=True).start()
        import Code
        self.target = Code.xbmcnfotv()

    def test_sanity(self):
        self.assertEqual(1,1)


if __name__ == '__main__':
    unittest.main()
