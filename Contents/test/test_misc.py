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


    @patch('Code._parse_dt', side_effect=lambda x,y: x)
    def test_get_premier(self, mock_utils):
        for _in, _out in [
            ("<x><aired>XXX</aired></x>", {'originally_available_at':'XXX'}),
            ("<x><premiered>XXX</premiered></x>", {'originally_available_at':'XXX'}),
            ("<x><dateadded>XXX</dateadded></x>", {'originally_available_at':'XXX'}),
            ("<x><aired>XXX</aired><premiered>YYY</premiered><dateadded>ZZZ</dateadded></x>", {'originally_available_at':'XXX'}),
        ]:
            xml = ET.fromstring(_in)
            self.assertEqual(self.target._get_premier(xml), _out)

    def test_get_directors(self):
        for _in, _out in [
            ("<x></x>", {}),
            ("<x><director>d1</director></x>", {'directors': ['d1']}),
            ("<x><director>d3/d2 /d1</director></x>", {'directors':['d1','d2','d3']}),
            ("<x><director>d3/d3</director></x>", {'directors':['d3']}),
        ]:
            xml = ET.fromstring(_in)
            self.assertEqual(self.target._get_directors(xml), _out)

    def test_get_collections_from_set(self):
        for _in, _out in [
            ("<x></x>", []),
            ("<x><set><name>a_name</name></set></x>", ['a_name']),
            ("<x><set>a_name</set></x>", ['a_name']),
        ]:
            xml = ET.fromstring(_in)
            self.assertEqual(self.target._get_collections_from_set(xml), _out)

    def test_get_collections_from_tags(self):
        for _in, _out in [
            ("<x></x>", []),
            ("<x><tag>single</tag></x>", ['single']),
            ("<x><tag>multi</tag><tag>tags</tag></x>", ['multi','tags']),
            ("<x><tag>mul/ti</tag><tag>ta/gs</tag></x>", ['mul','ti','ta','gs']),
        ]:
            xml = ET.fromstring(_in)
            self.assertEqual(self.target._get_collections_from_tags(xml), _out)

    def test_get_duration_ms(self):
        for _in, _out in [
            ("<x></x>", {}),
            ("<x><fileinfo><streamdetails><video><durationinseconds>123</durationinseconds></video></streamdetails></fileinfo></x>", {'duration': 123000}),
            ("<x><runtime>Garbage</runtime></x>", {}),
            ("<x><runtime>01X</runtime></x>", {'duration': 3600000}),
            ("<x><runtime>6</runtime></x>", {'duration': 360000}),
        ]:
            xml = ET.fromstring(_in)
            self.assertEqual(self.target._get_duration_ms(xml), _out)

    def test_get_credites(self):
        for _in, _out in [
            ("<x></x>", {}),
            ("<x><credits>c1</credits></x>", {'writers': ['c1']}),
            ("<x><credits>c1/c2</credits></x>", {'writers': ['c1','c2']}),
            ("<x><credits>c1</credits><credits>c2</credits></x>", {'writers': ['c1','c2']}),
            ("<x><credits>(Producer)p1</credits></x>", {'producers': ['p1']}),
            ("<x><credits>p1(Producer)</credits></x>", {'producers': ['p1']}),
            ("<x><credits>(Writer)w1</credits></x>", {'writers': ['w1']}),
            ("<x><credits>w1(Writer)</credits></x>", {'writers': ['w1']}),
            ("<x><credits>(Guest Star)gs1</credits></x>", {'guest_stars': ['gs1']}),
            ("<x><credits>gs1(Guest Star)</credits></x>", {'guest_stars': ['gs1']}),
            ("<x><credits>gs2 (Guest Star)/(Producer)p2</credits></x>", {'producers': ['p2'],'guest_stars':['gs2']}),
        ]:
            xml = ET.fromstring(_in)
            self.assertEqual(self.target._get_credits(xml), _out)

    def test_get_ratings(self):
        for _in, _out in [
            ("<x></x>", {}),
            ("<x><rating><value>8.8</value></rating><rating><value>9.9</value></rating></x>", {'rating': 8.8}),
            ("<x><rating><value>8</value></rating></x>", {'rating': 8.0}),
            ("<x><rating><value>1.54</value></rating></x>", {'rating': 1.5}),
            ("<x><rating><value>1,54</value></rating></x>", {'rating': 1.5}),
            ("<x><rating><value>0.2</value></rating></x>", {'rating': 0.2}),
        ]:
            xml = ET.fromstring(_in)
            self.assertEqual(self.target._get_ratings(xml), _out)

    def test_debug_logging(self):
        msg = "A test message"
        self.Prefs.__getitem__.return_value = 1
        self.target.DLog(msg)
        self.Prefs.__getitem__.assert_called_with('debug')
        self.Log.assert_called_with(msg)


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





    @patch('os.path')
    def test_find_nfo_for_file_tvshow(self, mock_path):
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
    def test_find_nfo_for_file_episode(self, mock_path):
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


    @patch('Code._sanitize_nfo')
    def test_extract_info_for_mediafile(self, _sanitize_nfo):
        self.target._find_nfo_for_file = Mock(return_value = "afile.nfo")
        self.Core.storage.return_value.load.return_value = 'some text'
        self.target._parse_tvshow_nfo_text = Mock(return_value = {'made':'it'})

        self.assertEqual(self.target._extract_info_for_mediafile("afile.ext"), {'made':'it','nfo_file':'afile.nfo'})
        self.Core.storage.load.assert_called_once_with('afile.nfo')
        _sanitize_nfo.assert_called() # Make sure we are sanitizing
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

        for name in ['Log', 'Locale', 'Prefs', 'Agent', 'Platform', 'MetadataSearchResult', 'XML', 'String']:
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
        
        pms = Mock()
        pms._find_mediafiles_for_id = Mock(side_effect="a_mediafile")
        self.target.pms = pms

        self.assertEqual(self.target.search(results, media, lang), None)

        self.MetadataSearchResult.assert_called_once_with(score=100, lang=lang, **extracted)
        results.Append.assert_called_once()
        self.Log.assert_called_with(AnyStringWith('craped results'))

    @patch('os.path')
    def test_search_error_with_mediafile(self, mock_path):
        pms = Mock()
        pms._find_mediafiles_for_id = Mock(side_effect=Exception())
        self.target.pms = pms
        #self.pms._find_mediafiles_for_id = Mock(side_effect=Exception())
        #self.target._find_mediafiles_for_id = Mock(side_effect=Exception())

        self.assertEqual(self.target.search(Mock(), Mock(), Mock()), None)

        self.Log.assert_called_with(AnyStringWith('Traceback'))

    @patch('os.path')
    def test_search_with_guessing(self, mock_path):
        results = Mock()
        pms = Mock()
        pms._find_mediafiles_for_id = Mock(side_effect="a_mediafile")
        self.target.pms = pms
        #self.target._find_mediafiles_for_id = Mock(side_effect="a_mediafile")
        self.target._extract_info_for_mediafile = Mock(return_value={})
        self.target._guess_title_by_mediafile = Mock(return_value='a_guess')
        self.target._generate_id_from_title = Mock(return_value='12345')

        self.assertEqual(self.target.search(results, Mock(title=None, id=None), 'alang'), None)

        self.Log.assert_called_with(AnyStringWith('craped results'))
        results.Append.assert_called_once()
        self.MetadataSearchResult.assert_called_once_with(id='12345', score=100, lang='alang', sorttitle=None, title='a_guess', year=0)

