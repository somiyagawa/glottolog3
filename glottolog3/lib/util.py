import re

from sqlalchemy import or_, not_, func, cast, Integer, literal_column, union

from clld.util import slug
from clld.db.meta import DBSession

from glottolog3.models import Provider, Macroarea, Doctype, Languoid, LegacyCode


PAGES_PATTERN = re.compile(':(?P<pages>[0-9]+(\-[0-9]+)?(,\s*[0-9]+(\-[0-9]+)?)*)')
REF_PATTERN = re.compile('\*\*(?P<id>[0-9]+)\*\*(?P<comment>[^\*]*)')
REF_PATTERN2 = re.compile('\*\*(?P<id>[0-9]+)\*\*')
YEAR_PATTERN = re.compile('[0-9]{4}$')
NUMERALMAP = zip(
    (1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1),
    ('M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I')
)


def roman_to_int(n):
    """convert Roman numbers to integers for the computation of pagenumbers"""
    n = unicode(n).upper()
    i = result = 0
    for integer, numeral in NUMERALMAP:
        while n[i:i + len(numeral)] == numeral:
            result += integer
            i += len(numeral)
    return result


def get_map(type_):
    """When resolving relations in source files to objects in the DB we have to work
    around some inconsistencies.
    """
    _get_map = lambda cls, attr='name': dict(
        (getattr(obj, attr), obj) for obj in DBSession.query(cls))
    if type_ == Provider:
        map_ = _get_map(Provider, 'id')
        map_['ozbib2'] = map_['ozbib']
        map_['fabreall2009ann'] = map_['fabre']
        map_['fabreall2009'] = map_['fabre']
        map_['sn'] = map_['nordhoff']
        map_['umi'] = map_['hh']
        map_['eballiso2009'] = map_['eball']
        map_['sealang'] = map_['sala']
        map_['hedvigtirailleur'] = map_['skirgard']
    elif type_ == Macroarea:
        map_ = _get_map(Macroarea)
        map_['Middle America'] = map_['North America']
        map_['Papua'] = map_['Papunesia']
        map_['Afria'] = map_['Africa']
    elif type_ == Doctype:
        map_ = _get_map(Doctype)
        map_['sociolinguistic'] = map_['socling']
    else:
        raise ValueError
    return map_


def glottocode(name, session, codes=None):
    letters = slug(name)[:4].ljust(4, 'a')
    active = session.query(cast(func.substring(Languoid.id, 5), Integer).label('number'))\
        .filter(Languoid.id.startswith(letters))
    legacy = session.query(cast(func.substring(LegacyCode.id, 5), Integer).label('number'))\
        .filter(LegacyCode.id.startswith(letters))
    number = session.query(func.coalesce(func.max(literal_column('number') + 1), 1234))\
        .select_from(union(active, legacy)).scalar()
    number = str(number)
    assert len(number) == 4
    res = letters + number
    if codes is not None:
        i = 0
        while res in codes:
            i += 1
            res = letters + str(int(number) + i)
        codes[res] = True
    return res
