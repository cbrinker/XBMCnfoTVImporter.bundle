import unittest

from mock import Mock, MagicMock, patch

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

if __name__ == '__main__':
    unittest.main()
