import logging
import os
import urllib
import urlparse

from utils import _get

class MediaFinder(object):
    nfo_file = None

    def __init__(self, Prefs):
        self.prefs = Prefs

    def _get_actor_photo(self, actor_name, actor_thumb):

        if not actor_name:
            logging.debug("No valid actor name found, defaulting")
            return actor_thumb

        actor_thumb_path = _get(self.prefs, 'athumbpath', '').rstrip('/')  # Need to avoid empty here
        if actor_thumb_path == "":
            logging.debug("A valid 'athumbpath' preference was not found, defaulting")
            return actor_thumb

        actor_thumb_engine = _get(self.prefs, 'athumblocation')
        logging.debug("Using thumb engine '{}'".format(actor_thumb_engine))
        if actor_thumb_engine == 'local':
            local_path = self._find_local_photo(actor_name, actor_thumb_path)
            if local_path:
                return local_path
        elif actor_thumb_engine == 'global':
            global_path = self._find_global_photo(actor_name, actor_thumb_path)
            if global_path:
                return global_path
        elif actor_thumb_engine == 'link':
            pass

        return actor_thumb

    def _find_local_photo(self, actor_name, actor_thumb_path):
        if not self.nfo_file:
            logging.debug('Attempted lookup of local photo failed, no nfo_dir specified')
            return None

        actor_image_filename = self._get_filename(actor_name)
        local_path = os.path.join(os.path.dirname(self.nfo_file), '.actors', actor_image_filename)
        if not os.path.isfile(local_path):
            return None

        # file:///dir/dir/ ???
        _, _, spath, _, _ = urlparse.urlsplit(actor_thumb_path) # /my/thumbs
        basepath = os.path.basename(spath)          # thumbs
        logging.debug('Searching for additional path parts after: ', basepath)
        found_pos = spath.find(basepath)            # 4
        add_pos = found_pos + len(basepath)         # 4 + 6 = 10
        add_path = os.path.dirname(spath)[add_pos:] # ''
        print(spath, basepath, found_pos, add_pos, add_path)
        if found_pos != -1 and add_path !='':
            logging.debug('Found additional path parts: ' + add_path)
        else:
            logging.debug('Found no additional path parts')
            add_path = ''
        local_path = actor_thumb_path + add_path + '/' + basepath + '/.actors/' + actor_image_filename
        if not os.path.isfile(local_path):
            return None

    def _get_filename(self, actor_name):
        return actor_name.replace(' ', '_') + '.jpg'

    def _find_global_photo(self, actor_name, actor_thumb_path):
        #TODO: Fix this up when unit testing. The code didn't originally work
        actor_image_filename = self._get_filename(actor_name)
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



