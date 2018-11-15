import unittest

from mock import Mock, MagicMock, patch

from test import MyPlexTester, PrepareForPlexTest, AnyStringWith, ArgShouldContain

PrepareForPlexTest()
from Code import media_finder

SENTINEL="SeNtInEl"

class TestGetActorPhoto(MyPlexTester):

    def test_nfo_file_behavior(self):
        target = media_finder.MediaFinder({})
        self.assertEqual(target.nfo_file, None)
        target.nfo_file = SENTINEL
        self.assertEqual(target.nfo_file, SENTINEL)

    def test_get_actor_photo(self):

        P_LOC_LOCAL   = [('athumblocation','local')]
        P_LOC_GLOBAL  = [('athumblocation','global')]
        P_LOC_OTHER   = [('athumblocation','link')]
        P_THUMB_GOOD  = [('athumbpath', '/some/where/')]
        for _prefs, _name, _default, _out in [
            ({},                              '', SENTINEL, SENTINEL),
            ({},                              'A Person', SENTINEL, SENTINEL),
            (dict(P_THUMB_GOOD),              'A Person', SENTINEL, SENTINEL),
            (dict(P_THUMB_GOOD+P_LOC_OTHER),  'A Person', SENTINEL, SENTINEL),
            (dict(P_THUMB_GOOD+P_LOC_LOCAL),  'A Person', SENTINEL, 'local_path'),
            (dict(P_THUMB_GOOD+P_LOC_GLOBAL), 'A Person', SENTINEL, 'global_path'),
        ]:
            target = media_finder.MediaFinder(_prefs)
            target._find_local_photo = Mock(return_value='local_path')
            target._find_global_photo = Mock(return_value='global_path')
            self.assertEqual(target._get_actor_photo(_name, _default), _out)

    def test_find_local_photo(self):
        target = media_finder.MediaFinder(object)
        target.nfo_file = "/a/path/somewhere.nfo"

        mock_path = self.patch('os.path')
        mock_path.join     = Mock(side_effect = lambda *args: "/".join(args))
        mock_path.dirname  = Mock(side_effect = lambda x: x.rsplit("/",1)[0])
        mock_path.basename = Mock(side_effect = lambda x: x.rsplit("/",1)[-1])

        mock_path.isfile = Mock(return_value = False)
        self.assertEqual(target._find_local_photo('',''), None)

        mock_path.isfile = Mock(return_value = True)
        #TODO Need to clean this up
        self.assertEqual(target._find_local_photo('J Smith','/actor/thumbs'), '/actor/thumbs/thumbs/.actors/J_Smith.jpg')
