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
import logging

from utils import _get, check_file_paths, remove_empty_tags, unescape, _sanitize_nfo, _generate_id_from_title

from pms_gateway import PmsGateway
from nfo_parser import NfoParser
from media_finder import MediaFinder


class xbmcnfotv(Agent.TV_Shows):
    name = 'XBMCnfoTVImporter'
    ver = '1.1-93-gc3e9112-220'
    primary_provider = True
    languages = [Locale.Language.NoLanguage]
    accepts_from = ['com.plexapp.agents.localmedia','com.plexapp.agents.opensubtitles','com.plexapp.agents.podnapisi','com.plexapp.agents.plexthememusic','com.plexapp.agents.subzero']
    contributes_to = ['com.plexapp.agents.thetvdb']

    def __init__(self):
        self.pms = PmsGateway(XML, String)
        self.parser = NfoParser(Prefs)
        self.media_finder = MediaFinder(Prefs)

##### helper functions #####
    def DLog(self, LogMessage):
        if Prefs['debug']:
            Log(LogMessage)

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


    def _find_nfo_for_file(self, filename, algo='tvshow'):
        def _dir_at_depth(path, depth):
            for i in xrange(depth):
                path = os.path.dirname(path)
            return path

        if algo == 'episode':
            basename = os.path.basename(filename)
            boom = basename.split(".")
            boom[-1] = 'nfo'
            nfo_name = ".".join(boom)
        else:
            nfo_name = 'tvshow.nfo'

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


    def _guess_title_by_mediafile(self, mediafile):
        out = None
        filename = os.path.basename(mediafile)
        self.DLog("Guessing a title based on mediafile '%s'" % filename)

        matches = re.compile('(.+?)[ .]S(\d\d?)E(\d\d?).*?\Z').match(filename) 
        if matches:
            out = matches.group(1).replace(".", " ")

        self.DLog("Title guess of: '%s'" % out)
        return out

    def _build_show_summary(self,
        data,
        show_status = False,
        pre_rating = '', 
        post_rating = '', 
        ratings_pos = 'front',
        preserve_rating = False,
    ):
        out = []

        star = unescape("&#9733;")
        sep = " | "
        status      = _get(data, 'status')
        plot        = _get(data, 'plot')
        alt_ratings = _get(data, 'alt_ratings')
        rating      = _get(data, 'rating', 0.0)

        if show_status and status:
            out.append('Status: {}'.format(status))

        if plot:
            out.append(plot)

        if alt_ratings:
            buf = []
            for source, _rating in alt_ratings:
                buf.append("{}: {}".format(source, _rating))
            piece = sep.join(buf)

            if ratings_pos == 'front':
                out.insert(0, star+" "+piece+" "+star+"\n\n")
            else:
                out.append("\n\n"+star+" "+piece+" "+star)

        if preserve_rating:
            tmp = unescape("{}{:.1f}{}".format(pre_rating, rating, post_rating))
            out.insert(0, tmp)

        return sep.join(out)


    def _extract_info_for_mediafile(self, mediafile):
        out = {}
        nfo_file = self._find_nfo_for_file(mediafile, algo='tvshow')
        if nfo_file:
            out['nfo_file'] = nfo_file  # needed later to try to find local artwork/dirs
            Log("Found nfo file at '%s', parsing" % nfo_file)
            nfo_text = Core.storage.load(nfo_file)
            nfo_text = _sanitize_nfo(nfo_text, 'tvshow')
            out.update(self.parser._parse_tvshow_nfo_text(nfo_text))
            self.parser._parse_tvshow_nfo_text(out, nfo_file)

            for actor in _get(out, 'actors', []):
                self.media_finder.nfo_file = nfo_file  # Just in case we need to do local file probing
                photo = self.media_finder._get_actor_photo(actor['name'], actor.get('thumb')) # empty str, or content
                if photo:
                    actor['photo'] = photo

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
            mediafile = self.pms._find_mediafiles_for_id(record['id'])[0]
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
            record['id'] = _generate_id_from_title(record['title'])

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
        path = os.path.dirname(nfo_file)  # TODO: Get this data in here

        posterNames = []
        posterNames.append (os.path.join(path, "poster.jpg"))
        posterNames.append (os.path.join(path, "folder.jpg"))
        posterNames.append (os.path.join(path, "show.jpg"))
        posterNames.append (os.path.join(path, "season-all-poster.jpg"))
        # check possible poster file locations
        posterFilename = check_file_paths(posterNames, 'poster')
        if posterFilename:
            posterData = Core.storage.load(posterFilename)
            metadata.posters['poster.jpg'] = Proxy.Media(posterData)
            Log('Found poster image at ' + posterFilename)

        bannerNames = []
        bannerNames.append (os.path.join(path, "banner.jpg"))
        bannerNames.append (os.path.join(path, "folder-banner.jpg"))
        # check possible banner file locations
        bannerFilename = check_file_paths (bannerNames, 'banner')
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
        fanartFilename = check_file_paths(fanartNames, 'fanart')
        if fanartFilename:
            fanartData = Core.storage.load(fanartFilename)
            metadata.art['fanart.jpg'] = Proxy.Media(fanartData)
            Log('Found fanart image at ' + fanartFilename)

        themeNames = []
        themeNames.append (os.path.join(path, "theme.mp3"))
        # check possible theme file locations
        themeFilename = check_file_paths(themeNames, 'theme')
        if themeFilename:
            themeData = Core.storage.load(themeFilename)
            metadata.themes['theme.mp3'] = Proxy.Media(themeData)
            Log('Found theme music ' + themeFilename)

    def update_metadata_with_localmediaagent_seasons(self, metadata, season_num):
        path = os.path.dirname(nfo_file)  # TODO: Get this data in here
        seasonFilename = ""
        seasonFilenameZero = ""
        seasonPathFilename = ""
        if(season_num == 0):
            seasonFilenameFrodo = 'season-specials-poster.jpg'
            seasonFilenameEden = 'season-specials.tbn'
            seasonFilenameZero = 'season00-poster.jpg'
        else:
            seasonFilenameFrodo = 'season%(number)02d-poster.jpg' % {"number": season_num}
            seasonFilenameEden = 'season%(number)02d.tbn' % {"number": season_num}

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
        seasonPosterFilename = check_file_paths(seasonPosterNames, 'season poster')
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
        seasonBanner = check_file_paths(seasonBannerNames, 'season banner')
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
        seasonFanart = check_file_paths(seasonFanartNames, 'season fanart')
        if seasonFanart:
            seasonFanartData = Core.storage.load(seasonFanart)
            metadata.seasons[season_num].art[seasonFanart] = Proxy.Media(seasonFanartData)
            Log('Found season fanart image at ' + seasonFanart)


    def _update_episodes(self, media_id, duration_key):
        self.DLog("UpdateEpisodes called")
        pageUrl = "http://127.0.0.1:32400/library/metadata/" + media_id + "/children"  # Only in "children" xml
        directory_nodes = XML.ElementFromURL(pageUrl).xpath('//MediaContainer/Directory')


        for directory_node in directory_nodes:
            directory_key = directory_node.get('key')  # key="/library/metadata/${id}/children"
            season_num = int(directory_node.get('index')) # 1-indexed

            if 'allLeaves' in directory_key: # Non-episode node, skip it
                continue


            pageUrl = "http://127.0.0.1:32400" + directory_key
            video_nodes = XML.ElementFromURL(pageUrl).xpath('//MediaContainer/Video') # Only in "children" xml
            self.DLog("Found " + str(len(video_nodes)) + " episodes.")

            firstEpisodePath = XML.ElementFromURL(pageUrl).xpath('//Part')[0].get('file') # Only in "children" xml
            seasonPath = os.path.dirname(firstEpisodePath)

            if not Prefs['localmediaagent']:
                self.update_metadata_with_localmediaagent_seasons(metadata, season_num)

            for i, video_node in enumerate(video_nodes):
                ep_key = _get(video_node, 'key')  # /library/metadata/NNN
                ep_num = _get(video_node, 'index', i+1) # 1-indexed

                # Get the existing episode object from the model
                episode = metadata.seasons[season_num].episodes[ep_num]  # Uses canononical form for season+episode 1-index

                # Looks like we are denoting a single unit of work and passing in all state.
                @task
                def UpdateEpisode(episode=episode, season_num=season_num, ep_num=ep_num, ep_key=ep_key, duration_key=duation_key):
                    self._update_episode(episode=episode, season_num=season_num, ep_num=ep_num, ep_key=ep_key, duration_key=duation_key)

    def _multiple_episode_feature(self, nfo_text, mediafile, ep_num, tag_name="episodedetails"):
        end_tag = "</{}>".format(tag_name)
        out = {
            'enabled': Prefs['multEpisodePlexPatch'],
            'nfo_episode_count': int(nfo_text.count('<{}'.format(tag_name))),
            'possible': False,  # Can we actually run the feature
        }
        summaries = []
        title_sep = Prefs['multEpisodeTitleSeparator']
        titles = []

        if not re.search('.s\d{1,3}e\d{1,3}[-]?e\d{1,3}.', mediafile.lower()):  # user named file to ignore multiepisodes
            if out['nfo_episode_count'] > 1:  # verify there is more than one tag
                out['possible'] = True

        nfo_episode_index = 1
        while nfo_episode_index <= out['nfo_episode_count']:
            #self.DLog("EpNum: {} NFOEpCount:{} Current EpNFOPos:{}".format(ep_num, out['nfo_episode_count'], nfo_episode_index))
            # Remove URLs (or other stuff) at the end of the XML file
            nfo_text_part = ('{}'+end_tag).format(nfo_text.split(end_tag)[nfo_episode_index-1])

            try:
                nfo_xml = XML.ElementFromString(nfo_text_part).xpath('//{}'.format(tag_name))[0]
            except:
                return None, out

            nfo_xml = remove_empty_tags(nfo_xml)
            try:
                nfo_ep_num = int(nfo_xml.xpath('episode')[0].text)
            except:
                nfo_ep_num = nfo_episode_index

            # Creates combined strings for Plex MultiEpisode Patch
            if out['possible'] and out['enabled'] and out['nfo_episode_count'] > 1:
                #self.DLog('Multi Episode found: {}'.format(nfo_ep_num))
                try:
                    title = nfo_xml.xpath('title')[0].text
                    plot =  nfo_xml.xpath('plot')[0].text
                    titles.append(title)
                    summaries.append("[Episode #{} - {}] {}".format(nfo_ep_num, title, plot))
                except:
                    pass
            else:
                if nfo_ep_num == ep_num:
                    nfo_text = nfo_text_part
                    break
            nfo_episode_index = nfo_episode_index + 1

        if out['enabled'] and out['possible']:
            if len(titles):
                out['title'] = title_sep.join(titles)
            if len(summaries):
                out['summary'] = "\n".join(summaries)

        return nfo_xml, out

    def _parse_episode_nfo_text(self, nfo_xml, out):
        #try:
        #    nfo_xml = XML.ElementFromString(nfo_text).xpath('//tvshow')[0]
        #except:
        #    Log('ERROR: failed parsing tvshow XML in nfo file')
        #    return out

        #nfo_xml = remove_empty_tags(nfo_xml)

        for xml_key, out_key, cast in [
            #('id','id', None),
            #('sorttitle','sorttitle', None),
            ('title','title', None),
            #('studio','studio', None),
            #('originaltitle','original_title', None),
            #('year','year', int),
            #('tagline','tagline', None), # Not supported by TVShow obj?
            ('mpaa','content_rating', self.parser._parse_rating),
            #('genre','genres', lambda x:[y.strip() for y in x.split("/")]),
            #('status','status',lambda x: x.strip()),
            ('plot','summary', None), 
        ]:
            if out_key in out:  # We already have an override value
                continue
            try:
                value = nfo_xml.xpath(xml_key)[0].text
                if cast:
                    value = cast(value)
                out[out_key] = value
            except:
                self.DLog("No <%s> tag found in nfo file." % out_key)

        out.update(self.parser._get_premier(nfo_xml))
        out.update(self.parser._get_ratings(nfo_xml))
        out.update(self.parser._get_duration_ms(nfo_xml))
        out.update(self.parser._get_alt_ratings(nfo_xml))
        #out.update(self.parser._get_actors(nfo_xml))
        out.update(self.parser._get_directors(nfo_xml))
        out.update(self.parser._get_credits(nfo_xml))

        #collections = []
        #collections += self.parser._get_collections_from_set(nfo_xml)
        #collections += self.parser._get_collections_from_tags(nfo_xml)
        #if len(collections):
        #    out['collections'] = collections

        return out

    def _build_episode_summary(self, data):
        out = []
        out.append(data['plot'])

        alt_ratings = " | ".join("{}: {}".format(source, rating) for source, rating in data['alt_ratings'])

        #if Prefs['ratingspos'] == "front":
        #    if Prefs['preserveratingep']:
        #        metadata.summary = alt_ratings + unescape(" &#9733;\n\n") + metadata.summary
        #    else:
        #        metadata.summary = unescape("&#9733; ") + alt_ratings + unescape(" &#9733;\n\n") + metadata.summary
        #else:
        #    metadata.summary = metadata.summary + unescape("\n\n&#9733; ") + alt_ratings + unescape(" &#9733;")
        #if Prefs['preserveratingep']:
        #    tmp = unescape("{}{:.1f}{}".format(Prefs['beforeratingep'], data['rating'], Prefs['afterratingep']))
        #    out.insert(0, tmp)

        return " | ".join(out)


    def _update_episode(self, episode, season_num, ep_num, ep_key,duration_key):
        self.DLog("UpdateEpisode called for episode ({}, {}) S{}E{}".format(episode, ep_key, season_num, ep_num))
        if 'allLeaves' in ep_key: # Non-episode node, skip it
            return

        mediafile = self.pms._find_mediafiles_for_id(ep_key)[0]
        nfo_file = self._find_nfo_for_file(mediafile, algo='episode')

        if not nfo_file:
            return

        nfo_text = Core.storage.load(nfo_file)
        nfo_text = _sanitize_nfo(nfo_text, 'episodedetails', strip_tags=[
            'multiepisodenfo', # Media Browser tags
            'xbmcmultiepisode', # Sick Beard tags
        ])

        if not (nfo_text.count('<episodedetails') > 0 and nfo_text.count('</episodedetails>') > 0):
            Log("ERROR: <episodedetails> tag not found in episode NFO file " + nfo_file)
            return

        nfo_xml, mef = self._multiple_episode_feature(nfo_text, mediafile, ep_num)

        if not nfo_xml:
            return

        out = {}

        if mef['enabled']:
            mef_title = mef.get('title')
            if mef_title:
                out['title'] = mef_title
            mef_summary = mef.get('summary')
            if mef_summary:
                out['summary'] = mef_summary

        out = self._parse_episode_nfo_text(nfo_xml, out)

        if not Prefs['localmediaagent']:
            episodeThumbNames = []

            #Multiepisode nfo thumbs
            if (mef['nfo_episode_count'] > 1) and (not mef['enabled'] or not mef['possible']):
                for name in glob.glob1(os.path.dirname(nfo_file), '*S' + str(season_num.zfill(2)) + 'E' + str(ep_num.zfill(2)) + '*.jpg'):
                    if "-E" in name:
                        continue
                    episodeThumbNames.append(os.path.join(os.path.dirname(nfo_file), name))

            #Frodo
            episodeThumbNames.append(nfo_file.replace('.nfo', '-thumb.jpg'))
            #Eden
            episodeThumbNames.append(nfo_file.replace('.nfo', '.tbn'))
            #DLNA
            episodeThumbNames.append(nfo_file.replace('.nfo', '.jpg'))

            # check possible episode thumb file locations
            episodeThumbFilename = check_file_paths(episodeThumbNames, 'episode thumb')

            if episodeThumbFilename:
                thumbData = Core.storage.load(episodeThumbFilename)
                episode.thumbs[episodeThumbFilename] = Proxy.Media(thumbData)
                Log('Found episode thumb image at ' + episodeThumbFilename)

        out['summary'] = self._build_episode_summary(out)  # Summaries are complicated

        if True:
            pass
            #Transfer data to the episode object
            #for k in [
            #    'title', 'title_sort', 'original_title', 'rating',
            #    'content_rating', 'studio', 'originally_available_at',
            #    'tagline', 'summary',
            #]:
            #    setattr(metadata, k, record[k])
            #metadata.roles.clear()
            #for actor in _get(record, 'actors', []):
            #    newrole = metadata.roles.new()
            #    newrole.name = actor.get('name')
            #    newrole.role = actor.get('role')
            #    newrole.photo = actor.get('photo')
            #metadata.genres.clear()
            #for genre in _get(record, 'genres', []):
            #    metadata.genres.add(genre)
            #metadata.genres.discard('')
            #metadata.collections.clear()
            #for collection in _get(record, 'collections', []):
            #    metadata.collections.add(collection)
            #metadata.collections.discard('')
            #### TODO good new ####
            #episode.directors.clear()
            #for name in _get(record, 'directors', []):
            #    episode.directors.new().name = name
            #episode.producers.clear()
            #for name in _get(record, 'producers', []):
            #    episode.producers.new().name = name
            #episode.writers.clear()
            #for name in _get(record, 'writers', []):
            #    episode.writers.new().name = name
            #episode.guest_stars.clear()
            #for name in _get(record, 'guest_stars', []):
            #    episode.guest_stars.new().name = name
            #episode.duration = _get(out, 'duration')
            # TODO I HAVE NO IDEA WHAT THIS WAS TRYING TO DO:
            try:
                if out['duration'] > 0:
                    _min = int(round(float(out['duration'])/ 1000/60))
                    Dict[duration_key][_min] = Dict[duration_key][_min] + 1
            except:
                pass


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


    def _set_duration_as_avg_of_episodes(self, episode_durations):
        episode_avg_duration = 0
        valid_episode_durations = []
        try:
            valid_episode_durations = [x for x in episode_durations if x > 0]
            #self.DLog("Found episode durations are: {}".format(valid_episode_durations))
            episode_avg_duration = int(sum(valid_episode_durations) / float(len(valid_episode_durations))) # May div zero
            #self.DLog("Calculated the average duration at {} mins".format(episode_avg_duration))
        except:
            pass
            #self.DLog("Error calculating an average episode duration")
        return episode_avg_duration * 60 * 1000

