"""

    Reynir: Natural language processing for Icelandic

    Stats query response module

    Copyright (C) 2019 Miðeind ehf.

       This program is free software: you can redistribute it and/or modify
       it under the terms of the GNU General Public License as published by
       the Free Software Foundation, either version 3 of the License, or
       (at your option) any later version.
       This program is distributed in the hope that it will be useful,
       but WITHOUT ANY WARRANTY; without even the implied warranty of
       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
       GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see http://www.gnu.org/licenses/.


    This module handles queries related to statistics about the query mechanism.

"""


from datetime import datetime, timedelta

from db import SessionContext
from db.models import Person, Query
from db.queries import QueryTypesQuery

from queries import gen_answer, natlang_seq
from routes.people import top_persons


_STATS_QTYPE = "Stats"


_NUM_PEOPLE_QUERIES = (
    "hvað þekkirðu margar manneskjur",
    "hvað þekkir þú margar manneskjur",
    "hvað þekkirðu marga einstaklinga",
    "hvað þekkir þú marga einstaklinga",
    "hvað þekkirðu mikið af fólki",
    "hvað þekkir þú mikið af fólki",
    "hversu marga einstaklinga þekkirðu",
    "hversu marga einstaklinga þekkir þú",
    "hversu margar manneskjur þekkirðu",
    "hversu margar manneskjur þekkir þú",
    "hve marga einstaklinga þekkirðu",
    "hve marga einstaklinga þekkir þú",
    "hve margar manneskjur þekkirðu",
    "hve margar manneskjur þekkir þú",
)


_NUM_QUERIES = (
    "hvað hefurðu fengið margar fyrirspurnir",
    "hvað hefur þú fengið margar fyrirspurnir",
    "hvað hefurðu fengið margar spurningar",
    "hvað hefur þú fengið margar spurningar",
    "hvað hefurðu svarað mörgum spurningum",
    "hvað hefur þú svarað mörgum spurningum",
    "hversu mörgum fyrirspurnum hefurðu svarað",
    "hversu mörgum fyrirspurnum hefur þú svarað",
    "hversu mörgum spurningum hefurðu svarað",
    "hversu mörgum spurningum hefur þú svarað",
    "hve mörgum fyrirspurnum hefurðu svarað",
    "hve mörgum fyrirspurnum hefur þú svarað",
    "hve mörgum spurningum hefurðu svarað",
    "hve mörgum spurningum hefur þú svarað",
)


_MOST_FREQ_QUERIES = (
    "hvað er fólk að spyrja þig mest um",
    "hvað er fólk að spyrja mest um",
    "hvað spyr fólk mest um",
    "hvað spyr fólk þig mest um",
    "hvað ertu mest spurð um",
    "hvað ert þú mest spurð um",
    "hvað ertu aðallega spurð um",
    "hvað ert þú aðallega spurð um",
    "hvað spyr fólk þig aðallega um",
    "hvaða fyrirspurnir eru algengastar",
    "hvaða spurningar eru algengastar",
    "hvers konar spurningar eru algengastar",
    "hvernig spurningar færðu mest af",
    "hvernig spurningar færð þú mest af",
)


_MOST_MENTIONED_PEOPLE_QUERIES = (
    "um hverja er verið að tala",
    "um hverja er verið að fjalla í fjölmiðlum",
    "um hverja er mest fjallað í fjölmiðlum",
    "um hverja er mest talað í fjölmiðlum",
    "hverjir eru mest áberandi í fjölmiðlum",
    "hverjir eru mest áberandi í fjölmiðlum þessa dagana",
    "hverjir eru áberandi í fjölmiðlum",
    "hverjir eru áberandi í fjölmiðlum þessa dagana",
    "hvaða fólk hefur verið mest í fjölmiðlum síðustu daga",
    "hvaða fólk er mest í fréttum",
    "hvaða fólk er mest í fréttum þessa dagana",
    "hvaða fólk hefur verið mest í fréttum",
    "hvaða fólk hefur verið mest í fréttum nýlega",
    "hvaða fólk hefur verið mest í fréttum undanfarið",
    "hvaða fólk hefur verið mest í fréttum upp á síðkastið",
    "hvaða fólk hefur verið mest í fréttum síðustu daga",
    "hverjir hafa verið mest í fréttum",
    "hverjir hafa verið mest í fréttum nýlega",
    "hverjir hafa verið mest í fréttum undanfarið",
    "hverjir hafa verið mest í fréttum upp á síðkastið",
    "hverjir hafa verið mest í fréttum síðustu daga",
    "hvaða fólk hefur verið mest í fjölmiðlum",
    "hvaða fólk hefur verið mest í fjölmiðlum nýlega",
    "hvaða fólk hefur verið mest í fjölmiðlum undanfarið",
    "hvaða fólk hefur verið mest í fjölmiðlum upp á síðkastið",
    "hvaða fólk hefur verið mest í fjölmiðlum síðustu daga",
    "hverjir hafa verið mest í fjölmiðlum",
    "hverjir hafa verið mest í fjölmiðlum nýlega",
    "hverjir hafa verið mest í fjölmiðlum undanfarið",
    "hverjir hafa verið mest í fjölmiðlum upp á síðkastið",
    "hverjir hafa verið mest í fjölmiðlum síðustu daga",
    "hverjir eru umtöluðustu einstaklingarnir á Íslandi",
    "hverjir eru umtalaðastir",
    "um hverja er mest talað",
    "um hverja er mest skrifað",
    "hverjir hafa verið áberandi í fjölmiðlum síðustu daga",
    "hverjir hafa verið áberandi í fjölmiðlum undanfarið",
    "hverjir hafa verið áberandi í fjölmiðlum nýlega",
    "hverjir hafa verið áberandi í fjölmiðlum upp á síðkastið",
)


