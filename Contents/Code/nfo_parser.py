from utils import _get, _parse_dt, time_convert
import re


class NfoParser(object):
    def __init__(self, Prefs):
        self.Prefs = Prefs

    def _get_premier(self, nfo_xml):
        out = {}
        for key in ['aired', 'premiered', 'dateadded']:
            try:
                s = nfo_xml.xpath(key)[0].text
                if s:
                    dt = _parse_dt(s, _get(self.Prefs, 'dayfirst', False))
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
        matches = self.RE_MPAA_PAT.match(text)
        if matches.group('rating'):
            out = matches.group('rating')
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
