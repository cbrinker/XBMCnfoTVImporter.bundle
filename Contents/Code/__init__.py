# XBMCnfoTVImporter
# spec'd from: http://wiki.xbmc.org/index.php?title=Import_-_Export_Library#Video_nfo_Files
#
# Original code author: Harley Hooligan
# Modified by Guillaume Boudreau
# Eden and Frodo compatibility added by Jorge Amigo
# Cleanup and some extensions by SlrG
# Logo by CrazyRabbit
# Multi episode patch by random.server
# Fix of whole episodes getting cached as thumbnails by Em31Et
# Krypton ratings fix by F4RHaD
# Season banner and season art support by Christian
#
import os, re, time, datetime, platform, traceback, glob, re, htmlentitydefs
from dateutil.parser import parse
import urllib
import urlparse

PERCENT_RATINGS = {
  'rottentomatoes','rotten tomatoes','rt','flixster'
}

class xbmcnfotv(Agent.TV_Shows):
    name = 'XBMCnfoTVImporter'
    ver = '1.1-93-gc3e9112-220'
    primary_provider = True
    languages = [Locale.Language.NoLanguage]
    accepts_from = ['com.plexapp.agents.localmedia','com.plexapp.agents.opensubtitles','com.plexapp.agents.podnapisi','com.plexapp.agents.plexthememusic','com.plexapp.agents.subzero']
    contributes_to = ['com.plexapp.agents.thetvdb']