def _gen_num_people_answer(q):
    """ Answer questions about person database. """
    with SessionContext(read_only=True) as session:
        qr = session.query(Person.id).count()

        answer = "Í gagnagrunni mínum eru {0} einstaklingar.".format(qr or "engir")
        voice = answer
        response = dict(answer=answer)

        q.set_expires(datetime.utcnow() + timedelta(hours=1))
        q.set_answer(response, answer, voice)
        q.set_key("NumPeople")
        q.set_qtype(_STATS_QTYPE)

        return True


_QUERIES_PERIOD = 30  # days


def _gen_num_queries_answer(q):
    """ Answer questions concerning the number of queries handled. """
    with SessionContext(read_only=True) as session:
        qr = (
            session.query(Query.id)
            .filter(
                Query.timestamp >= datetime.utcnow() - timedelta(days=_QUERIES_PERIOD)
            )
            .count()
        )

        answer = "Á síðustu {0} dögum hef ég svarað {1} fyrirspurnum.".format(
            _QUERIES_PERIOD, qr or "engum"
        )
        voice = answer
        response = dict(answer=answer)

        q.set_key("NumQueries")
        q.set_answer(response, answer, voice)
        q.set_qtype(_STATS_QTYPE)

        return True


_QTYPE_TO_DESC = {
    "Weather": "spurningum um veðrið",
    "Arithmetic": "reiknidæmum",
    "Special": "sérstökum fyrirspurnum",
    "Opinion": "spurningum um skoðanir mínar",
    "Random": "beiðnum um tölur af handahófi",
    "Title": "spurningum um einstaklinga",
    "Geography": "spurningum um landafræði",
    "Location": "spurningum um staðsetningu",
    "Stats": "spurningum um tölfræði",
    "Telephone": "beiðnum um að hringja í símanúmer",
    "Date": "spurningum um dagsetningar",
    "Currency": "spurningum um gjaldmiðla",
    "Wikipedia": "beiðnum um upplýsingar úr Wikipedíu",
}


def _gen_most_freq_queries_answer(q):
    """ Answer question concerning most frequent queries. """
    with SessionContext(read_only=True) as session:
        start = datetime.utcnow() - timedelta(days=_QUERIES_PERIOD)
        end = datetime.utcnow()
        qr = QueryTypesQuery.period(start=start, end=end, enclosing_session=session)

        if qr:
            top_qtype = qr[0][1]
            desc = _QTYPE_TO_DESC.get(top_qtype) or "óskilgreindum fyrirspurnum"
            answer = "Undanfarið hef ég mest svarað {0}.".format(desc)
        else:
            answer = "Ég hef ekki svarað neinum fyrirspurnum upp á síðkastið."

        response = dict(answer=answer)
        voice = answer

        q.set_expires(datetime.utcnow() + timedelta(hours=1))
        q.set_answer(response, answer, voice)
        q.set_qtype(_STATS_QTYPE)
        q.set_key("FreqQuery")

        return True


_MOST_MENTIONED_COUNT = 3  # Individuals
_MOST_MENTIONED_PERIOD = 7  # Days


def _gen_most_mentioned_answer(q):
    """ Answer questions about the most mentioned/talked about people in Iceland. """
    top = top_persons(limit=_MOST_MENTIONED_COUNT, days=_MOST_MENTIONED_PERIOD)
    if not top:
        return False  # We don't know (empty database?)

    answer = natlang_seq([t.get("name") for t in top])
    response = dict(answer=answer)
    voice = "Umtöluðustu einstaklingar síðustu daga eru {0}.".format(answer)

    q.set_expires(datetime.utcnow() + timedelta(hours=1))
    q.set_answer(response, answer, voice)
    q.set_qtype(_STATS_QTYPE)
    q.set_key("MostMentioned")

    return True


# Map hashable query category tuple to corresponding handler function
_Q2HANDLER = {
    _NUM_PEOPLE_QUERIES: _gen_num_people_answer,
    _NUM_QUERIES: _gen_num_queries_answer,
    _MOST_FREQ_QUERIES: _gen_most_freq_queries_answer,
    _MOST_MENTIONED_PEOPLE_QUERIES: _gen_most_mentioned_answer,
}


def handle_plain_text(q):
    """ Handle a plain text query about query statistics. """
    ql = q.query_lower.rstrip("?")

    for qset, handler in _Q2HANDLER.items():
        if ql in qset:
            return handler(q)

    return False
