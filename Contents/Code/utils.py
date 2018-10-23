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
