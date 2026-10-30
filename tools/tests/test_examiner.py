import json, sys, tempfile, unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from examiner import lib
from fsrs import Rating

NOW = datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)


def card(cid, **kw):
    ch, p, _ = lib.CARD_ID_RE.fullmatch(cid).groups()
    return {"id": cid, "chapter": int(ch), "page": int(p), "topic": "t", "type": "recall",
            "q": f"Question {cid}?", "a": "Answer.", "points": ["one", "two"], "importance": imp(), **kw}


def imp(safety=1, decision=1, frequency=1, exam=1, core=1):
    return {"safety": safety, "decision": decision, "frequency": frequency, "exam": exam, "core": core, "why": "test"}


def bank_of(*cards):
    return {c["id"]: c for c in cards}


def item(n, result="correct", **kw):
    return {"n": n, "result": result, "points_hit": 2 if result == "correct" else kw.pop("points_hit", 1),
            "hints": 0, "fluency": "fluent", "confidence": None, "note": "", "retry": None, **kw}


class RateTests(unittest.TestCase):
    def r(self, **kw):
        return lib.rate({"result": "correct", "points_hit": 4, "hints": 0, "fluency": "fluent", **kw}, 4)[0]

    def test_rules(self):
        self.assertEqual(self.r(), Rating.Easy)
        self.assertEqual(self.r(fluency="hesitant"), Rating.Good)
        self.assertEqual(self.r(confidence="unsure"), Rating.Good)
        self.assertEqual(self.r(fluency="guessed"), Rating.Hard)
        self.assertEqual(self.r(hints=1), Rating.Hard)
        self.assertEqual(self.r(hints=2), Rating.Again)
        self.assertEqual(self.r(result="partial", points_hit=2), Rating.Hard)
        self.assertEqual(self.r(result="partial", points_hit=1), Rating.Again)
        self.assertEqual(self.r(result="wrong"), Rating.Again)
        self.assertEqual(self.r(result="blank", points_hit=0), Rating.Again)
        self.assertEqual(self.r(override=3, result="wrong"), Rating.Good)

    def test_once_failed_card_is_never_easy(self):
        self.assertEqual(lib.rate({"result": "correct", "points_hit": 2, "fluency": "fluent"}, 2, lapses=1)[0], Rating.Good)


