import regex_engine


def spans(p, s):
    return list(regex_engine.compile(p).finditer(s))


def test_leftmost_longest():
    assert spans("a+", "baaab aa") == [(1, 4), (6, 8)]


def test_alternation_prefers_longest():
    # leftmost-longest (POSIX), unlike Python's leftmost-first
    assert spans("a|ab", "ab") == [(0, 2)]


def test_no_match():
    assert spans("z", "abc") == []
    assert regex_engine.compile("z").search("abc") is None


def test_empty_matches_advance():
    assert spans("x*", "ab") == [(0, 0), (1, 1), (2, 2)]


def test_findall():
    rx = regex_engine.compile(r"[a-z]+@[a-z]+\.com")
    assert rx.findall("mail bob@x.com or amy@yo.com!") == ["bob@x.com", "amy@yo.com"]
