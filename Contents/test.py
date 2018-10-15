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

#print(mock.call_args_list)

class TestUtilities(unittest.TestCase):
    def setUp(self):

        for name in ['Log', 'Locale', 'Prefs', 'Agent', 'Platform', 'XML', 'String', 'Core', 'MetadataSearchResult', 'Dict']:
                patcher = patch("__builtin__."+name, create=True)
                setattr(self, name, patcher.start())
                self.addCleanup(patcher.stop)
        self.Agent.TV_Shows = object

        patch('Code.parallelize', create=True).start()
        import Code
        self.target = Code.xbmcnfotv()

    def test_sanity(self):
        self.assertEqual(1,1)

    def test_basic_class(self):
        self.assertEqual(self.target.name, 'XBMCnfoTVImporter')
        self.assertEqual(self.target.primary_provider, True)

    def test_not_debug_logging(self):
        self.Prefs.__getitem__.return_value = 0
        self.target.DLog("Anything")
        self.Log.assert_not_called()

    def test_debug_logging(self):
        msg = "A test message"
        self.Prefs.__getitem__.return_value = 1
        self.target.DLog(msg)
        self.Prefs.__getitem__.assert_called_with('debug')
        self.Log.assert_called_with(msg)

    def test_time_convert(self):
        for _in, _out in [
                (0, 0),
                (1, 3600000),
                (2, 7200000),
                (3, 180000),
                (119, 7140000),
                (120, 7200000),
                (121, 121000),
                (7199, 7199000),
                (7200, 7200000),
                (7201, 7201),
        ]:
                self.assertEqual(self.target.time_convert(_in), _out)


    def test_check_file_paths_no_input(self):
        out = self.target.checkFilePaths([], 'a_type')
        self.assertEqual(out, None)
        self.Log.assert_called_once_with(AnyStringWith('a_type'))

    @patch('os.path')
    def test_check_file_paths_success(self, mock_path):
        mock_path.isdir.return_value = False
        mock_path.exists.return_value = True
        out = self.target.checkFilePaths(['1stfound','y'], 'a_type')
        self.assertEqual(out, '1stfound')
        mock_path.exists.assert_called_once_with('1stfound')
        self.Log.assert_called_with(AnyStringWith('Found a_type'))

    @patch('os.path')
    def test_check_file_paths_skip_dirs(self, mock_path):
        mock_path.isdir.return_value = True
        mock_path.exists.return_value = True
        out = self.target.checkFilePaths(['1stfound','y'], 'a_type')
        self.assertEqual(out, None)

    @patch('os.path')
    def test_check_file_paths_skip_non_files(self, mock_path):
        mock_path.isdir.return_value = False
        mock_path.exists.return_value = False
        out = self.target.checkFilePaths(['1stfound','y'], 'a_type')
        self.assertEqual(out, None)

    def test_remove_empty_tags(self):
        _in = ET.fromstring("<x><a>Hello</a><b></b><c> </c></x>")
        _out = ET.fromstring("<x><a>Hello</a></x>")
        out = self.target.RemoveEmptyTags(_in)
        self.assertTrue(ET.tostring(out), ET.tostring(_out))

    def test_unescape(self):
        for _in, _out in [
                ("", ""),
                ("&#1234;", u'\u04d2'),
                ("&#x1234;", u'\u1234'),
                ("&x1234;", '&x1234;'),
                ("&name;", '&name;'),
                ("&quot;", '"'),
                ("&amp;", '&'),
                ("&lt;", "<"),
                ("&gt;", ">"),
                ("&#9733;", u'\u2605'), #black star
                ("&quot;&#&amp;&quot;", u'"&#&"'), # Try multiple
                ("&#4x0;", '&#4x0;'), # Bad char ref
        ]:
                self.assertEqual(self.target.unescape(_in), _out)

    def test_log_function_entry(self):
        self.Prefs.__getitem__.return_value = True
        self.assertEqual(self.target._log_function_entry('AFuncName'), None)
        self.Log.assert_any_call(AnyStringWith('Entering AFuncName'))
        self.Log.assert_any_call(AnyStringWith('is enabled'))

        self.Prefs.__getitem__.return_value = False
        self.assertEqual(self.target._log_function_entry('AFuncName'), None)
        self.Log.assert_any_call(AnyStringWith('Entering AFuncName'))
        self.Log.assert_any_call(AnyStringWith('is disabled'))


    def test_generate_id_from_title(self):
        for _in, _out in [
                ("short", '115104111114116'),
                ("superlongstringthatshouldntfail", '3133201520464985288'),
                ("!@#$%^&*()-=+;", '8726810728445481197'),
                ("01234567890", '4267046678020928968'),
        ]:
                self.assertEqual(self.target._generate_id_from_title(_in), _out)


    def test_find_mediafile_for_id(self):
        self.XML.ElementFromURL.return_value.xpath.return_value = [{'file':'file_value'}]
        self.String.Unquote.side_effect = lambda x: x

        self.assertEqual(self.target._find_mediafile_for_id('18879'), 'file_value')
        self.XML.ElementFromURL.assert_called_once_with(AnyStringWith('18879'))
        self.String.Unquote.assert_called_once_with('file_value')


    def test_sanitize_nfo(self):
        for _in, _out in [
                ("<tvshow>\n<a>Hi&lo&amp;w</a>\n<x/>\n</tvshow>Some garbage", '<tvshow>\n<a>Hi&amp;lo&amp;w</a>\n</tvshow>'),
        ]:
                self.assertEqual(self.target._sanitize_nfo(_in, 'tvshow'), _out)

    @patch('os.path')
    def test_find_nfo_for_file(self, mock_path):

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

    @patch('os.path')
    def test_guess_title_by_mediafile(self, mock_path):
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


    def test_parse_tvshow_nfo_text(self):
        tv_mock = MagicMock()
        tv_mock.xpath.side_effect=lambda x: [Mock(text=inputs[x])]
        self.XML.ElementFromString.return_value.xpath.return_value = [tv_mock]

        # Bestcase
        inputs = { 'id':'a', 'sorttitle':'b', 'title':'c', 'year':'1', 'extra':'a'}
        outputs = { 'id':'a', 'sorttitle':'b', 'title':'c', 'year':1, }
        self.assertEqual(self.target._parse_tvshow_nfo_text("_"), outputs)

        # bad year
        inputs = { 'id':'a', 'sorttitle':'b', 'title':'c', 'year':'nondigit', 'extra':'a'}
        outputs = { 'id':'a', 'sorttitle':'b', 'title':'c', }
        self.assertEqual(self.target._parse_tvshow_nfo_text("_"), outputs)
        #self.Log.assert_called_once_with(AnyStringWith('<year>'))

        # all bad
        inputs = {}
        outputs = {}
        self.assertEqual(self.target._parse_tvshow_nfo_text("_"), outputs)


    def test_parse_tvshow_nfo_text_parse_error(self):
        self.XML.ElementFromString.side_effect = Exception()
        self.assertEqual(self.target._parse_tvshow_nfo_text("_"), {})
        self.Log.assert_called_once_with(AnyStringWith('failed parsing'))


    def test_extract_info_for_mediafile(self):
        self.target._find_nfo_for_file = Mock(return_value = "afile.nfo")
        self.Core.storage.return_value.load.return_value = 'some text'
        self.target._sanitize_nfo = Mock(return_value = 'sanitized text')
        self.target._parse_tvshow_nfo_text = Mock(return_value = {'made':'it'})

        self.assertEqual(self.target._extract_info_for_mediafile("afile.ext"), {'made':'it'})
        self.Core.storage.load.assert_called_once_with('afile.nfo')
        self.target._sanitize_nfo.assert_called() # Make sure we are sanitizing
        self.target._parse_tvshow_nfo_text.assert_called()

        #Sad path
        self.target._find_nfo_for_file = Mock(return_value = None)
        self.assertEqual(self.target._extract_info_for_mediafile("afile.ext"), {})

    #@patch('os.path')
    #def test_update(self, mock_path):
    #    results = MagicMock()
    #    media = MagicMock()
    #    lang = None
    #    out = self.target.update(results, media, lang)
    #    self.assertEqual(out, None)


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


    @patch('os.path')
    def test_search(self, mock_path):
        results = MagicMock()
        media = MagicMock(id='an_id', title='a_title')
        lang = 'alang'
        extracted = {'id':'a_id', 'year':1970, 'title':'a_title', 'sorttitle':'a_sorttitle'}
        self.target._extract_info_for_mediafile = Mock(return_value=extracted)
        self.target._find_mediafile_for_id = Mock(side_effect="a_mediafile")

        self.assertEqual(self.target.search(results, media, lang), None)

        self.MetadataSearchResult.assert_called_once_with(score=100, lang=lang, **extracted)
        results.Append.assert_called_once()
        self.Log.assert_called_with(AnyStringWith('craped results'))

    @patch('os.path')
    def test_search_error_with_mediafile(self, mock_path):
        self.target._find_mediafile_for_id = Mock(side_effect=Exception())

        self.assertEqual(self.target.search(Mock(), Mock(), Mock()), None)

        self.Log.assert_called_with(AnyStringWith('Traceback'))

    @patch('os.path')
    def test_search_with_guessing(self, mock_path):
        results = Mock()
        self.target._find_mediafile_for_id = Mock(side_effect="a_mediafile")
        self.target._extract_info_for_mediafile = Mock(return_value={})
        self.target._guess_title_by_mediafile = Mock(return_value='a_guess')
        self.target._generate_id_from_title = Mock(return_value='12345')

        self.assertEqual(self.target.search(results, Mock(title=None, id=None), 'alang'), None)

        self.Log.assert_called_with(AnyStringWith('craped results'))
        results.Append.assert_called_once()
        self.MetadataSearchResult.assert_called_once_with(id='12345', score=100, lang='alang', sorttitle=None, title='a_guess', year=0)


if __name__ == '__main__':
    unittest.main()
