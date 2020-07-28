import logging
import re
import json

from queries import gen_answer, read_jsfile

# This module wants to handle parse trees for queries
HANDLE_TREE = True

# The context-free grammar for the queries recognized by this plug-in module
GRAMMAR = """

Query →
    QSmartDeviceQuery '?'?

QSmartDeviceQuery →
    QConnectQuery
    | QLightOnQuery
    | QLightOffQuery
    | QLightDimQuery
    | QLightColorQuery
    | QHubInfoQuery
    | QHomeLightSaturationQuery

# 'Connect smart device grammar'
QConnectQuery →
    "tengdu" "snjalltæki" | "tengdu" QLightQuery

# 'Lightswitch grammar'
QLightOnQuery →
    "kveiktu" "á"? QLightQuery QHomeInOrOnQuery QLightOnPhenonmenon
    | "kveiktu" QHomeInOrOnQuery QHomeDeviceQuery_þgf

QLightOffQuery →
    "slökktu" "á"? QLightQuery QHomeInOrOnQuery QLightOffPhenonmenon
    | "slökktu" QHomeInOrOnQuery QHomeDeviceQuery_þgf

QLightOnPhenonmenon → Nl

# $tag(keep) QLightOnPhenomenon
 
QLightOffPhenonmenon → Nl

# 'Dimmer switch grammar'
QLightDimQuery →
    "settu" QLightQuery QHomeWhereDeviceQuery "í" QLightPercentage
    | "settu" QHomeDeviceQuery_þf "í" QLightPercentage
    | "settu" "birtuna" QHomeWhereDeviceQuery "í" QLightPercentage

QLightPercentage →
    töl | to | tala

QHomeDeviceQuery/fall → Fyrirbæri/fall/kyn
 
QHomeWhereDeviceQuery → FsLiður

# 'Color change query'
QLightColorQuery →
    "settu"? QColorName_nf "ljós" "í" QLightOnPhenonmenon

QColorName/fall →
    Lo/fall/tala/kyn

$tag(keep) QColorName/fall

# Set the saturation of a light or group
QHomeLightSaturationQuery →
    "settu" QHomeLightSaturation QHomeWhereDeviceQuery "í" QLightPercentage

QHomeLightSaturation →
    'mettun' | 'mettunina'

QLightPercentage →
    töl | to | tala

QHomeDeviceQuery/fall → Fyrirbæri/fall/kyn
 
QHomeWhereDeviceQuery → FsLiður

# 'information about hub grammar'
QHubInfoQuery →
    "hvaða" QLightOrGroup "eru" "tengdir" 
    | "hvað" "er" "tengt"

QLightOrGroup →
    "ljós" | "hóp" | "hópa"

# 'Helper functions'
QLightQuery → 
    "ljós" | "ljósið" | "ljósin" | "ljósunum"

QLightNamePhenonmenon → Nl

QHomeInOrOnQuery →
    "í" | "á"

"""


def QConnectQuery(node, params, result):
    result.qtype = "ConnectSmartDevice"

def QLightOnPhenonmenon(node, params, result):
    result.subject = node.contained_text()

def QLightOnQuery(node, params, result):
    result.qtype = "LightOn"

def QLightOffQuery(node, params, result):
    result.qtype = "LightOff"

def QLightOffPhenonmenon(node, params, result):
    result.subject = node.contained_text()

def QLightNamePhenonmenon(node, params, result):
    result.subject = node.contained_text()

def QLightDimQuery(node, params, result):
    result.qtype = "LightDim"

def QLightPercentage(node, params, result):
    d = result.find_descendant(t_base="tala")
    if d:
        add_num(terminal_num(d), result)
    else:
        add_num(result._nominative, result)

def QLightColorQuery(node, params, result):
    result.qtype = "LightColor"

def QColorName(node, params, result):
    result.color = node.contained_text()

def QHubInfoQuery(node, params, result):
    result.qtype = "HubInfo"

def QHomeWhereDeviceQuery(node, params, result):
    result.subject = node.contained_text().split(" ")[1]

def QHomeDeviceQuery(node, params, result):
    result.subject = node.contained_text()

def QHomeLightSaturationQuery(node, params, result):
    result.qtype = "LightSaturation"

_FIX_MAP = {
    'Skrifstofan': 'skrifstofa',
    'Húsið': 'hús'
}

_NUMBER_WORDS = {
    "núll": 0,
    "einn": 1,
    "einu": 1,
    "tveir": 2,
    "tveim": 2,
    "tvisvar sinnum": 2,
    "þrír": 3,
    "þrisvar sinnum": 3,
    "fjórir": 4,
    "fjórum sinnum": 4,
    "fimm": 5,
    "sex": 6,
    "sjö": 7,
    "átta": 8,
    "níu": 9,
    "tíu": 10,
    "ellefu": 11,
    "tólf": 12,
    "þrettán": 13,
    "fjórtán": 14,
    "fimmtán": 15,
    "sextán": 16,
    "sautján": 17,
    "átján": 18,
    "nítján": 19,
    "tuttugu": 20,
    "þrjátíu": 30,
    "fjörutíu": 40,
    "fimmtíu": 50,
    "sextíu": 60,
    "sjötíu": 70,
    "áttatíu": 80,
    "níutíu": 90,
    "hundrað": 100,
    "þúsund": 1000,
    "milljón": 1e6,
    "milljarður": 1e9,
}

