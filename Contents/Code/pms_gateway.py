

class PmsGateway(object):
    """
    An object to abstract out all interactions with the PlexMediaServer
    """
    def __init__(self, XML=None, String=None):
        self.server="http://127.0.0.1:32400"
        self.XML = XML
        self.String = String

    def _find_mediafiles_for_id(self, key):
        if 'metadata' not in key:
            key = "/library/metadata/{}".format(key)
        pageUrl = self.server + key + "/tree"
        out = []
        for mediapart in self.XML.ElementFromURL(pageUrl).xpath('//MediaPart'):
            out.append(self.String.Unquote(mediapart.get('file').encode('utf-8')))
        return out
