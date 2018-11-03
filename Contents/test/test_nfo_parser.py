import unittest

from mock import Mock, MagicMock, patch

from lxml import etree as ET

class AnyStringWith(str):
    def __eq__(self, other):
        return self in other


class TestNfoParser(unittest.TestCase):
    def setUp(self):
        for name in ['Locale', 'Agent']:
            patcher = patch("__builtin__."+name, create=True)
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)
        from Code.nfo_parser import NfoParser as uut
        self.target = uut(Mock())

    @patch('Code.nfo_parser._parse_dt', side_effect=lambda x,y:x)
    def test_get_premier(self, mock_parse_dt):
        for _in, _out in [
            ("<x><aired>XXX</aired></x>", {'originally_available_at':'XXX'}),
            ("<x><premiered>XXX</premiered></x>", {'originally_available_at':'XXX'}),
            ("<x><dateadded>XXX</dateadded></x>", {'originally_available_at':'XXX'}),
            ("<x><aired>XXX</aired><premiered>YYY</premiered><dateadded>ZZZ</dateadded></x>", {'originally_available_at':'XXX'}),
        ]:
            xml = ET.fromstring(_in)
            self.assertEqual(self.target._get_premier(xml), _out)
        self.assertEqual(self.target._get_premier(None), {}) # Don't raise for bad input

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
        self.assertEqual(self.target._get_ratings(None), {}) # Don't raise for bad input

    def test_parse_rating(self):
        for _in, _out in [
            #Best cases
            ("G", "G"),
            ("MA", "MA"),
            ("NC-17", "NC-17"),
            ("PG", "PG"),
            ("PG-13", "PG-13"),
            ("FUT3-2/4+0.1", "FUT3-2/4+0.1"),
            #Edge cases
            ("", "NR"), # Empty input
            ("pg", "pg"), # Case insensitive
            ("Rated PG", "PG"), # Optional prepend
        ]:
            self.assertEqual(self.target._parse_rating(_in), _out)

        self.assertEqual(self.target._parse_rating(None), 'NR') # Don't raise for bad input

    @patch('Code.nfo_parser.time_convert', side_effect=lambda x:"converted(%s)"%x)
    def test_get_duration_ms(self, mock_time_convert):
        for _in, _out in [
            ("<x></x>", {}),
            ("<x><fileinfo><streamdetails><video><durationinseconds>123</durationinseconds></video></streamdetails></fileinfo></x>", {'duration': 123000}),
            ("<x><runtime>Garbage</runtime></x>", {}),
            ("<x><runtime>01X</runtime></x>", {'duration': 'converted(1)'}),
            ("<x><runtime>6</runtime></x>", {'duration': 'converted(6)'}),
        ]:
            xml = ET.fromstring(_in)
            self.assertEqual(self.target._get_duration_ms(xml), _out)

        self.assertEqual(self.target._get_duration_ms(None), {}) # Don't raise for bad input

    def test_get_directors(self):
        for _in, _out in [
            ("<x></x>", {}),
            ("<x><director>d1</director></x>", {'directors': ['d1']}),
            ("<x><director>d3/d2 /d1</director></x>", {'directors':['d1','d2','d3']}),
            ("<x><director>d3/d3</director></x>", {'directors':['d3']}),
        ]:
            xml = ET.fromstring(_in)
            self.assertEqual(self.target._get_directors(xml), _out)

        self.assertEqual(self.target._get_directors(None), {}) # Don't raise for bad input

    def test_get_credits(self):
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
        self.assertEqual(self.target._get_credits(None), {}) # Don't raise for bad input

    def test_get_alt_ratings(self):
        SINGLE_RATING="""<x><ratings>
            <rating moviedb="p1">a</rating>
        </ratings></x>"""
        MULTI_RATING="""<x><ratings>
            <rating moviedb="p1">a</rating>
            <rating moviedb="rt">1,1</rating>
        </ratings></x>"""
        BAD_RATING="""<x><ratings>
            <rating>a</rating>
        </ratings></x>"""
        for _prefs, _in, _out in [
            # Feature undefined
            ({}, None, {}),
            # Feature off
            ({'altratings': False}, None, {}),
            ({'altratings': False}, "<x></x>", {}),
            # Feature on, default (no filtering)
            ({'altratings': True}, '<x></x>', {}),
            ({'altratings': True}, SINGLE_RATING, {'alt_ratings':[('p1','a')]}),
            ({'altratings': True}, MULTI_RATING,  {'alt_ratings':[('p1','a'),('rt','1.1%')]}),
            ({'altratings': True}, BAD_RATING,    {}),
            # Feature on, filtering providers
            ({'altratings': True, 'ratings':['p1']}, MULTI_RATING, {'alt_ratings':[('p1','a')]}),
        ]:
            if isinstance(_in, basestring):
                _in = ET.fromstring(_in)
            self.target.prefs=_prefs
            self.assertEqual(self.target._get_alt_ratings(_in), _out)


