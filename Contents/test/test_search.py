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

        for name in ['Log', 'Locale', 'Prefs', 'Agent', 'Platform', 'MetadataSearchResult']:
                patcher = patch("__builtin__."+name, create=True)
                setattr(self, name, patcher.start())
                self.addCleanup(patcher.stop)
        self.Agent.TV_Shows = object

        patch('Code.parallelize', create=True).start()
        import Code
        self.target = Code.xbmcnfotv()

    def test_sanity(self):
        self.assertEqual(1,1)

    @patch('os.path')
    def test_search(self, mock_path):
        results = MagicMock()
        media = MagicMock(id='an_id', title='a_title')
        lang = 'alang'

        extracted = {'id':'a_id', 'year':1970, 'title':'a_title', 'sorttitle':'a_sorttitle'}
        self.target._extract_info_for_mediafile = Mock(return_value=extracted)

        self.target._find_mediafile_for_id = Mock(side_effect="a_mediafile")
        self.assertEqual(self.target.search(results, media, lang), None)

        #self.MetadataSearchResult.assert_called_once_with(score=100, lang=lang, **extracted)
        #results.Append.assert_called_once()
        #self.Log.assert_called_with(AnyStringWith('craped results'))


if __name__ == '__main__':
    unittest.main()