##### helper functions #####
    def DLog (self, LogMessage):
        if Prefs['debug']:
            Log (LogMessage)

    def time_convert (self, duration):
        if (duration <= 2):
            duration = duration * 60 * 60 * 1000 #h to ms
        elif (duration <= 120):
            duration = duration * 60 * 1000 #m to ms
        elif (duration <= 7200):
            duration = duration * 1000 #s to ms
        return duration

    def checkFilePaths(self, pathfns, ftype):
        for pathfn in pathfns:
            if os.path.isdir(pathfn): continue
            self.DLog("Trying " + pathfn)
            if not os.path.exists(pathfn):
                continue
            else:
                Log("Found " + ftype + " file " + pathfn)
                return pathfn
        else:
            Log("No " + ftype + " file found! Aborting!")

    def RemoveEmptyTags(self, xmltags):
        for xmltag in xmltags.iter("*"):
            if len(xmltag):
                continue
            if not (xmltag.text and xmltag.text.strip()):
                #self.DLog("Removing empty XMLTag: " + xmltag.tag)
                xmltag.getparent().remove(xmltag)
        return xmltags

    ##
    # Removes HTML or XML character references and entities from a text string.
    # Copyright: http://effbot.org/zone/re-sub.htm October 28, 2006 | Fredrik Lundh
    # @param text The HTML (or XML) source text.
    # @return The plain text, as a Unicode string, if necessary.

    def unescape(self, text):
        def fixup(m):
            text = m.group(0)
            if text[:2] == "&#":
                # character reference
                try:
                    if text[:3] == "&#x":
                        return unichr(int(text[3:-1], 16))
                    else:
                        return unichr(int(text[2:-1]))
                except ValueError:
                    pass
            else:
                # named entity
                try:
                    text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
                except KeyError:
                    pass
            return text # leave as is
        return re.sub("&#?\w+;", fixup, text)

    def _log_function_entry(self, func_name):
        self.DLog("++++++++++++++++++++++++")
        self.DLog("Entering "+func_name+" function")
        self.DLog("++++++++++++++++++++++++")
        Log ("" + self.name + " Version: " + self.ver)
        self.DLog("Plex Server Version: " + Platform.ServerVersion)

        if Prefs['debug']:
            Log ('Agents debug logging is enabled!')
        else:
            Log ('Agents debug logging is disabled!')


    def _find_mediafile_for_id(self, id):
        pageUrl = "http://127.0.0.1:32400/library/metadata/" + id + "/tree"
        first_mediapart = XML.ElementFromURL(pageUrl).xpath('//MediaPart')[0]
        first_mediapart_file = String.Unquote(first_mediapart.get('file').encode('utf-8'))

        self.DLog("Found mediapart file: '%s'" % first_mediapart_file)
        return first_mediapart_file


    def _find_nfo_for_file(self, filename, nfo_name='tvshow.nfo'):
        def _dir_at_depth(path, depth):
            for i in xrange(depth):
                path = os.path.dirname(path)
            return path

        Log("Searching for a '%s' file for '%s'" % (nfo_name, filename))
        parent_search_depths = [1, 0, 2, 3]
        for parent_search_depth in parent_search_depths:
            candidate_dir = _dir_at_depth(filename, parent_search_depth)
            candidate_path = os.path.join(candidate_dir, nfo_name)
            self.DLog("Searching for file at '%s'" % candidate_path)
            if os.path.exists(candidate_path):
                Log("Found file at '%s'!" % candidate_path)
                return candidate_path
        Log("No '%s' file found for '%s'" % (nfo_name, filename))
        return None


    def _sanitize_nfo(self, nfo_text, root_tag):
        # work around failing XML parses for things with &'s in them. This may need to go farther than just &'s....
        nfo_text = re.sub(r'&(?![A-Za-z]+[0-9]*;|#[0-9]+;|#x[0-9a-fA-F]+;)', r'&amp;', nfo_text)
        # remove empty xml tags from nfo

        #self.DLog('Removing empty XML tags from tvshows nfo...')
        nfo_text = re.sub(r'^\s*<.*/>[\r\n]+', '', nfo_text, flags = re.MULTILINE)

        end_root_tag = "</%s>" % root_tag
        if nfo_text.count(end_root_tag) > 0:
            # Remove URLs (or other stuff) at the end of the XML file
            nfo_text = '%s%s' % (nfo_text.split(end_root_tag)[0], end_root_tag)
        return nfo_text


    def _guess_title_by_mediafile(self, mediafile):
        out = None
        filename = os.path.basename(mediafile)
        self.DLog("Guessing a title based on mediafile '%s'" % filename)

        matches = re.compile('(.+?)[ .]S(\d\d?)E(\d\d?).*?\Z').match(filename) 
        if matches:
            out = matches.group(1).replace(".", " ")

        self.DLog("Title guess of: '%s'" % out)
        return out

    def _parse_rating(self, text):
        out = 'NR'
        matches = re.compile(r'(?:Rated\s)?(?P<mpaa>[A-z0-9-+/.]+(?:\s[0-9]+[A-z]?)?)?').match(text)
        if matches.group('mpaa'):
            out = matches.group('mpaa')
        return out

    def _parse_dt(self, s):
        if Prefs['dayfirst']:
            return parse(s, dayfirst=True)
        else:
            return parse(s)

    def _get_premier(self, nfo_xml):
        out = {}
        for key in ['aired', 'premiered', 'dateadded']:
            try:
                s = nfo_xml.xpath(key)[0].text
                if s:
                    out['originally_available_at'] = self._parse_dt(s)
                    break
            except:
                pass
        return out

    def _get_ratings(self, nfo_xml):
        out = {}

        rating = 0.0
        try:
            rating = nfo_xml.xpath("rating")[0].text.replace(',', '.')
            rating = round(float(rating), 1)
            out['rating'] = rating
        except:
            pass
        return out


    def _get_alt_ratings(self, nfo_xml):
        #{'atr_ratings': [(provider,rating)]}

        if not Prefs['altratings']:
            return {}

        allowed_ratings = Prefs['ratings']
        if not allowed_ratings:
            allowed_ratings = "ALL"

        additional_ratings = []
        try:
            additional_ratings = nfo_xml.xpath('ratings')
            if not additional_ratings:
                return {}  # Not Found in xml, abort
        except:
            pass

        alt_ratings = []
        for addratingXML in additional_ratings:
            for addrating in addratingXML:
                try:
                    rating_provider = str(addrating.attrib['moviedb'])
                    value = str(addrating.text.replace(',', '.'))
                    if rating_provider.lower() in PERCENT_RATINGS:
                        value = value + "%"
                    if allowed_ratings == "ALL" or rating_provider in allowed_ratings:
                        alt_ratings.append((rating_provider, value))
                except:
                    self.DLog("Skipping additional rating without moviedb attribute!")
        if len(alt_ratings):
            return {'alt_ratings': alt_ratings}
        else:
            return {}

    def _get_duration(self, nfo_xml):
        out = {}
        for key in ['durationinseconds', 'runtime']:
            try:
                v = nfo_xml.xpath(key)[0].text
                v = int(re.compile('^([0-9]+)').findall(v)[0])
                if key == 'durationinseconds':
                    v *= 1000
                elif key == 'runtime':
                    v = self.time_convert(self, v)
                if v:
                    out['duration'] = v
                    break
            except:
                pass
        return out

    def _build_summary(self, data):
        # CONSTRUCT A SUMMARY
        out = []
        if Prefs['statusinsummary']:
            out.append('Status: {}'.format(data['status']))

        out.append(data['plot'])

        alt_ratings = " | ".join("{}: {}".format(source, rating) for source, rating in data['alt_ratings'])

        """
        if Prefs['ratingspos'] == "front":
            if Prefs['preserverating']:
                metadata.summary = alt_ratings + self.unescape(" &#9733;\n\n") + metadata.summary
            else:
                metadata.summary = self.unescape("&#9733; ") + alt_ratings + self.unescape(" &#9733;\n\n") + metadata.summary
        else:
            metadata.summary = metadata.summary + self.unescape("\n\n&#9733; ") + alt_ratings + self.unescape(" &#9733;")
        if Prefs['preserverating']:
            tmp = self.unescape("{}{:.1f}{}".format(Prefs['beforerating'], data['rating'], Prefs['afterrating']))
            out.insert(0, tmp)
        """
        return " | ".join(out)

    def _get_collections_from_set(self, nfo_xml):
        out = []
        try:
            set_xml = nfo_xml.xpath('set')[0]
            has_names = set_xml.xpath('name')
            if len(has_names):  # Found enhanced set tag name
                out.append(has_names[0].text)
            else:
                out.append(set_xml.text)
        except:
            pass
        return out

    def _get_collections_from_tags(self, nfo_xml):
        out = []
        try:
            for tag_xml in nfo_xml.xpath('tag'):
                tags = [x.strip() for x in tag_xml.text.split('/')]
                for tag in tags:
                    out.append(tag)
        except:
            pass
        return out


    def _find_local_photo(self, actor_name, actor_thumb_path):
        #TODO: Fix this up when unit testing. The code didn't originally work
        actor_image_filename = actor_name.replace(' ', '_') + '.jpg'
        local_path = os.path.join(actor_thumb_path, '.actors', actor_image_filename)
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


    def _find_global_photo(self, actor_name, actor_thumb_path):
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


    def _get_actor_photo(self, actor_name, actor_thumb):

        if not actor_name:  # Without and actor name, default to thumb
            return actor_thumb

        actor_thumb_path = Prefs['athumbpath'].rstrip('/')  # Need to avoid empty here
        if actor_thumb_path == "":
            return actor_thumb

        actor_thumb_engine = Prefs['athumblocation']
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


    def _get_actors(self, nfo_xml):
        try:
            actor_nodes = nfo_xml.xpath('actor')
        except:
            return {}

        seen_roles = []
        actors = []
        for n, actor in enumerate(actor_nodes):
            actor = {  # Defaulting to unknown
                'name': 'Unknown Actor {}'.format(n+1),
                'role': 'Unknown Role {}'.format(n+1),
            }
            try:
                actor['name'] = actor.xpath('name')[0].text.strip()
            except:
                pass
            try:
                role = actor.xpath('role')[0].text.strip()
                role_seen_count = seen_roles.count(role)
                if role_seen_count:
                    actor['role'] = '{} {}'.format(role, role_seen_count+1)
                else:
                    actor['role'] = role
                seen_roles.append(role)
            except:
                pass
            try:
                actor['thumb'] = actor.xpath('thumb')[0].text.strip()
            except:
                pass
            actor['photo'] = self._get_actor_photo(actor['name'], actor.get('thumb')) # empty str, or content
            actors.append(actor)
        return {'actors': actors}


    def _parse_tvshow_nfo_text(self, nfo_text):
        out = {}
        try:
            nfo_xml = XML.ElementFromString(nfo_text).xpath('//tvshow')[0]
        except:
            Log('ERROR: failed parsing tvshow XML in nfo file')
            return out

        nfo_xml = self.RemoveEmptyTags(nfo_xml)

        for xml_key, out_key, cast in [
            ('id','id', None),
            ('sorttitle','sorttitle', None),
            ('title','title', None),
            ('studio','studio', None),
            ('originaltitle','original_title', None),
            ('year','year', int),
            ('tagline','tagline', None), # Not supported by TVShow obj?
            ('mpaa','content_rating', self._parse_rating),
            ('genre','genres', lambda x:[y.strip() for y in x.split("/")]),
            ('status','status',lambda x: x.strip()),
            ('plot','plot', None), 
        ]:
            try:
                value = nfo_xml.xpath(xml_key)[0].text
                if cast:
                    value = cast(value)
                out[out_key] = value
            except:
                self.DLog("No <%s> tag found in nfo file." % out_key)

        out.update(self._get_premier(nfo_xml))
        out.update(self._get_ratings(nfo_xml))
        out.update(self._get_duration(nfo_xml))
        out.update(self._get_alt_ratings(nfo_xml))
        out.update(self._get_actors(nfo_xml))

        collections = []
        collections += self._get_collections_from_set(nfo_xml)
        collections += self._get_collections_from_tags(nfo_xml)
        if len(collections):
            out['collections'] = collections

        return out

    def _generate_id_from_title(self, title):
        ord3 = lambda x : '%.3d' % ord(x)
        out = ''.join(map(ord3, title))
        out = str(abs(hash(int(out))))
        return out


    def _extract_info_for_mediafile(self, mediafile):
        out = {}
        nfo_file = self._find_nfo_for_file(mediafile)
        if nfo_file:
            Log("Found nfo file at '%s', parsing" % nfo_file)
            nfo_text = Core.storage.load(nfo_file)
            nfo_text = self._sanitize_nfo(nfo_text, 'tvshow')
            out = self._parse_tvshow_nfo_text(nfo_text)
        return out


    def search(self, results, media, lang):
        self._log_function_entry('search')

        record = {
            'id':        media.id,
            'lang':      lang,
            'score':     100,  # 100 is perfect match
            'sorttitle': None,
            'title':     media.title,
            'year':      0, # TODO: Need a better default
        }

        try:
            mediafile = self._find_mediafile_for_id(record['id'])
        except:
            Log("Error trying to find mediafile for id: '%s'" % record['id'])
            self.DLog("Traceback: %s" % traceback.format_exc())
            return

        record.update(self._extract_info_for_mediafile(mediafile))

        # Attempt to guess/fixup mising values
        if not record['title']:
            record['title'] = "Unknown"
            if mediafile:
                title_guess = self._guess_title_by_mediafile(mediafile)
                if title_guess:
                    record['title'] = title_guess
        if not record['id']:
            record['id'] = self._generate_id_from_title(record['title'])

        Log("Scraped results: %s" % record)
        if True:
            #Transfer daat to the metadata object
            result = MetadataSearchResult(
                id=record['id'],
                lang=record['lang'],
                score=record['score'],
                sorttitle=record['sorttitle'],
                title=record['title'],
                year=record['year'],
            )
            results.Append(result)

    def update_metadata_with_localmediaagent(self, metadata):
        posterNames = []
        posterNames.append (os.path.join(path, "poster.jpg"))
        posterNames.append (os.path.join(path, "folder.jpg"))
        posterNames.append (os.path.join(path, "show.jpg"))
        posterNames.append (os.path.join(path, "season-all-poster.jpg"))

        # check possible poster file locations
        posterFilename = self.checkFilePaths (posterNames, 'poster')

        if posterFilename:
            posterData = Core.storage.load(posterFilename)
            metadata.posters['poster.jpg'] = Proxy.Media(posterData)
            Log('Found poster image at ' + posterFilename)

        bannerNames = []
        bannerNames.append (os.path.join(path, "banner.jpg"))
        bannerNames.append (os.path.join(path, "folder-banner.jpg"))

        # check possible banner file locations
        bannerFilename = self.checkFilePaths (bannerNames, 'banner')

        if bannerFilename:
            bannerData = Core.storage.load(bannerFilename)
            metadata.banners['banner.jpg'] = Proxy.Media(bannerData)
            Log('Found banner image at ' + bannerFilename)

        fanartNames = []

        fanartNames.append (os.path.join(path, "fanart.jpg"))
        fanartNames.append (os.path.join(path, "art.jpg"))
        fanartNames.append (os.path.join(path, "backdrop.jpg"))
        fanartNames.append (os.path.join(path, "background.jpg"))

        # check possible fanart file locations
        fanartFilename = self.checkFilePaths (fanartNames, 'fanart')

        if fanartFilename:
            fanartData = Core.storage.load(fanartFilename)
            metadata.art['fanart.jpg'] = Proxy.Media(fanartData)
            Log('Found fanart image at ' + fanartFilename)

        themeNames = []

        themeNames.append (os.path.join(path, "theme.mp3"))

        # check possible theme file locations
        themeFilename = self.checkFilePaths (themeNames, 'theme')

        if themeFilename:
            themeData = Core.storage.load(themeFilename)
            metadata.themes['theme.mp3'] = Proxy.Media(themeData)
            Log('Found theme music ' + themeFilename)

