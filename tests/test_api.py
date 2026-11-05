from fastapi.testclient import TestClient

from app.server import app, MAX_PATTERN, MAX_TEXT

client = TestClient(app)


def test_full_match():
    r = client.post("/api/analyze", json={"pattern": "a(b|c)*d", "text": "abcd"})
    assert r.status_code == 200
    body = r.json()
    assert body["result"] == {"matched": True}
    assert body["nfa"]["dot"].startswith("digraph")
    assert body["dfa"]["truncated"] is False
    assert len(body["trace"]) == 5
    assert body["ast"]["tree"]["type"] == "Concat"
    assert body["ast"]["dot"].startswith("digraph")
    # a(b|c)*d builds leaves before their parents, and the root last
    build = body["ast"]["build"]
    assert build[0] == {"node": 1, "parent": 0, "span": [0, 1], "kind": "char", "label": "a"}
    assert build[-1]["node"] == 0 and build[-1]["span"] == [0, 8]
    star = next(b for b in build if b["kind"] == "star")
    assert star["span"] == [1, 7]
    # first char 'a' takes exactly one symbol edge; the DFA ends accepting
    assert len(body["trace"][1]["taken"]) == 1
    assert body["trace"][-1]["dfa"] in body["dfa"]["accepting"]


def test_search_mode():
    r = client.post("/api/analyze", json={"pattern": "a+", "text": "baab a", "mode": "search"})
    assert r.json()["result"] == {"matches": [[1, 3], [5, 6]]}


def test_syntax_error():
    r = client.post("/api/analyze", json={"pattern": "a(b", "text": ""})
    assert r.status_code == 400
    assert r.json() == {"error": "Unclosed group '('", "position": 1}


def test_limits():
    r = client.post("/api/analyze", json={"pattern": "a" * (MAX_PATTERN + 1), "text": ""})
    assert r.status_code == 422
    r = client.post("/api/analyze", json={"pattern": "a", "text": "a" * (MAX_TEXT + 1)})
    assert r.status_code == 422


def test_index_served():
    r = client.get("/")
    assert r.status_code == 200
    assert "<html" in r.text.lower()
