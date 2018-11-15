import logging
import urlparse
import os

class MediaFinder(object):

    def __init__(self, Prefs):
        self.prefs = Prefs

    def _get_actor_photo(self, nfo_file, actor_name, actor_thumb):

        if not actor_name:  # Without and actor name, default to thumb
            return actor_thumb

        actor_thumb_path = self.prefs['athumbpath'].rstrip('/')  # Need to avoid empty here
        if actor_thumb_path == "":
            return actor_thumb

        actor_thumb_engine = self.prefs['athumblocation']
        if actor_thumb_engine == 'local':
            local_path = self._find_local_photo(nfo_file, actor_name, actor_thumb_path)
            if local_path:
                return local_path
        elif actor_thumb_engine == 'global':
            global_path = self._find_global_photo(nfo_file, actor_name, actor_thumb_path)
            if global_path:
                return global_path
        elif actor_thumb_engine == 'link':
            pass

        return actor_thumb

    def _find_local_photo(self, nfo_file, actor_name, actor_thumb_path):
        #TODO: Fix this up when unit testing. The nfo_file is not defined
        actor_image_filename = actor_name.replace(' ', '_') + '.jpg'
        local_path = os.path.join(os.path.dirname(nfo_file), '.actors', actor_image_filename)
        if not os.path.isfile(local_path):
            return None

        # file:///dir/dir/ ???
        _, _, spath, _, _ = urlparse.urlsplit(actor_thumb_path)
        basepath = os.path.basename(spath)
        search_pos = spath.find(basepath)
        add_pos = search_pos + len(basepath)
        add_path = os.path.dirname(spath)[add_pos:]
        if search_pos != -1 and add_path !='':
            pass
        else:
            add_path = ''
        return actor_thumb_path + add_path + '/' + basepath + '/.actors/' + actor_image_filename


    def _find_global_photo(self, nfo_file, actor_name, actor_thumb_path):
        #TODO: Fix this up when unit testing. The code didn't originally work
        actor_image_filename = actor_name.replace(' ', '_') + '.jpg'
        actor_image_path = actor_thumb_path + '/' + actor_image_filename

        # Let's actually hit the URL
        scheme, netloc, spath, qs, anchor = urlparse.urlsplit(actor_image_path)
        spath = urllib.quote(spath, '/%')
        qs = urllib.quote_plus(qs, ':&=')
        actor_image_path_url = urlparse.urlunsplit((scheme, netloc, spath, qs, anchor))
        response = urllib.urlopen(actor_image_path_url).code
        if not response == 200:
            return None

        return actor_image_path