class BankTests(unittest.TestCase):
    def test_check_card(self):
        lib.check_card(card("ch01.p002.01", related=["ch01.p002.02"]))
        for bad in ({"type": "mcq"}, {"page": 3}, {"points": []}, {"extra": 1}, {"q": " "}, {"importance": {"safety": 1}},
                    {"importance": {**imp(), "safety": 4}}, {"importance": {**imp(), "why": ""}}):
            with self.assertRaises(ValueError): lib.check_card({**card("ch01.p002.01"), **bad})

    def test_merge_adds_and_replaces(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "ch01.json"
            self.assertEqual(lib.merge_cards(f, 1, "Pre-op", [card("ch01.p002.02"), card("ch01.p002.01")]), (2, 0))
            self.assertEqual(lib.merge_cards(f, 1, "Pre-op", [card("ch01.p002.01", a="New.")]), (0, 1))
            b = lib.load_bank(Path(d))
            self.assertEqual(list(b), ["ch01.p002.01", "ch01.p002.02"]); self.assertEqual(b["ch01.p002.01"]["a"], "New.")
            with self.assertRaises(ValueError): lib.merge_cards(f, 1, "Pre-op", [card("ch02.p040.01")])

    def test_book_page_from_running_head(self):
        self.assertEqual(lib.book_page("2    CHAPTER 1 Preoperative assessment\n\nx"), 2)
        self.assertEqual(lib.book_page("\n          CARDIOVASCULAR HISTORY           3\nx"), 3)
        self.assertEqual(lib.book_page("816    CHAPTER 17 Chest trauma"), 816)

    def test_real_chapter_pages_have_numbers(self):
        pdf = next((ROOT / "Cardiothoracic_Surgery_Chapters").glob("Chapter_01_*.pdf"))
        pages = lib.page_texts(pdf)
        self.assertEqual([p["page"] for p in pages[1:6]], [2, 3, 4, 5, 6])
        self.assertIn("book page 2", lib.qa_prompt(1, "Preoperative assessment", pages[1:2]))


class ImportanceTests(unittest.TestCase):
    def test_score_and_tiers(self):
        self.assertEqual(lib.importance_score(imp(3, 3, 3, 3, 3)), 100)
        self.assertEqual(lib.importance_score(imp(0, 0, 0, 0, 0)), 0)
        self.assertEqual(lib.tier(card("ch01.p002.01", importance=imp(3, 3, 2, 2, 1))), "A")
        self.assertEqual(lib.tier(card("ch01.p002.01", importance=imp(3, 0, 0, 0, 0))), "A")  # can kill: must know
        self.assertEqual(lib.tier(card("ch01.p002.01", importance=imp(1, 2, 2, 1, 1))), "B")
        self.assertEqual(lib.tier(card("ch01.p002.01", importance=imp(0, 0, 1, 1, 0))), "C")

    def test_must_know_cards_keep_higher_retention(self):
        a, c = card("ch01.p002.01", importance=imp(3, 3, 3, 3, 3)), card("ch01.p002.02", importance=imp(0, 0, 0, 0, 0))
        self.assertGreater(lib.scheduler_for(a).desired_retention, lib.scheduler_for(c).desired_retention)
        b = bank_of(a, c); st = lib.load_state(Path("/nonexistent"))
        plan = lib.plan_session(b, st, NOW, sid="S20261101-0900")
        lib.mark(plan, {"items": [item(1, fluency="hesitant"), item(2, fluency="hesitant")]}, st, b, NOW)
        due = {i: datetime.fromisoformat(e["fsrs"]["due"]) for i, e in st["cards"].items()}
        self.assertLessEqual(due[a["id"]], due[c["id"]])

    def test_calibration_warns_on_inflation(self):
        many = [card(f"ch01.p002.{k:02d}", importance=imp(3, 3, 3, 3, 3)) for k in range(1, 11)]
        self.assertTrue(lib.calibration(many)["warnings"])
        mixed = [card(f"ch01.p002.{k:02d}", importance=imp(*([3] * 5 if k <= 2 else [1] * 5 if k <= 6 else [0] * 5)))
                 for k in range(1, 11)]
        self.assertEqual(lib.calibration(mixed)["warnings"], [])

    def test_new_cards_come_most_important_first_across_chapters(self):
        b = bank_of(card("ch01.p002.01", importance=imp(0, 1, 1, 0, 0)), card("ch07.p300.01", importance=imp(3, 3, 3, 3, 2)),
                    card("ch03.p100.01", importance=imp(2, 2, 2, 2, 1)), card("ch01.p004.01", importance=imp(1, 2, 2, 1, 1)))
        st = lib.load_state(Path("/nonexistent"))
        order = [i["id"] for i in lib.plan_session(b, st, NOW, new=10)["items"]]
        self.assertEqual(order, ["ch07.p300.01", "ch03.p100.01", "ch01.p004.01", "ch01.p002.01"])
        only_a = [i["id"] for i in lib.plan_session(b, st, NOW, new=10, tiers=["A"])["items"]]
        self.assertEqual(only_a, ["ch07.p300.01"])
        ch1 = [i["id"] for i in lib.plan_session(b, st, NOW, new=10, chapters=[1])["items"]]
        self.assertEqual(ch1, ["ch01.p004.01", "ch01.p002.01"])

    def test_qa_prompt_explains_the_criteria(self):
        pr = lib.qa_prompt(1, "Pre-op", [{"pdf_page": 2, "page": 2, "text": "x"}])
        for k in lib.CRITERIA: self.assertIn(f"- {k} (weight", pr)
        self.assertIn('"importance": {"safety"', pr)


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.bank = bank_of(*(card(f"ch01.p00{p}.0{k}") for p in (2, 3, 4) for k in (1, 2, 3)))
        self.state = lib.load_state(Path("/nonexistent"))

    def run_session(self, results, now=NOW, **kw):
        plan = lib.plan_session(self.bank, self.state, now, **kw)
        rep = {"session": plan["session"], "items": [item(it["n"], **results.get(it["id"], {})) for it in plan["items"]]}
        return plan, lib.mark(plan, rep, self.state, self.bank, now)

    def test_equal_importance_falls_back_to_book_order_without_page_repeats(self):
        plan = lib.plan_session(self.bank, self.state, NOW, minutes=20, new=5)
        ids = [i["id"] for i in plan["items"]]
        self.assertEqual(sorted(ids), ["ch01.p002.01", "ch01.p002.02", "ch01.p002.03", "ch01.p003.01", "ch01.p003.02"])
        pages = [self.bank[i]["page"] for i in ids]
        self.assertFalse(any(a == b for a, b in zip(pages, pages[1:])), pages)
        self.assertTrue(all(i["kind"] == "new" for i in plan["items"]))

    def test_mark_schedules_and_refuses_twice(self):
        plan, rows = self.run_session({"ch01.p002.01": {"result": "wrong"}}, new=3)
        e = self.state["cards"]
        self.assertEqual(len(e), 3); self.assertIn(plan["session"], self.state["sessions"])
        self.assertLess(datetime.fromisoformat(e["ch01.p002.01"]["fsrs"]["due"]), datetime.fromisoformat(e["ch01.p002.02"]["fsrs"]["due"]))
        with self.assertRaises(ValueError): lib.mark(plan, {"items": []}, self.state, self.bank, NOW)

    def test_due_cards_come_back_most_forgotten_first_and_confident_errors_lead(self):
        self.run_session({"ch01.p002.02": {"result": "wrong", "confidence": "sure"}}, new=9, minutes=60)
        later = NOW + timedelta(days=30)
        plan = lib.plan_session(self.bank, self.state, later, new=0)
        self.assertEqual(plan["items"][0]["id"], "ch01.p002.02")
        self.assertTrue(all(i["kind"] == "review" for i in plan["items"]))

    def test_failure_pulls_page_siblings_forward(self):
        self.run_session({}, new=9, minutes=60)  # all Easy: due in about a week
        t = NOW + timedelta(days=1)
        self.state["cards"]["ch01.p002.01"]["fsrs"]["due"] = t.isoformat()
        plan = lib.plan_session(self.bank, self.state, t, new=0)
        self.assertEqual([i["id"] for i in plan["items"]], ["ch01.p002.01"])
        rep = {"items": [item(1, "blank", points_hit=0)]}
        rows = lib.mark(plan, rep, self.state, self.bank, t)
        moved = {r["id"] for r in rows if r["rating"] == "moved"}
        self.assertEqual(moved, {"ch01.p002.02", "ch01.p002.03"})
        self.assertEqual(self.state["cards"]["ch01.p002.02"]["fsrs"]["due"], (t + lib.NUDGE_TO).isoformat())

    def test_retry_and_notes_and_leech(self):
        self.bank = bank_of(card("ch01.p002.01"))
        t = NOW
        for k in range(lib.LEECH_LAPSES + 1):
            plan = lib.plan_session(self.bank, self.state, t, sid=f"S2026110{k}-0900")
            rep = {"items": [item(1, "wrong", note="mixed up class III and IV", retry={"result": "correct", "points_hit": 2, "hints": 0})]}
            lib.mark(plan, rep, self.state, self.bank, t)
            t += timedelta(days=3)
        e = self.state["cards"]["ch01.p002.01"]
        self.assertEqual(e["history"][1]["why"][:6], "retry:"); self.assertEqual(e["history"][1]["r"], 3)
        self.assertEqual(e["lapses"], lib.LEECH_LAPSES); self.assertTrue(e["leech"])
        plan = lib.plan_session(self.bank, self.state, t)
        self.assertEqual(plan["items"], [{"n": 1, "id": "ch01.p002.01", "kind": "teach"}])
        prompt = lib.examiner_prompt(plan, self.bank, self.state)
        self.assertIn("TEACH", prompt); self.assertIn("last time: mixed up class III and IV", prompt)
        lib.mark(plan, {"items": [item(1)]}, self.state, self.bank, t)
        self.assertFalse(self.state["cards"]["ch01.p002.01"]["leech"])

    def test_parse_report_from_chat_text(self):
        text = 'Here you go:\n```json\n{"session": "S20261101-0900", "items": [{"n": 1, "result": "partial", "points_hit": 1}]}\n```\nGood luck!'
        self.assertEqual(lib.parse_report(text)["items"][0]["result"], "partial")
        with self.assertRaises(ValueError): lib.parse_report('{"items": [{"n": 1, "result": "ok"}]}')

    def test_state_round_trips(self):
        self.run_session({}, new=2)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "state.json"; lib.save_state(p, self.state)
            self.assertEqual(lib.load_state(p), json.loads(json.dumps(self.state)))


if __name__ == "__main__":
    unittest.main()