_COLOR_NAME_TO_CIE = {
    'gulur': 60 * 65535/360,
    'grænn': 120 * 65535/360,
    'ljósblár': 180 * 65535/360,
    'blár': 240 * 65535/360,
    'bleikur': 300 * 65535/360, 
    'rauður': 360 * 65535/360,
}

def parse_num(num_str):
    """ Parse Icelandic number string to float or int """
    num = None
    try:
        # Handle numbers w. Icelandic decimal places ("17,2")
        if re.search(r"^\d+,\d+", num_str):
            num = float(num_str.replace(",", "."))
        # Handle digits ("17")
        else:
            num = float(num_str)
    except ValueError:
        # Handle number words ("sautján")
        if num_str in _NUMBER_WORDS:
            num = _NUMBER_WORDS[num_str]
        # Ordinal number strings ("17.")
        elif re.search(r"^\d+\.$", num_str):
            num = int(num_str[:-1])
        else:
            num = 0
    except Exception as e:
        logging.warning("Unexpected exception: {0}".format(e))
        raise
    return num

def add_num(num, result):
    """ Add a number to accumulated number args """
    if "numbers" not in result:
        result.numbers = []
    if isinstance(num, str):
        result.numbers.append(parse_num(num))
    else:
        result.numbers.append(num)

def terminal_num(t):
    """ Extract numerical value from terminal token's auxiliary info,
        which is attached as a json-encoded array """
    if t and t._node.aux:
        aux = json.loads(t._node.aux)
        if isinstance(aux, int) or isinstance(aux, float):
            return aux
        return aux[0]

def sentence(state, result):
    """ Called when sentence processing is complete """
    q = state["query"]

    if "qtype" in result and result.qtype == "ConnectSmartDevice":
        # A non-voice answer is usually a dict or a list
        answer = "Skal gert"

        js = read_jsfile("connectHub.js")

        q.set_command(js)
        q.set_answer(dict(answer=answer), answer, answer)

    elif "qtype" in result and (result.qtype == "LightOn" or result.qtype == "LightOff"):

        onOrOff = 'true' if result.qtype == 'LightOn' else 'false'

        stofn = None

        for i, token in enumerate(q.token_list):
            if token.txt == result.subject:
                stofn = token[2][0].stofn
                stofn = _FIX_MAP.get(stofn) or stofn

        js = read_jsfile("lightService.js")
        js += f'main(\'{stofn}\', {onOrOff});'
        print('js')

        answer = f'{stofn} {onOrOff}'

        q.set_answer(dict(answer=answer), answer, answer)
        q.set_command(js)

    elif "qtype" in result and result.qtype == "LightDim":

        number = result.numbers[0]

        stofn = None

        for i, token in enumerate(q.token_list):
            if token.txt == result.subject:
                stofn = token[2][0].stofn
                stofn = _FIX_MAP.get(stofn) or stofn

        js = read_jsfile("lightService.js")
        js += f'main(\'{stofn}\', true, {number});'
        print('js')
        answer = stofn
        q.set_answer(dict(answer=answer), answer, answer)
        q.set_command(js)

    elif "qtype" in result and result.qtype == "LightColor":
        stofn_name = None
        stofn_color = None

        for i, token in enumerate(q.token_list):
            if token.txt == result.subject:
                stofn_name = token[2][0].stofn
                stofn_name = _FIX_MAP.get(stofn_name) or stofn_name
            if token.txt == result.color:
                options = token[2]
                for word_variation in options:
                    if word_variation.ordfl == 'lo' and word_variation.stofn in _COLOR_NAME_TO_CIE.keys():
                        stofn_color = word_variation.stofn
                        break
        
        js = read_jsfile("lightService.js")
        js += f'main(\'{stofn_name}\', true, null, {_COLOR_NAME_TO_CIE[stofn_color.lower()]});'

        answer = f'{stofn_color} {stofn_name}'
        q.set_answer(dict(answer=answer), answer, answer)
        q.set_command(js)
        print(js)

    elif "qtype" in result and result.qtype == "HubInfo":
        answer = "Skal gert"

        js = read_jsfile("lightInfo.js")

        q.set_command(js)
        q.set_answer(dict(answer=answer), answer, answer)

    elif "qtype" in result and result.qtype == "LightSaturation":
        number = result.numbers[0]
        stofn = None

        for i, token in enumerate(q.token_list):
            if token.txt == result.subject:
                stofn = token[2][0].stofn
                stofn = _FIX_MAP.get(stofn) or stofn

        js = read_jsfile("lightService.js")
        js += f'main(\'{stofn}\', undefined, undefined, undefined, sat = {number});'
        print('js')

        answer = f'{stofn} {number}'

        q.set_answer(dict(answer=answer), answer, answer)
        q.set_command(js)

    else:
        q.set_error("E_QUERY_NOT_UNDERSTOOD")