##### update Function #####
    def update(self, metadata, media, lang):
        self._log_function_entry('update')

        record = {
            'id':        media.id,
            'lang':      lang,
            'sorttitle': None,
            'title':     media.title,
            'year':      0, # TODO: Need a better default
        }
        Log('Update called for TV Show with id = ' + record['id'])

        try:
            mediafile = self.pms._find_mediafiles_for_id(record['id'])[0]
        except:
            Log("Error trying to find mediafile for id: '%s'" % record['id'])
            self.DLog("Traceback: %s" % traceback.format_exc())
            return

        if not Prefs['localmediaagent']:
            self.update_metadata_with_localmediaagent(metadata)

        record.update(self._extract_info_for_mediafile(mediafile))

        if not record['title']:
            record['title'] = "Unknown"
            if mediafile:
                title_guess = self._guess_title_by_mediafile(mediafile)
                if title_guess:
                    record['title'] = title_guess

        # initialize global storage for duration calculations
        Dict.Reset()
        duration_key = 'duration_'+record['id']  # duration_23542342352523432
        Dict[duration_key] = [0] * 200 # Dict['duration_23542342352523432'] = [0,0,0,0,.(200)]

        @parallelize
        def UpdateEpisodes():  # Grabs the season data
            self._update_episodes(media.id, duration_key)

        if not record.get('duration'):
            record['duration'] = self._set_duration_as_avg_of_episodes(Dict[duration_key])
        Dict.Reset()

        record['summary'] = self._build_show_summary(
            record,
            _get(Prefs, 'statusinsummary'),
            _get(Prefs, 'beforerating'),
            _get(Prefs, 'afterrating'),
            _get(Prefs, 'ratingspos'),
            _get(Prefs, 'preserverating'),
        )  # Summaries are complicated

        if True:
            #Transfer data to the metadata object
            for k in [
                'title', 'title_sort', 'original_title', 'rating',
                'content_rating', 'studio', 'originally_available_at',
                'tagline', 'summary', 'duration',
            ]:
                setattr(metadata, k, record[k])
            metadata.roles.clear()
            for actor in _get(record, 'actors', []):
                newrole = metadata.roles.new()
                newrole.name = actor.get('name')
                newrole.role = actor.get('role')
                newrole.photo = actor.get('photo')
            metadata.genres.clear()
            for genre in _get(record, 'genres', []):
                metadata.genres.add(genre)
            metadata.genres.discard('')
            metadata.collections.clear()
            for collection in _get(record, 'collections', []):
                metadata.collections.add(collection)
            metadata.collections.discard('')

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
        #self.DLog("Average series episode duration set to: {}".format(metadata.duration))



