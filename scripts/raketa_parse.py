"""Rule parser for @raketa_trevoga: oblast header lines, then "N [реактивний] БпЛА на TOWN" lines under them."""
import json, re, sys
HEAD = {
    "київщин": "kyivska", "київ": "kyiv", "чернігівщин": "chernihivska", "сумщин": "sumska", "харківщин": "kharkivska",
    "харків": "kharkivska", "полтавщин": "poltavska", "дніпропетровщин": "dnipropetrovska", "дніпровщин": "dnipropetrovska",
    "запоріжж": "zaporizka", "запорізьк": "zaporizka", "миколаївщин": "mykolaivska", "одещин": "odeska", "херсонщин": "khersonska",
    "кіровоградщин": "kirovohradska", "черкащин": "cherkaska", "вінниччин": "vinnytska", "житомирщин": "zhytomyrska",
    "рівненщин": "rivnenska", "волин": "volynska", "львівщин": "lvivska", "тернопільщин": "ternopilska",
    "хмельниччин": "khmelnytska", "франківщин": "ivano_frankivska", "прикарпатт": "ivano_frankivska", "закарпатт": "zakarpatska",
    "буковин": "chernivetska", "чернівеччин": "chernivetska", "донеччин": "donetska",
}

# Oblast centres as targets in headerless posts ("БпЛА на Одесу"), stems of the accusative forms.
CITY = {"київ": "kyiv", "рівн": "rivnenska", "запоріжж": "zaporizka", "кропивницьк": "kirovohradska", "сум": "sumska",
        "чернігів": "chernihivska", "одес": "odeska", "івано-франківськ": "ivano_frankivska", "луцьк": "volynska",
        "харків": "kharkivska", "дніпр": "dnipropetrovska", "полтав": "poltavska", "черкас": "cherkaska", "вінниц": "vinnytska",
        "житомир": "zhytomyrska", "львів": "lvivska", "тернопіл": "ternopilska", "хмельницьк": "khmelnytska",
        "ужгород": "zakarpatska", "чернівц": "chernivetska", "миколаїв": "mykolaivska", "херсон": "khersonska"}


def city(word):
    w = word.lower()
    for stem, rid in sorted(CITY.items(), key=lambda kv: -len(kv[0])):
        if w.startswith(stem) and len(w) - len(stem) <= 2:
            return rid
    return None


def header(line):
    l = line.strip().rstrip(":").strip().lower()
    if not l or len(l.split()) > 2:
        return None
    for stem, rid in sorted(HEAD.items(), key=lambda kv: -len(kv[0])):
        if l.startswith(stem) and (stem != "київ" or l in ("київ", "києві")):
            return rid
    return None

def parse(text):
    """-> list of (oblast, count, weapon) for threat lines under each header."""
    out, cur = [], None
    for line in text.split("\n"):
        h = header(line)
        if h:
            cur = h; continue
        m = re.search(r"(?:(\d+)\s*[хx]?\s*)?(реактивн\w*\s+)?(БпЛА|БПЛА|шахед\w*|ракет\w*|КАБ\w*)\s+(?:курсом\s+)?на\s", line, re.I)
        target = city(line[m.end():].split()[0]) if m and line[m.end():].split() else None
        if m and (cur or target):
            w = "missile" if m.group(3).lower().startswith("ракет") else "kab" if m.group(3).upper().startswith("КАБ") else "jet_drone" if m.group(2) else "shahed"
            out.append((cur or target, int(m.group(1) or 1), w))
    return out

if __name__ == "__main__":
    for line in open(sys.argv[1]):
        p = json.loads(line)
        print(json.dumps({"id": p["id"], "date": p["date"], "parsed": parse(p["text"])}, ensure_ascii=False))
