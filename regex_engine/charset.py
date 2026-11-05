"""A set of characters stored as sorted, non-overlapping codepoint ranges."""

MAX_CODEPOINT = 0x10FFFF


def _normalize(ranges):
    ranges = sorted(ranges)
    merged = []
    for lo, hi in ranges:
        if merged and lo <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
        else:
            merged.append((lo, hi))
    return tuple(merged)


def _complement(ranges):
    result = []
    prev = 0
    for lo, hi in ranges:
        if lo > prev:
            result.append((prev, lo - 1))
        prev = hi + 1
    if prev <= MAX_CODEPOINT:
        result.append((prev, MAX_CODEPOINT))
    return tuple(result)


class CharSet:
    __slots__ = ("ranges", "_label")

    def __init__(self, ranges, label=None):
        self.ranges = _normalize(ranges)
        self._label = label

    # ---- constructors -------------------------------------------------
    @classmethod
    def char(cls, ch):
        return cls([(ord(ch), ord(ch))])

    @classmethod
    def union(cls, sets, negated=False, label=None):
        ranges = [r for s in sets for r in s.ranges]
        ranges = _normalize(ranges)
        if negated:
            ranges = _complement(ranges)
        return cls(ranges, label)

    def negate(self, label=None):
        return CharSet(_complement(self.ranges), label)

    # ---- queries ------------------------------------------------------
    def matches(self, ch):
        cp = ord(ch)
        for lo, hi in self.ranges:
            if cp < lo:
                return False
            if cp <= hi:
                return True
        return False

    def contains_cp(self, cp):
        return self.matches(chr(cp))

    def __eq__(self, other):
        return isinstance(other, CharSet) and self.ranges == other.ranges

    def __hash__(self):
        return hash(self.ranges)

    def label(self):
        if self._label is not None:
            return self._label
        return describe_ranges(self.ranges)

    def __repr__(self):
        return f"CharSet({self.label()})"


def _show(cp):
    ch = chr(cp)
    specials = {"\n": "\\n", "\t": "\\t", "\r": "\\r", " ": "␣"}
    if ch in specials:
        return specials[ch]
    if ch in "\\[]^-":
        return "\\" + ch
    if not ch.isprintable():
        return f"\\u{cp:04x}"
    return ch


def describe_ranges(ranges):
    """Human-readable label for a set of ranges, e.g. 'a', '[a-z0-9]', '[^\\n]'."""
    if len(ranges) == 1 and ranges[0][0] == ranges[0][1]:
        ch = chr(ranges[0][0])
        return _show(ranges[0][0]) if ch not in "[]^-" else ch
    if not ranges:
        return "∅"
    # Prefer the shorter of the positive and negated descriptions.
    comp = _complement(ranges)
    size = sum(hi - lo + 1 for lo, hi in ranges)
    if comp and (size > 0x10000 or len(comp) < len(ranges)):
        if comp == ((10, 10),):
            return "."
        return "[^" + _body(comp) + "]"
    if not comp:
        return "any"
    return "[" + _body(ranges) + "]"


def _body(ranges):
    parts = []
    for lo, hi in ranges:
        if lo == hi:
            parts.append(_show(lo))
        elif hi == lo + 1:
            parts.append(_show(lo) + _show(hi))
        else:
            parts.append(f"{_show(lo)}-{_show(hi)}")
    return "".join(parts)


DIGIT = CharSet([(ord("0"), ord("9"))], "\\d")
WORD = CharSet([(ord("0"), ord("9")), (ord("A"), ord("Z")), (ord("a"), ord("z")), (ord("_"), ord("_"))], "\\w")
SPACE = CharSet([(ord(c), ord(c)) for c in " \t\n\r\f\v"], "\\s")
DOT = CharSet([(10, 10)]).negate(".")

CLASS_ESCAPES = {
    "d": DIGIT,
    "w": WORD,
    "s": SPACE,
    "D": DIGIT.negate("\\D"),
    "W": WORD.negate("\\W"),
    "S": SPACE.negate("\\S"),
}

CHAR_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "f": "\f", "v": "\v", "0": "\0"}
