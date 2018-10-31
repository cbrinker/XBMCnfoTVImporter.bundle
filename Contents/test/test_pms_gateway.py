import unittest

from mock import Mock, MagicMock, patch

class AnyStringWith(str):
    def __eq__(self, other):
        return self in other

class TestPmsGateway(unittest.TestCase):
    def setUp(self):
        for name in ['Locale', 'Agent']:
            patcher = patch("__builtin__."+name, create=True)
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)

    def test_find_mediafile_for_id(self):
        from Code.pms_gateway import PmsGateway as target

        XML = Mock()
        XML.ElementFromURL.return_value.xpath.return_value = [{'file':'file_value'}]
        String = Mock()
        String.Unquote.side_effect = lambda x: x

        t = target(XML, String)

        self.assertEqual(t._find_mediafiles_for_id('18879'), ['file_value'])
        XML.ElementFromURL.assert_called_once_with(AnyStringWith('18879'))
        String.Unquote.assert_called_once_with('file_value')
