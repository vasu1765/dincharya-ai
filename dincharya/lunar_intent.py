"""Deterministic extraction for bounded English, Hindi and Hinglish lunar requests."""
from datetime import date, timedelta
import re
import unicodedata

DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
TITLE = re.compile(r'"([^"\n]+)"|“([^”\n]+)”')
LUNAR = re.compile(r"(?<!\w)(?:lunar|tithi|tithi-based|panchang|amanta|purnimanta|purnimant|"
                   r"तिथि|पंचांग|चंद्र|अमांत|अमान्त|पूर्णिमांत|पूर्णिमान्त)(?!\w)", re.I)
DAY = r"\d{4}-\d{2}-\d{2}"
CLOCK = r"(?:[01]\d|2[0-3]):[0-5]\d"
FIELDS = {
    "convention": {"amanta": "amanta अमांत अमान्त", "purnimanta": "purnimanta purnimant पूर्णिमांत पूर्णिमान्त"},
    "paksha": {"shukla": "shukla shukl शुक्ल", "krishna": "krishna krishn कृष्ण"},
    "intercalation": {"ordinary": "ordinary regular samanya सामान्य", "adhika": "adhika adhik अधिक",
                      "both": "both dono दोनों"},
    "repeated": {"first": "first pehli pehla पहली पहला", "last": "last aakhiri aakhri आखिरी अंतिम",
                 "review": "review समीक्षा"},
    "purpose": {"birthday": "birthday janmadin जन्मदिन", "wedding_anniversary": "anniversary salgirah सालगिरह वर्षगांठ",
                "monthly": "monthly mahine मासिक"},
    "month": {
        "chaitra": "chaitra chait चैत्र चैत", "vaishakha": "vaishakha vaishakh वैशाख",
        "jyeshtha": "jyeshtha jyeshth jyeshta ज्येष्ठ", "ashadha": "ashadha ashadh आषाढ़ आषाढ",
        "shravana": "shravana shravan saavan श्रावण सावन", "bhadrapada": "bhadrapada bhadrapad भाद्रपद",
        "ashvina": "ashvina ashwin ashvin आश्विन अश्विन", "kartika": "kartika kartik कार्तिक",
        "margashirsha": "margashirsha margashirsh मार्गशीर्ष", "pausha": "pausha paush पौष",
        "magha": "magha magh माघ", "phalguna": "phalguna phalgun फाल्गुन",
    },
}
TITHIS = (
    "pratipada प्रतिपदा", "dwitiya dvitiya द्वितीया", "tritiya तृतीया", "chaturthi चतुर्थी",
    "panchami पंचमी", "shashthi shashti षष्ठी", "saptami सप्तमी", "ashtami अष्टमी",
    "navami नवमी", "dashami दशमी", "ekadashi एकादशी", "dwadashi dvadashi द्वादशी",
    "trayodashi त्रयोदशी", "chaturdashi चतुर्दशी", "purnima poornima पूर्णिमा amavasya अमावस्या",
)
FILLER = frozenset((
    "please schedule remind reminder set me on in at for from to between and year "
    "during lunar tithi tithi-based panchang paksha paksh date ist asia/kolkata delhi "
    "new time repeat repeated sunrise mas maas month of the ka ki ke ko par mein me "
    "baje yaad dilao dila dena kar do lagao mujhe se tak rakh ke liye "
    "कृपया मुझे में को पर से तक बजे याद दिलाओ दिलाना करो लगाओ रखो के लिए और की "
    "तिथि पंचांग चंद्र पक्ष वर्ष साल समय दिल्ली माह मास महीना अगर दो बार सूर्योदय"
).split())
EXAMPLE = ('Example / उदाहरण: Remind me "Family puja" on lunar Chaitra Shukla Navami, '
           'Purnimanta, ordinary, first, in 2027 at 18:00 IST.')


class Clarify(ValueError):
    """A bounded request could not supply a unique complete intent."""


def _choice(words, field, aliases):
    lookup = {name: value for value, names in aliases.items() for name in names.split()}
    hits = {lookup[w] for w in words if w in lookup}
    if len(hits) > 1:
        raise Clarify(f"Choose one {field}.")
    return next(iter(hits), None), lookup.keys()


