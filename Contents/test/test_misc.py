#!/usr/bin/env python

import unittest

from mock import Mock, MagicMock, patch
from lxml import etree as ET

from test import MyPlexTester, PrepareForPlexTest, AnyStringWith, ArgShouldContain

#print(mock.call_args_list)

PrepareForPlexTest()
import Code

class TestUtilities(MyPlexTester):
    def setUp(self):
        self.target = Code.xbmcnfotv()

    def test_sanity(self):
        self.assertEqual(1,1)

    def test_basic_class(self):
        self.assertEqual(self.target.name, 'XBMCnfoTVImporter')
        self.assertEqual(self.target.primary_provider, True)

    def test_not_debug_logging(self):
        my_log = self.patch('__builtin__.Log')
        my_prefs = self.patch('__builtin__.Prefs')

        my_prefs.__getitem__.return_value = 0
        self.target.DLog("Anything")
        my_log.assert_not_called()

    def test_debug_logging(self):
        my_log = self.patch('__builtin__.Log')
        my_prefs = self.patch('__builtin__.Prefs')

        msg = "A test message"
        my_prefs.__getitem__.return_value = 1
        self.target.DLog(msg)
        my_prefs.__getitem__.assert_called_with('debug')
        my_log.assert_called_with(msg)


    def test_set_duration_as_avg_of_episodes(self):
        for _in, _out in [
            ([0, 100, 0], 6000000),
            ([20,30,40,50], 2100000),
            ([2.5,1.2], 60000),
            ([0, 0], 0),
            (None, 0),
            ("", 0),
            ([], 0),
        ]:
            self.assertEqual(self.target._set_duration_as_avg_of_episodes(_in), _out)

    def test_log_function_entry(self):
        my_log = self.patch('__builtin__.Log')
        my_prefs = self.patch('__builtin__.Prefs')

        my_prefs.__getitem__.return_value = True
        self.assertEqual(self.target._log_function_entry('AFuncName'), None)
        my_log.assert_any_call(AnyStringWith('Entering AFuncName'))
        my_log.assert_any_call(AnyStringWith('is enabled'))

    def test_log_function_entry_disabled(self):
        my_log = self.patch('__builtin__.Log')
        my_prefs = self.patch('__builtin__.Prefs')

        Prefs.__getitem__.return_value = False
        self.assertEqual(self.target._log_function_entry('AFuncNameX'), None)
        my_log.assert_any_call(AnyStringWith('is disabled'))


    def test_find_nfo_for_file_tvshow(self):
        mock_path = self.patch('os.path')
        # Simulate os.path calls based on just string manipulation
        mock_path.dirname = Mock(side_effect = lambda x: "/".join(x.split("/")[:-1]))
        mock_path.exists  = Mock(side_effect = lambda x: x in files_exist_at)
        mock_path.join    = Mock(side_effect = lambda x,y: x+"/"+y)

        for files_exist_at, _in, _out in [
            (['a/b/tvshow.nfo'], 'a/b/c/d', 'a/b/tvshow.nfo'), # perfect match
            (['a/b/c/tvshow.nfo'], 'a/b/c/d', 'a/b/c/tvshow.nfo'), # path guess 1
            (['a/tvshow.nfo'], 'a/b/c/d', 'a/tvshow.nfo'), #path guess 2
            ([], 'a/b/c/d', None), # No files found
        ]:
            self.assertEqual(self.target._find_nfo_for_file(_in), _out)

    def test_find_nfo_for_file_episode(self):
        mock_path = self.patch('os.path')
        # Simulate os.path calls based on just string manipulation
        mock_path.dirname = Mock(side_effect = lambda x: "/".join(x.split("/")[:-1]))
        mock_path.exists  = Mock(side_effect = lambda x: x in files_exist_at)
        mock_path.join    = Mock(side_effect = lambda x,y: x+"/"+y)
        mock_path.basename = Mock(side_effect = lambda x: x.rsplit("/",1)[-1])

        for files_exist_at, _in, _out in [
            (['a/b/something.nfo'], 'a/b/something.xyz', 'a/b/something.nfo'), # perfect match
            ([], 'a/b/c/d', None), # No files found
        ]:
            self.assertEqual(self.target._find_nfo_for_file(_in, algo='episode'), _out)

    def test_guess_title_by_mediafile(self):
        mock_path = self.patch('os.path')
        mock_path.basename = Mock(side_effect = lambda x: x.split("/")[-1])

        for _in, _out in [
            ('a/b/Dotted.Test.Show.S11E22.ext', 'Dotted Test Show'),
            ('a/b/space show S11E22.ext', 'space show'),
            ('a/b/Simple.S11E22.garbage.ext', 'Simple'),
            ('a/b/Another Simple S11E22 garbage ext', 'Another Simple'),
            ('', None),
            ('a/b/non_conformant.ext', None),
        ]:
            self.assertEqual(self.target._guess_title_by_mediafile(_in), _out)

    def test_extract_info_for_mediafile(self):
        _sanitize_nfo = self.patch('Code._sanitize_nfo')
        self.target._find_nfo_for_file = Mock(return_value = "afile.nfo")
        Core.storage.return_value.load.return_value = 'some text'
        self.target.parser._parse_tvshow_nfo_text = Mock(return_value = {'made':'it'})

        self.assertEqual(self.target._extract_info_for_mediafile("afile.ext"), {'made':'it','nfo_file':'afile.nfo'})
        Core.storage.load.assert_called_once_with('afile.nfo')
        _sanitize_nfo.assert_called() # Make sure we are sanitizing
        self.target.parser._parse_tvshow_nfo_text.assert_called()

        self.target._find_nfo_for_file = Mock(return_value = None)
        self.assertEqual(self.target._extract_info_for_mediafile("afile.ext"), {})


    #def test_update(self):
    #    mock_path = self.patch('os.path')
    #    results = MagicMock()
    #    media = MagicMock()
    #    lang = None
    #    out = self.target.update(results, media, lang)
    #    self.assertEqual(out, None)


