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
        from Code.nfo_parser import NfoParser as target

        t = target()
