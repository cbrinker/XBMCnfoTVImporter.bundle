import logging
import re

from utils import _get, _parse_dt, time_convert


class NfoParser(object):
    def __init__(self, Prefs):
        self.prefs = Prefs

    def _get_premier(self, nfo_xml):
        out = {}
        for key in ['aired', 'premiered', 'dateadded']:
            try:
                s = nfo_xml.xpath(key)[0].text
                if s:
                    dt = _parse_dt(s, _get(self.prefs, 'dayfirst', False))
                    if dt:
                        out['originally_available_at'] = dt
                    break
            except:
                pass
        return out

    def _get_ratings(self, nfo_xml):
        out = {}

        rating = 0.0
        try:
            rating_vals = nfo_xml.xpath(".//rating/value")
            rating_text = rating_vals[0].text
            rating = rating_text.replace(',', '.')
            rating = round(float(rating), 1)
            out['rating'] = rating
        except:
            pass
        return out

    RE_MPAA_PAT = re.compile(r'(Rated\s)?(?P<rating>[A-z0-9-+/.]+(\s[0-9]+[A-z]?)?)?')
    def _parse_rating(self, text):
        out = 'NR'
        try:
            matches = self.RE_MPAA_PAT.match(text)
            if matches.group('rating'):
                out = matches.group('rating')
        except:
            pass
        return out

    RE_BEGIN_INT_PAT = re.compile('^([0-9]+)')
    def _get_duration_ms(self, nfo_xml):
        out = {}
        for key in ['durationinseconds', 'runtime']:
            try:
                v = nfo_xml.xpath(".//{}".format(key))[0].text
                v = int(self.RE_BEGIN_INT_PAT.findall(v)[0])
                if key == 'durationinseconds':
                    v *= 1000
                elif key == 'runtime':
                    v = time_convert(v)
                if v:
                    out['duration'] = v
                    break
            except:
                pass
        return out

    def _get_directors(self, nfo_xml):
        out = {}
        directors = []
        try:
            for node in nfo_xml.xpath('director'):
                value = node.text.split("/")
                directors += [x.strip() for x in value]
            if len(directors):
                out['directors'] = sorted(list(set(directors)))
        except:
            pass
        return out

    def _get_credits(self, nfo_xml):
        out = {
            'producers': [],
            'writers': [],
            'guest_stars': [],
        }
        try:
            for node in nfo_xml.xpath('credits'):
                for credit in node.text.split("/"):
                    if re.search("(Producer)", credit, re.IGNORECASE):
                        credit = re.sub ("\(Producer\)","",credit,flags=re.I).strip()
                        out['producers'].append(credit)
                    elif re.search("(Guest Star)", credit, re.IGNORECASE):
                        credit = re.sub ("\(Guest Star\)","",credit,flags=re.I).strip()
                        out['guest_stars'].append(credit)
                    elif re.search("(Writer)", credit, re.IGNORECASE):
                        credit = re.sub ("\(Writer\)","",credit,flags=re.I).strip()
                        out['writers'].append(credit)
                    else:
                        out['writers'].append(credit) # Unknown
        except:
            pass
        for k, v in out.items():
            if len(v) == 0:
                del out[k]
        return out

    PERCENT_RATINGS = {
      'rottentomatoes','rotten tomatoes','rt','flixster'
    }
    def _get_alt_ratings(self, nfo_xml):
        #return of: {'atr_ratings': [(provider,rating)]}

        if not _get(self.prefs, 'altratings'):
            return {}

        allowed_ratings = _get(self.prefs, 'ratings')
        if not allowed_ratings:
            allowed_ratings = "ALL"

        additional_ratings = []
        try:
            additional_ratings = nfo_xml.xpath('//ratings')
            if not additional_ratings:
                return {}  # Not Found in xml, abort
        except:
            pass

        alt_ratings = []
        for additional_rating in additional_ratings:
            for rating_node in additional_rating:
                try:
                    rating_provider = str(rating_node.attrib['moviedb'])
                    value = str(rating_node.text.replace(',', '.'))
                    if rating_provider.lower() in self.PERCENT_RATINGS:
                        value = value + "%"
                    if allowed_ratings == "ALL" or rating_provider in allowed_ratings:
                        alt_ratings.append((rating_provider, value))
                except:
                    logging.debug("Skipping additional rating without moviedb attribute!")
        if len(alt_ratings):
            return {'alt_ratings': alt_ratings}
        else:
            return {}

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

    def _get_actors(self, nfo_xml):
        out = {}
        actor_nodes = None
        try:
            actor_nodes = nfo_xml.xpath('actor')
        except:
            pass

        if not actor_nodes:
            return out 

        seen_roles = []
        out['actors'] = []
        for n, actor_node in enumerate(actor_nodes):
            actor = {  # Defaulting to unknown
                'name': 'Unknown Actor {}'.format(n+1),
                'role': 'Unknown Role {}'.format(n+1),
            }

            try:
                actor['name'] = actor_node.xpath('name')[0].text.strip()
            except:
                pass

            try:
                role = actor_node.xpath('role')[0].text.strip()
                role_seen_count = seen_roles.count(role)
                if role_seen_count:
                    actor['role'] = '{} {}'.format(role, role_seen_count+1)
                else:
                    actor['role'] = role
                seen_roles.append(role)
            except:
                pass

            try:
                actor['thumb'] = actor_node.xpath('thumb')[0].text.strip()
            except:
                pass

            out['actors'].append(actor)
        return out