##### update Function #####
    def update(self, metadata, media, lang):
        self._log_function_entry('update')

        Dict.Reset()
        metadata.duration = None

        record = {
            'id':        media.id,
            'lang':      lang,
            'sorttitle': None,
            'title':     media.title,
            'year':      0, # TODO: Need a better default
        }

        duration_key = 'duration_'+record['id']
        Dict[duration_key] = [0] * 200
        Log('Update called for TV Show with id = ' + record['id'])

        try:
            mediafile = self._find_mediafile_for_id(record['id'])
        except:
            Log("Error trying to find mediafile for id: '%s'" % record['id'])
            self.DLog("Traceback: %s" % traceback.format_exc())
            return

        if not Prefs['localmediaagent']:
            update_metadata_with_localmediaagent(metadata)

        record.update(self._extract_info_for_mediafile(mediafile))

        if not record['title']:
            record['title'] = "Unknown"
            if mediafile:
                title_guess = self._guess_title_by_mediafile(mediafile)
                if title_guess:
                    record['title'] = title_guess

        #Log("---------------------")
        #Log("Series nfo Information")
        #Log("---------------------")
        #try: Log("ID: " + str(metadata.guid))
        #except: Log("ID: -")
        #try: Log("Title: " + str(metadata.title))
        #except: Log("Title: -")
        #try: Log("Sort Title: " + str(metadata.title_sort))
        #except: Log("Sort Title: -")
        #try: Log("Original: " + str(metadata.original_title))
        #except: Log("Original: -")
        #try: Log("Rating: " + str(metadata.rating))
        #except: Log("Rating: -")
        #try: Log("Content: " + str(metadata.content_rating))
        #except: Log("Content: -")
        #try: Log("Network: " + str(metadata.studio))
        #except: Log("Network: -")
        #try: Log("Premiere: " + str(metadata.originally_available_at))
        #except: Log("Premiere: -")
        ##try: Log("Tagline: " + str(metadata.tagline))
        #except: Log("Tagline: -")
        #try: Log("Summary: " + str(metadata.summary))
        #except: Log("Summary: -")
        #Log("Genres:")
        #try: [Log("\t" + genre) for genre in metadata.genres]
        #except: Log("\t-")
        #Log("Collections:")
        #try: [Log("\t" + collection) for collection in metadata.collections]
        #except: Log("\t-")
        #try: Log("Duration: " + str(metadata.duration // 60000) + ' min')
        #except: Log("Duration: -")
        #Log("Actors:")
        #try: [Log("\t" + actor.name + " > " + actor.role) for actor in metadata.roles]
        #except: [Log("\t" + actor.name) for actor in metadata.roles]
        #Log("---------------------")

        if True:
            #Transfer daat to the metadata object
            for k in ['title','title_sort','original_title','rating','content_rating','studio','originally_available_at','tagline','summary','duration']:
                setattr(metadata, k, record[k])
            metadata.roles.clear()
            for actor in record.get('actors', []):
                newrole = metadata.roles.new()
                newrole.name = actor.get('name')
                newrole.role = actor.get('role')
                newrole.photo = actor.get('photo')
            metadata.summary = self._build_summary(record)
            metadata.genres.clear()
            if record.get('genres'):
                for genre in record['genres']:
                    metadata.genres.add(genre)
            metadata.genres.discard('')
            metadata.collections.clear()
            if record.get('collections'):
                for collection in record['collections']:
                    metadata.collections.add(collection)
            metadata.collections.discard('')


        # Grabs the season data
        @parallelize
        def UpdateEpisodes():
            self.DLog("UpdateEpisodes called")
            pageUrl = "http://127.0.0.1:32400/library/metadata/" + media.id + "/children"
            seasonList = XML.ElementFromURL(pageUrl).xpath('//MediaContainer/Directory')

            seasons = []
            for seasons in seasonList:
                try: seasonID = seasons.get('key')
                except: pass
                try: season_num = seasons.get('index')
                except: pass

                self.DLog("seasonID : " + path)
                if seasonID.count('allLeaves') == 0:
                    self.DLog("Finding episodes")

                    pageUrl = "http://127.0.0.1:32400" + seasonID

                    episodes = XML.ElementFromURL(pageUrl).xpath('//MediaContainer/Video')
                    self.DLog("Found " + str(len(episodes)) + " episodes.")

                    firstEpisodePath = XML.ElementFromURL(pageUrl).xpath('//Part')[0].get('file')
                    seasonPath = os.path.dirname(firstEpisodePath)

                    seasonFilename = ""
                    seasonFilenameZero = ""
                    seasonPathFilename = ""
                    if(int(season_num) == 0):
                        seasonFilenameFrodo = 'season-specials-poster.jpg'
                        seasonFilenameEden = 'season-specials.tbn'
                        seasonFilenameZero = 'season00-poster.jpg'
                    else:
                        seasonFilenameFrodo = 'season%(number)02d-poster.jpg' % {"number": int(season_num)}
                        seasonFilenameEden = 'season%(number)02d.tbn' % {"number": int(season_num)}

                    if not Prefs['localmediaagent']:
                        seasonPosterNames = []

                        #Frodo
                        seasonPosterNames.append (os.path.join(path, seasonFilenameFrodo))
                        seasonPosterNames.append (os.path.join(path, seasonFilenameZero))
                        seasonPosterNames.append (os.path.join(seasonPath, seasonFilenameFrodo))
                        seasonPosterNames.append (os.path.join(seasonPath, seasonFilenameZero))
                        #Eden
                        seasonPosterNames.append (os.path.join(path, seasonFilenameEden))
                        seasonPosterNames.append (os.path.join(seasonPath, seasonFilenameEden))
                        #DLNA
                        seasonPosterNames.append (os.path.join(seasonPath, "folder.jpg"))
                        seasonPosterNames.append (os.path.join(seasonPath, "poster.jpg"))
                        #Fallback to Series Poster
                        seasonPosterNames.append (os.path.join(path, "poster.jpg"))

                        # check possible season poster file locations
                        seasonPosterFilename = self.checkFilePaths (seasonPosterNames, 'season poster')

                        if seasonPosterFilename:
                            seasonData = Core.storage.load(seasonPosterFilename)
                            metadata.seasons[season_num].posters[seasonPosterFilename] = Proxy.Media(seasonData)
                            Log('Found season poster image at ' + seasonPosterFilename)

                        # Season Banner
                        seasonBannerFileName = 'season%(number)02d-banner.jpg' % {"number": int(season_num)}

                        seasonBannerNames = []
                        seasonBannerNames.append (os.path.join(seasonPath, seasonBannerFileName))
                        seasonBannerNames.append (os.path.join(seasonPath, "banner.jpg"))
                        seasonBannerNames.append (os.path.join(seasonPath, "folder-banner.jpg"))
                        seasonBannerNames.append (os.path.join(path, seasonBannerFileName))
                        seasonBannerNames.append (os.path.join(path, "banner.jpg"))
                        seasonBannerNames.append (os.path.join(path, "folder-banner.jpg"))

                        # check possible banner file locations
                        seasonBanner = self.checkFilePaths (seasonBannerNames, 'season banner')

                        if seasonBanner:
                            seasonBannerData = Core.storage.load(seasonBanner)
                            metadata.seasons[season_num].banners[seasonBanner] = Proxy.Media(seasonBannerData)
                            Log('Found season banner image at ' + seasonBanner)

                        # Season Fanart
                        seasonFanartFileName = 'season%(number)02d-fanart.jpg' % {"number": int(season_num)}
                        seasonFanartNames = []
                        seasonFanartNames.append (os.path.join(seasonPath, seasonFanartFileName))
                        seasonFanartNames.append (os.path.join(path, seasonFanartFileName))
                        seasonFanartNames.append (os.path.join(path, "fanart.jpg"))

                        # check possible Fanart file locations
                        seasonFanart = self.checkFilePaths (seasonFanartNames, 'season fanart')

                        if seasonFanart:
                            seasonFanartData = Core.storage.load(seasonFanart)
                            metadata.seasons[season_num].art[seasonFanart] = Proxy.Media(seasonFanartData)
                            Log('Found season fanart image at ' + seasonFanart)

                    episodeXML = []
                    epnumber = 0
                    for episodeXML in episodes:
                        ep_key = episodeXML.get('key')
                        self.DLog("epKEY: " + ep_key)
                        epnumber = epnumber + 1
                        ep_num = episodeXML.get('index')
                        if (ep_num == None):
                            self.DLog("epNUM: Error!")
                            ep_num = str(epnumber)
                        self.DLog("epNUM: " + ep_num)

                        # Get the episode object from the model
                        episode = metadata.seasons[season_num].episodes[ep_num]

                        # Grabs the episode information
                        @task
                        def UpdateEpisode(episode=episode, season_num=season_num, ep_num=ep_num, ep_key=ep_key, path=path1):
                            self.DLog("UpdateEpisode called for episode (" + str(episode)+ ", " + str(ep_key) + ") S" + str(season_num.zfill(2)) + "E" + str(ep_num.zfill(2)))
                            if(ep_num.count('allLeaves') == 0):
                                pageUrl = "http://127.0.0.1:32400" + ep_key + "/tree"
                                path1 = String.Unquote(XML.ElementFromURL(pageUrl).xpath('//MediaPart')[0].get('file')).encode('utf-8')

                                self.DLog('UPDATE: ' + path1)
                                filepath = path1.split
                                path = os.path.dirname(path1)
                                fileExtension = path1.split(".")[-1].lower()

                                nfoFile = path1.replace('.'+fileExtension, '.nfo')
                                self.DLog("Looking for episode NFO file " + nfoFile)
                                if os.path.exists(nfoFile):
                                    self.DLog("File exists...")
                                    nfoText = Core.storage.load(nfoFile)
                                    # strip media browsers <multiepisodenfo> tags
                                    nfoText = nfoText.replace ('<multiepisodenfo>','')
                                    nfoText = nfoText.replace ('</multiepisodenfo>','')
                                    # strip Sick Beard's <xbmcmultiepisodenfo> tags
                                    nfoText = nfoText.replace ('<xbmcmultiepisode>','')
                                    nfoText = nfoText.replace ('</xbmcmultiepisode>','')
                                    # work around failing XML parses for things with &'s in them. This may need to go farther than just &'s....
                                    nfoText = re.sub(r'&(?![A-Za-z]+[0-9]*;|#[0-9]+;|#x[0-9a-fA-F]+;)', r'&amp;', nfoText)
                                    # remove empty xml tags from nfo
                                    self.DLog('Removing empty XML tags from tvshows nfo...')
                                    nfoText = re.sub(r'^\s*<.*/>[\r\n]+', '', nfoText, flags = re.MULTILINE)
                                    nfoTextLower = nfoText.lower()
                                    if nfoTextLower.count('<episodedetails') > 0 and nfoTextLower.count('</episodedetails>') > 0:
                                        self.DLog("Looks like an XBMC NFO file (has <episodedetails>)")
                                        nfoepc = int(nfoTextLower.count('<episodedetails'))
                                        nfopos = 1
                                        multEpTitlePlexPatch = multEpSummaryPlexPatch = ""
                                        multEpTestPlexPatch = 0
                                        while nfopos <= nfoepc:
                                            self.DLog("EpNum: " + str(ep_num) + " NFOEpCount:" + str(nfoepc) +" Current EpNFOPos: " + str(nfopos))
                                            # Remove URLs (or other stuff) at the end of the XML file
                                            nfoTextTemp = '%s</episodedetails>' % nfoText.split('</episodedetails>')[nfopos-1]

                                            # likely an xbmc nfo file
                                            try: nfoXML = XML.ElementFromString(nfoTextTemp).xpath('//episodedetails')[0]
                                            except:
                                                self.DLog('ERROR: Cant parse XML in file: ' + nfoFile)
                                                return

                                            # remove remaining empty xml tags
                                            self.DLog('Removing remaining empty XML Tags from episode nfo...')
                                            nfoXML = self.RemoveEmptyTags(nfoXML)

                                            # check ep number
                                            nfo_ep_num = 0
                                            try:
                                                nfo_ep_num = nfoXML.xpath('episode')[0].text
                                                self.DLog('EpNum from NFO: ' + str(nfo_ep_num))
                                            except:
                                                self.DLog('No EpNum from NFO! Assuming: ' + ep_num)
                                                nfo_ep_num = ep_num
                                                pass

                                            # Checks to see user has renamed files so plex ignores multiepisodes and confirms that there is more than on episodedetails
                                            if not re.search('.s\d{1,3}e\d{1,3}[-]?e\d{1,3}.', path1.lower()) and (nfoepc > 1):
                                                multEpTestPlexPatch = 1

                                            # Creates combined strings for Plex MultiEpisode Patch
                                            if multEpTestPlexPatch and Prefs['multEpisodePlexPatch'] and (nfoepc > 1):
                                                self.DLog('Multi Episode found: ' + str(nfo_ep_num))
                                                multEpTitleSeparator = Prefs['multEpisodeTitleSeparator']
                                                try:
                                                    if nfopos == 1:
                                                        multEpTitlePlexPatch = nfoXML.xpath('title')[0].text
                                                        multEpSummaryPlexPatch = "[Episode #" + str(nfo_ep_num) + " - " + nfoXML.xpath('title')[0].text + "] " + nfoXML.xpath('plot')[0].text
                                                    else:
                                                        multEpTitlePlexPatch = multEpTitlePlexPatch + multEpTitleSeparator + nfoXML.xpath('title')[0].text
                                                        multEpSummaryPlexPatch = multEpSummaryPlexPatch + "\n" + "[Episode #" + str(nfo_ep_num) + " - " + nfoXML.xpath('title')[0].text + "] " + nfoXML.xpath('plot')[0].text
                                                except: pass
                                            else:
                                                if int(nfo_ep_num) == int(ep_num):
                                                    nfoText = nfoTextTemp
                                                    break

                                            nfopos = nfopos + 1

                                        if (not multEpTestPlexPatch or not Prefs['multEpisodePlexPatch']) and (nfopos > nfoepc):
                                            self.DLog('No matching episode in nfo file!')
                                            return

                                        # Ep. Title
                                        if Prefs['multEpisodePlexPatch'] and (multEpTitlePlexPatch != ""):
                                            self.DLog('using multi title: ' + multEpTitlePlexPatch)
                                            episode.title = multEpTitlePlexPatch
                                        else:
                                            try: episode.title = nfoXML.xpath('title')[0].text
                                            except:
                                                self.DLog("ERROR: No <title> tag in " + nfoFile + ". Aborting!")
                                                return
                                        # Ep. Content Rating
                                        try:
                                            mpaa = nfoXML.xpath('./mpaa')[0].text
                                            match = re.match(r'(?:Rated\s)?(?P<mpaa>[A-z0-9-+/.]+(?:\s[0-9]+[A-z]?)?)?', mpaa)
                                            if match.group('mpaa'):
                                                content_rating = match.group('mpaa')
                                            else:
                                                content_rating = 'NR'
                                            episode.content_rating = content_rating
                                        except: pass
                                        # Ep. Premiere
                                        try:
                                            air_string = None
                                            try:
                                                self.DLog("Reading aired tag...")
                                                air_string = nfoXML.xpath("aired")[0].text
                                                self.DLog("Aired tag is: " + air_string)
                                            except:
                                                self.DLog("No aired tag found...")
                                                pass
                                            if not air_string:
                                                try:
                                                    self.DLog("Reading dateadded tag...")
                                                    air_string = nfoXML.xpath("dateadded")[0].text
                                                    self.DLog("Dateadded tag is: " + air_string)
                                                except:
                                                    self.DLog("No dateadded tag found...")
                                                    pass
                                            if air_string:
                                                try:
                                                    if Prefs['dayfirst']:
                                                        dt = parse(air_string, dayfirst=True)
                                                    else:
                                                        dt = parse(air_string)
                                                    episode.originally_available_at = dt
                                                    self.DLog("Set premiere to: " + dt.strftime('%Y-%m-%d'))
                                                except:
                                                    self.DLog("Couldn't parse premiere: " + air_string)
                                                    pass
                                        except:
                                            self.DLog("Exception parsing Ep Premiere: " + traceback.format_exc())
                                            pass
                                        # Ep. Summary
                                        if Prefs['multEpisodePlexPatch'] and (multEpSummaryPlexPatch != ""):
                                            self.DLog('using multi summary: ' + multEpSummaryPlexPatch)
                                            episode.summary = multEpSummaryPlexPatch
                                        else:
                                            try: episode.summary = nfoXML.xpath('plot')[0].text
                                            except:
                                                episode.summary = ""
                                                pass
                                        # Ep. Ratings
                                        try:
                                            epnforating = round(float(nfoXML.xpath("rating")[0].text.replace(',', '.')),1)
                                            episode.rating = epnforating
                                            self.DLog("Episode Rating found: " + str(epnforating))
                                        except:
                                            self.DLog("Cant read rating from episode nfo.")
                                            epnforating = 0.0
                                            pass
                                        if Prefs['altratings']:
                                            self.DLog("Searching for additional episode ratings...")
                                            allowedratings = Prefs['ratings']
                                            if not allowedratings: allowedratings = ""
                                            addepratingsstring = ""
                                            try:
                                                addepratings = nfoXML.xpath('ratings')
                                                self.DLog("Additional episode ratings found: " + str(addeprating))
                                            except:
                                                self.DLog("Can't read additional episode ratings from nfo.")
                                                pass
                                            if addepratings:
                                                for addepratingXML in addepratings:
                                                    for addeprating in addepratingXML:
                                                        try:
                                                            epratingprovider = str(addeprating.attrib['moviedb'])
                                                        except:
                                                            pass
                                                            self.DLog("Skipping additional episode rating without moviedb attribute!")
                                                            continue
                                                        epratingvalue = str(addeprating.text.replace (',','.'))
                                                        if epratingprovider.lower() in PERCENT_RATINGS:
                                                            epratingvalue = epratingvalue + "%"
                                                        if epratingprovider in allowedratings or allowedratings == "":
                                                            self.DLog("adding episode rating: " + epratingprovider + ": " + epratingvalue)
                                                            addepratingsstring = addepratingsstring + " | " + epratingprovider + ": " + epratingvalue
                                                if addratingsstring != "": # originally in series??
                                                    self.DLog("Putting additional episode ratings at the " + Prefs['ratingspos'] + " of the summary!")
                                                    if Prefs['ratingspos'] == "front":
                                                        if Prefs['preserveratingep']:
                                                            episode.summary = addepratingsstring[3:] + self.unescape(" &#9733;\n\n") + episode.summary
                                                        else:
                                                            episode.summary = self.unescape("&#9733; ") + addepratingsstring[3:] + self.unescape(" &#9733;\n\n") + episode.summary
                                                    else:
                                                        episode.summary = episode.summary + self.unescape("\n\n&#9733; ") + addepratingsstring[3:] + self.unescape(" &#9733;")
                                                else:
                                                    self.DLog("Additional episode ratings empty or malformed!")
                                            if Prefs['preserveratingep']:
                                                self.DLog("Putting Ep .nfo rating in front of summary!")
                                                episode.summary = self.unescape(str(Prefs['beforeratingep'])) + "{:.1f}".format(epnforating) + self.unescape(str(Prefs['afterratingep'])) + episode.summary
                                                episode.rating = epnforating
                                            else:
                                                episode.rating = epnforating
                                        # Ep. Producers / Writers / Guest Stars(Credits)
                                        try:
                                            credit_string = None
                                            credits = nfoXML.xpath('credits')
                                            episode.producers.clear()
                                            episode.writers.clear()
                                            episode.guest_stars.clear()
                                            for creditXML in credits:
                                                for credit in creditXML.text.split("/"):
                                                    credit_string = credit.strip()
                                                    self.DLog ("Credit String: " + credit_string)
                                                    if re.search ("(Producer)", credit_string, re.IGNORECASE):
                                                        credit_string = re.sub ("\(Producer\)","",credit_string,flags=re.I).strip()
                                                        self.DLog ("Credit (Producer): " + credit_string)
                                                        episode.producers.new().name = credit_string
                                                        continue
                                                    if re.search ("(Guest Star)", credit_string, re.IGNORECASE):
                                                        credit_string = re.sub ("\(Guest Star\)","",credit_string,flags=re.I).strip()
                                                        self.DLog ("Credit (Guest Star): " + credit_string)
                                                        episode.guest_stars.new().name = credit_string
                                                        continue
                                                    if re.search ("(Writer)", credit_string, re.IGNORECASE):
                                                        credit_string = re.sub ("\(Writer\)","",credit_string,flags=re.I).strip()
                                                        self.DLog ("Credit (Writer): " + credit_string)
                                                        episode.writers.new().name = credit_string
                                                        continue
                                                    self.DLog ("Unknown Credit (adding as Writer): " + credit_string)
                                                    episode.writers.new().name = credit_string
                                        except:
                                            self.DLog("Exception parsing Credits: " + traceback.format_exc())
                                            pass
                                        # Ep. Directors
                                        try:
                                            directors = nfoXML.xpath('director')
                                            episode.directors.clear()
                                            for directorXML in directors:
                                                for director in directorXML.text.split("/"):
                                                    director_string = director.strip()
                                                    self.DLog ("Director: " + director)
                                                    episode.directors.new().name = director
                                        except:
                                            self.DLog("Exception parsing Director: " + traceback.format_exc())
                                            pass
                                        # Ep. Duration
                                        try:
                                            self.DLog ("Trying to read <durationinseconds> tag from episodes .nfo file...")
                                            fileinfoXML = XML.ElementFromString(nfoText).xpath('fileinfo')[0]
                                            streamdetailsXML = fileinfoXML.xpath('streamdetails')[0]
                                            videoXML = streamdetailsXML.xpath('video')[0]
                                            eruntime = videoXML.xpath("durationinseconds")[0].text
                                            eduration_ms = int(re.compile('^([0-9]+)').findall(eruntime)[0]) * 1000
                                            episode.duration = eduration_ms
                                        except:
                                            try:
                                                self.DLog ("Fallback to <runtime> tag from episodes .nfo file...")
                                                eruntime = nfoXML.xpath("runtime")[0].text
                                                eduration = int(re.compile('^([0-9]+)').findall(eruntime)[0])
                                                eduration_ms = self.time_convert (self, eduration)
                                                episode.duration = eduration_ms
                                            except:
                                                episode.duration = metadata.duration if metadata.duration else None
                                                self.DLog ("No Episode Duration in episodes .nfo file.")
                                                pass
                                        try:
                                            if (eduration_ms > 0):
                                                eduration_min = int(round (float(eduration_ms) / 1000 / 60))
                                                Dict[duration_key][eduration_min] = Dict[duration_key][eduration_min] + 1
                                        except:
                                            pass

                                        if not Prefs['localmediaagent']:
                                            episodeThumbNames = []

                                            #Multiepisode nfo thumbs
                                            if (nfoepc > 1) and (not Prefs['multEpisodePlexPatch'] or not multEpTestPlexPatch):
                                                for name in glob.glob1(os.path.dirname(nfoFile), '*S' + str(season_num.zfill(2)) + 'E' + str(ep_num.zfill(2)) + '*.jpg'):
                                                    if "-E" in name: continue
                                                    episodeThumbNames.append (os.path.join(os.path.dirname(nfoFile), name))

                                            #Frodo
                                            episodeThumbNames.append (nfoFile.replace('.nfo', '-thumb.jpg'))
                                            #Eden
                                            episodeThumbNames.append (nfoFile.replace('.nfo', '.tbn'))
                                            #DLNA
                                            episodeThumbNames.append (nfoFile.replace('.nfo', '.jpg'))

                                            # check possible episode thumb file locations
                                            episodeThumbFilename = self.checkFilePaths (episodeThumbNames, 'episode thumb')

                                            if episodeThumbFilename:
                                                thumbData = Core.storage.load(episodeThumbFilename)
                                                episode.thumbs[episodeThumbFilename] = Proxy.Media(thumbData)
                                                Log('Found episode thumb image at ' + episodeThumbFilename)

                                        Log("---------------------")
                                        Log("Episode (S"+season_num.zfill(2)+"E"+ep_num.zfill(2)+") nfo Information")
                                        Log("---------------------")
                                        try: Log("Title: " + str(episode.title))
                                        except: Log("Title: -")
                                        try: Log("Content: " + str(episode.content_rating))
                                        except: Log("Content: -")
                                        try: Log("Rating: " + str(episode.rating))
                                        except: Log("Rating: -")
                                        try: Log("Premiere: " + str(episode.originally_available_at))
                                        except: Log("Premiere: -")
                                        try: Log("Summary: " + str(episode.summary))
                                        except: Log("Summary: -")
                                        Log("Writers:")
                                        try: [Log("\t" + writer.name) for writer in episode.writers]
                                        except: Log("\t-")
                                        Log("Directors:")
                                        try: [Log("\t" + director.name) for director in episode.directors]
                                        except: Log("\t-")
                                        try: Log("Duration: " + str(episode.duration // 60000) + ' min')
                                        except: Log("Duration: -")
                                        Log("---------------------")
                                    else:
                                        Log("ERROR: <episodedetails> tag not found in episode NFO file " + nfoFile)

        # Final Steps
        duration_min = 0
        duration_string = ""
        if not metadata.duration:
            try:
                duration_min = Dict[duration_key].index(max(Dict[duration_key]))
                for d in Dict[duration_key]:
                    if (d != 0):
                        duration_string = duration_string + "(" + str(Dict[duration_key].index(d)) + "min:" + str(d) + ")"
            except:
                self.DLog("Error accessing duration_key in dictionary!")
                pass
            self.DLog("Episode durations are: " + duration_string)
            metadata.duration = duration_min * 60 * 1000
            self.DLog("Set Series Episode Runtime to median of all episodes: " + str(metadata.duration) + " (" + str (duration_min) + " minutes)")
        else:
            self.DLog("Series Episode Runtime already set! Current value is:" + str(metadata.duration))
        Dict.Reset()
