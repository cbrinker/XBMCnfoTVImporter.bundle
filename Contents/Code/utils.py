import htmlentitydefs
import logging
import os
import re
from dateutil.parser import parse

def time_convert(duration):
    if (duration <= 2):
        duration = duration * 60 * 60 * 1000 #h to ms
    elif (duration <= 120):
        duration = duration * 60 * 1000 #m to ms
    elif (duration <= 7200):
        duration = duration * 1000 #s to ms
    return duration

def _get(node, key, default=None):
    val = node.get(key)
    if val is None:
        return default
    return val

def check_file_paths(pathfns, ftype):
    for pathfn in pathfns:
        if os.path.isdir(pathfn):
            continue
        logging.debug("Trying {}".format(pathfn))
        if not os.path.exists(pathfn):
            continue
        else:
            logging.info("Found {} file {}".format(ftype, pathfn))
            return pathfn
    else:
        logging.info("No {} file found! Aborting!".format(ftype))

def remove_empty_tags(xmltags):
    logging.debug('Removing remaining empty XML Tags from episode nfo...')
    for xmltag in xmltags.iter("*"):
        if len(xmltag):
            continue
        if xmltag.getparent() is None:
            continue
        if xmltag.text and xmltag.text.strip():
            continue
        logging.debug("Removing empty XMLTag: {}".format(xmltag.tag))
        xmltag.getparent().remove(xmltag)
    return xmltags


def unescape(text):
    """
    Removes HTML or XML character references and entities from a text string.
    Copyright: http://effbot.org/zone/re-sub.htm October 28, 2006 | Fredrik Lundh
    @param text The HTML (or XML) source text.
    @return The plain text, as a Unicode string, if necessary.
    """
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

def _parse_dt(text, dayfirst=False):
    out = None
    try:
        out = parse(text, dayfirst=(True if dayfirst else None))
    except:
        pass
    return out