class TestMultipleEpisode(unittest.TestCase):
    def setUp(self):

        for name in ['Log', 'Locale', 'Prefs', 'Agent', 'Platform', 'MetadataSearchResult', 'XML', 'String']:
                patcher = patch("__builtin__."+name, create=True)
                setattr(self, name, patcher.start())
                self.addCleanup(patcher.stop)
        self.Agent.TV_Shows = object

        patch('Code.parallelize', create=True).start()
        import Code
        self.target = Code.xbmcnfotv()

    @patch('os.path')
    def test_multiple_episodes(self, mock_path):
        self.Prefs.__getitem__.side_effect=lambda x: _prefs[x]
        self.target.RemoveEmptyTags = Mock(side_effect=lambda x:x)
        self.XML.ElementFromString.side_effect=lambda x: ET.fromstring(x)
        _prefs = {
            'multEpisodePlexPatch': True,
            'multEpisodeTitleSeparator': ';',
            'debug': True,
        }

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

class TestParseEpisode(unittest.TestCase):
    def setUp(self):

        for name in ['Log', 'Locale', 'Prefs', 'Agent', 'Platform', 'MetadataSearchResult', 'XML', 'String']:
                patcher = patch("__builtin__."+name, create=True)
                setattr(self, name, patcher.start())
                self.addCleanup(patcher.stop)
        self.Agent.TV_Shows = object

        patch('Code.parallelize', create=True).start()
        import Code
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
