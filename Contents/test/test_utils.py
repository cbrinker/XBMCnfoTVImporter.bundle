import datetime
import unittest

from mock import Mock, MagicMock, patch
from lxml import etree as ET

class TestUtilities(unittest.TestCase):
    def setUp(self):
        for name in ['Locale', 'Agent']:
            patcher = patch("__builtin__."+name, create=True)
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)

    def test_time_convert(self):
        import Code.utils as target
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
                self.assertEqual(target.time_convert(_in), _out)

    def test_get(self):
        import Code.utils as target
        self.assertEqual(target._get({}, 'x'), None)
        self.assertEqual(target._get({'x':'y'}, 'x'), 'y')
        self.assertEqual(target._get({'x':None}, 'x', 'something'), 'something')

    def test_check_file_paths_no_input(self):
        import Code.utils as target
        out = target.check_file_paths([], 'a_type')
        self.assertEqual(out, None)

    @patch('os.path')
    def test_check_file_paths_success(self, mock_path):
        import Code.utils as target
        mock_path.isdir.return_value = False
        mock_path.exists.return_value = True
        out = target.check_file_paths(['1stfound','y'], 'a_type')
        self.assertEqual(out, '1stfound')
        mock_path.exists.assert_called_once_with('1stfound')

    @patch('os.path')
    def test_check_file_paths_skip_dirs(self, mock_path):
        import Code.utils as target
        mock_path.isdir.return_value = True
        mock_path.exists.return_value = True
        out = target.check_file_paths(['1stfound','y'], 'a_type')
        self.assertEqual(out, None)

    @patch('os.path')
    def test_check_file_paths_skip_non_files(self, mock_path):
        import Code.utils as target
        mock_path.isdir.return_value = False
        mock_path.exists.return_value = False
        out = target.check_file_paths(['1stfound','y'], 'a_type')
        self.assertEqual(out, None)


    def test_remove_empty_tags(self):
        import Code.utils as target

        for _in, _out in [
            ("<x></x>", "<x/>"),
            ("<x><a>Hello</a><b></b><c> </c></x>", "<x><a>Hello</a></x>"),
        ]:
            xml_in = ET.fromstring(_in)
            val_out = target.remove_empty_tags(xml_in)
            val_out = ET.tostring(val_out)
            self.assertEqual(val_out, _out)

    def test_unescape(self):
        import Code.utils as target
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
                self.assertEqual(target.unescape(_in), _out)

    def test_parse_dt(self):
        import Code.utils as target
        expected_dt = datetime.datetime(2018, 8, 11, 0, 0)
        for _in, _out in [
            (("08.11.2018", False), expected_dt),
            (("08/11/2018", False), expected_dt),
            (("Garbage",    False), None),
            (("11.08.2018", True),  expected_dt),
            (("11/08/2018", True),  expected_dt),
            (("Garbage",    True),  None),
        ]:
            self.assertEqual(target._parse_dt(*_in), _out)

    def test_sanitize_nfo(self):
        import Code.utils as target
        for _in, _out in [
                ("<tvshow>\n<a>Hi&lo&amp;w</a>\n<x/>\n</tvshow>Some garbage", '<tvshow>\n<a>Hi&amp;lo&amp;w</a>\n</tvshow>'),
                ("<tvshow>\n<a>Hi&lo&amp;w</a>\n<x/>\n</tvshow>", '<tvshow>\n<a>Hi&amp;lo&amp;w</a>\n</tvshow>'),
                ("<tvshow>X</tvshow>\n<tvshow>Y</tvshow>XXXX", '<tvshow>X</tvshow>\n<tvshow>Y</tvshow>'),
                ("<tvshow>X</tvshow>\n<tvshow>Y</tvshow>", '<tvshow>X</tvshow>\n<tvshow>Y</tvshow>'),
                ("<tvshow/>", '<tvshow/>'),
        ]:
                self.assertEqual(target._sanitize_nfo(_in, 'tvshow'), _out)

        for _in, _out in [
                ("before<x>during</x><x/>after", 'beforeduringafter'),
        ]:
                self.assertEqual(target._sanitize_nfo(_in, 'y', ['x']), _out)

if __name__ == '__main__':
    unittest.main()
