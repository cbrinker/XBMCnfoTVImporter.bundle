import unittest

from mock import patch, MagicMock

class PatchMixin(object):
    """
    Testing utility mixin that provides methods to patch objects so that they
    will get unpatched automatically.
    """

    def patch(self, *args, **kwargs):
        patcher = patch(*args, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def patch_object(self, *args, **kwargs):
        patcher = patch.object(*args, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def patch_dict(self, *args, **kwargs):
        patcher = patch.dict(*args, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

class AnyStringWith(str):
    def __eq__(self, other):
        return self in other

def ArgShouldContain(x):
    def wrapper(arg):
        assert str(x) in arg, "'%s' does not contain '%s'" % (arg, x)
    return wrapper

class MyPlexTester(PatchMixin, unittest.TestCase):
    pass

def PrepareForPlexTest():
    """Going to mock out all of the things a
    plex module thinks automatically exist"""

    for patch_name, patch_obj in [
        ('__builtin__.Agent', MagicMock(TV_Shows=object)),
        ('__builtin__.Core', MagicMock()),
        ('__builtin__.Dict', MagicMock()),
        ('__builtin__.Locale', MagicMock()),
        ('__builtin__.Log', MagicMock()),
        ('__builtin__.MetadataSearchResult', MagicMock()),
        ('__builtin__.Platform', MagicMock()),
        ('__builtin__.Prefs', MagicMock()),
        ('__builtin__.String', MagicMock()),
        ('__builtin__.XML', MagicMock()),
        ('Code.parallelize', MagicMock()),
    ]:
        name = patch_name.split(".")[-1]  # Hacky way to get names for reference
        patcher = patch(patch_name, patch_obj, create=True)
        globals()[name] = patcher.start()  # Inject into calling module
