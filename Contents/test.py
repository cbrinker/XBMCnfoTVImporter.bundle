import unittest
from mock import MagicMock, patch

from lxml import etree as ET

class AnyStringWith(str):
    def __eq__(self, other):
        return self in other
def arg_should_contain(x):
    def wrapper(arg):
        assert str(x) in arg, "'%s' does not contain '%s'" % (arg, x)
    return wrapper

#print(mock.call_args_list)

class MyTest(unittest.TestCase):
    def setUp(self):

	for name in ['Log', 'Locale', 'Prefs', 'Agent', 'Platform', 'XML', 'String', 'Core', 'MetadataSearchResult', 'Dict']:
		patcher = patch("__builtin__."+name, create=True)
		setattr(self, name, patcher.start())
		self.addCleanup(patcher.stop)
	self.Agent.TV_Shows = object

	patch('Code.parallelize', create=True).start()
	import Code
	#Code.PERCENT_RATINGS = []
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
	mock_path.isdir.return_value = True
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
		("&x1234;", '&x1234;'),
		("&name;", '&name;'),
		("&quot;", '"'),
		("&amp;", '&'),
		("&lt;", "<"),
		("&gt;", ">"),
		("&#9733;", u'\u2605'), #black star
		("&quot;&#&amp;&quot;", u'"&#&"'), # Try multiple
	]:
		self.assertEqual(self.target.unescape(_in), _out)

    def test_log_function_entry(self):
	self.assertEqual(self.target._log_function_entry('AFuncName'), None)
	self.Log.assert_any_call(AnyStringWith('Entering AFuncName'))
	
    @patch('os.path')
    def test_search(self, mock_path):
	results = MagicMock()
	media = MagicMock()
	lang = None

	self.Core.storage.load.return_value = "A String"

	out = self.target.search(results, media, lang)
	self.assertEqual(out, None)

    @patch('os.path')
    def test_update(self, mock_path):
	results = MagicMock()
	media = MagicMock()
	lang = None

	self.Core.storage.load.return_value = "A String"

	out = self.target.update(results, media, lang)
	self.assertEqual(out, None)



if __name__ == '__main__':
    unittest.main()