class TestSearch(MyPlexTester):
    def setUp(self):
        self.target = Code.xbmcnfotv()

    def test_search(self):
        mock_path = self.patch('os.path')
        results = MagicMock()
        media = MagicMock(id='an_id', title='a_title')
        lang = 'alang'
        extracted = {'id':'a_id', 'year':1970, 'title':'a_title', 'sorttitle':'a_sorttitle'}
        self.target._extract_info_for_mediafile = Mock(return_value=extracted)

        pms = Mock()
        pms._find_mediafiles_for_id = Mock(side_effect="a_mediafile")
        self.target.pms = pms

        self.assertEqual(self.target.search(results, media, lang), None)

        MetadataSearchResult.assert_called_once_with(score=100, lang=lang, **extracted)
        results.Append.assert_called_once()
        Log.assert_called_with(AnyStringWith('craped results'))

    def test_search_error_with_mediafile(self):
        mock_path = self.patch('os.path')
        my_log = self.patch('__builtin__.Log') # reinitialize to verify not called

        pms = Mock()
        pms._find_mediafiles_for_id = Mock(side_effect=Exception())
        self.target.pms = pms

        self.assertEqual(self.target.search(Mock(), Mock(), Mock()), None)

        my_log.assert_called_with(AnyStringWith('Traceback'))


    def test_search_with_guessing(self):
        mock_path = self.patch('os.path')
        mock_gen = self.patch('Code._generate_id_from_title', return_value='12345')
        my_msr = self.patch('__builtin__.MetadataSearchResult')
        my_log = self.patch('__builtin__.Log') # reinitialize to verify not called

        results = Mock()
        pms = Mock()
        pms._find_mediafiles_for_id = Mock(side_effect="a_mediafile")
        self.target.pms = pms
        self.target._extract_info_for_mediafile = Mock(return_value={})
        self.target._guess_title_by_mediafile = Mock(return_value='a_guess')

        self.assertEqual(self.target.search(results, Mock(title=None, id=None), 'alang'), None)

        my_log.assert_called_with(AnyStringWith('craped results'))
        results.Append.assert_called_once()
        my_msr.assert_called_once_with(id='12345', score=100, lang='alang', sorttitle=None, title='a_guess', year=0)

class TestMultipleEpisode(MyPlexTester):
    def setUp(self):
        self.target = Code.xbmcnfotv()

    def test_multiple_episodes(self):
        mock_path = self.patch('os.path')
        _prefs = {
            'multEpisodePlexPatch': True,
            'multEpisodeTitleSeparator': ';',
            'debug': True,
        }
        Prefs.__getitem__.side_effect=lambda x: _prefs[x]
        self.target.RemoveEmptyTags = Mock(side_effect=lambda x:x)
        XML.ElementFromString.side_effect=lambda x: ET.fromstring(x)

        for _in, _out in [
            (
                ("""<x><episode>9</episode><title>t1</title><plot>p1</plot>
                    </x><x><title>t2</title><plot>p2</plot></x>""", '/x/afile.ext', 1, 'x'),
                {
                    'enabled': True,
                    'nfo_episode_count': 2,
                    'possible': True,
                    'summary': '[Episode #9 - t1] p1\n[Episode #2 - t2] p2',
                    'title': 't1;t2',
                },
            ),
            (
                ("<x><title>b_title</title><plot>b_plot</plot></x>", '/x/afile.ext', 1, 'x'),
               {
                    'enabled': True,
                    'nfo_episode_count': 1,
                    'possible': False,  # Only one episode
                },
            ),
            (
                ("<x></x><x></x>", '/x/.S1E1-E1.ext', 1, 'x'),
                {
                    'enabled': True,
                    'nfo_episode_count': 2,
                    'possible': False,
                },
            ),
        ]:
            xml, output = self.target._multiple_episode_feature(*_in)
            self.assertEqual(output, _out)


class TestParseEpisode(MyPlexTester):
    def setUp(self):
        self.target = Code.xbmcnfotv()

    def test_parse_episode_nfo_text(self):
        nfo_xml = ET.fromstring("""<x><title>a_title</title><mpaa>PG</mpaa><plot>aplot</plot></x>""")
        self.assertEqual(self.target._parse_episode_nfo_text(nfo_xml, {}), {
            'content_rating':'PG',
            'title':'a_title',
            'summary':'aplot',
        })

    def test_parse_episode_nfo_text_title_overrides(self):
        nfo_xml = ET.fromstring("""<x><title>a_title</title><mpaa>PG</mpaa></x>""")
        self.assertEqual(self.target._parse_episode_nfo_text(nfo_xml, {'title':'better title'}), {
            'content_rating':'PG',
            'title':'better title',
        })

if __name__ == '__main__':
    unittest.main()
