import unittest

from mock import Mock, MagicMock, patch

from test import MyPlexTester, PrepareForPlexTest, AnyStringWith, ArgShouldContain
PrepareForPlexTest()
from Code import media_finder

class TestMediaFinder(MyPlexTester):
    def setUp(self):
        self.target = media_finder.MediaFinder(object)

    def test_sanity(self):
        self.assertTrue(True)

    def test_find_local_photo(self):
        #TODO test here
        #mock_path = self.patch('os.path')
        #mock_path.basename = Mock(side_effect = lambda x: x.split("/")[-1])

        #for _file, _name, _path, _out in [
        #    ('', '','',''),
        #]:
        #    self.assertEqual(self.target._find_local_photo(_file, _name, _path), _out)
        self.assertEqual(1,1)