def parse_request(text):
    if not isinstance(text, str) or not 1 <= len(text) <= 1200:
        raise Clarify("Send a short scheduling request.")
    normalized = unicodedata.normalize("NFC", text)
    titles = list(TITLE.finditer(normalized))
    if len(titles) != 1:
        raise Clarify('Give one appointment title in double quotes.')
    original_title = titles[0].group(1) or titles[0].group(2)
    if any(unicodedata.category(c).startswith("C") and c not in "\u200c\u200d" for c in original_title):
        raise Clarify("Use a plain appointment title.")
    title = " ".join(original_title.split())
    if not 1 <= len(title) <= 80:
        raise Clarify("Keep the quoted title between 1 and 80 characters.")
    request = TITLE.sub(" ", normalized).translate(DIGITS).casefold()
    # Explicit Delhi civil date window and 24-hour start time.
    days = re.findall(rf"(?<![\d-]){DAY}(?![\d-])", request)
    request = re.sub(rf"(?<![\d-]){DAY}(?![\d-])", " ", request)
    times = re.findall(rf"(?<![\d:]){CLOCK}(?![\d:])", request)
    request = re.sub(rf"(?<![\d:]){CLOCK}(?![\d:])", " ", request)
    years = re.findall(r"(?<!\d)20\d{2}(?!\d)", request)
    request = re.sub(r"(?<!\d)20\d{2}(?!\d)", " ", request)
    try:
        if len(days) in (1, 2) and not years:
            start = date.fromisoformat(days[0])
            end = date.fromisoformat(days[-1]) + timedelta(days=1)
        elif len(years) == 1 and not days:
            start, end = date(int(years[0]), 1, 1), date(int(years[0]) + 1, 1, 1)
        else:
            raise Clarify("Give one year, one ISO date, or two ISO dates.")
    except (ValueError, OverflowError):
        raise Clarify("Give one year, one ISO date, or two valid ISO dates.") from None
    if not 0 < (end - start).days <= 366 or len(times) != 1:
        raise Clarify("Give one Delhi search window and one HH:MM time in IST.")
    words = request.translate(str.maketrans({c: " " for c in ",.!?;()।"})).split()
    consumed = set(FILLER)
    fields = {}
    for field, aliases in FIELDS.items():
        fields[field], recognized = _choice(words, field, aliases)
        consumed.update(recognized)
    tithis = {i: f"{i} {names}" for i, names in enumerate(TITHIS, 1)}
    tithi, recognized = _choice(words, "tithi", tithis)
    consumed.update(recognized)
    if set(words) - consumed:
        raise Clarify("I could not interpret part of the request. Use the supported Delhi lunar format.")
    if words.count("from") != words.count("to") or words.count("between") > 1 or (
            ("from" in words or "between" in words) and len(days) != 2):
        raise Clarify("Use a complete date range or one date.")
    for names, opposite in (({"purnima", "poornima", "पूर्णिमा"}, "krishna"),
                            ({"amavasya", "अमावस्या"}, "shukla")):
        if names.intersection(words) and fields["paksha"] == opposite:
            raise Clarify("The named tithi and paksha disagree.")
    if ({"purnima", "poornima", "पूर्णिमा"}.intersection(words)
            and {"amavasya", "अमावस्या"}.intersection(words)):
        raise Clarify("Choose Purnima or Amavasya.")
    required = ["convention", "paksha", "intercalation"]
    missing = [field for field in required if fields[field] is None]
    if tithi is None:
        missing.append("tithi")
    purpose = fields.pop("purpose") or "monthly"
    if purpose != "monthly" and fields["month"] is None:
        missing.append("lunar month")
    if missing:
        raise Clarify("Specify " + ", ".join(missing) + ".")
    fields["repeated"] = fields["repeated"] or "review"
    return dict(title=title, purpose=purpose, start=start.isoformat(), end=end.isoformat(),
                time=times[0], rule=dict(fields, tithi=tithi, birth_basis="explicit_rule"))
