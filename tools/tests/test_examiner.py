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
    return {"id": cid, "chapter": int(ch), "page": int(p), "topic": f"Topic of page {int(p)}", "type": "recall", "level": 1,
            "q": f"Question {cid}?", "a": "Answer.", "points": ["one", "two"], "facts": [f"p{int(p):03d}.f01"],
            "importance": imp(), **kw}


def chapter_file(cards, pages=None):
    pages = pages or {str(c["page"]): {"facts": ["a fact"]} for c in cards}
    return {"pages": pages, "cards": cards}


def imp(safety=1, decision=1, frequency=1, exam=1, core=1):
    return {"safety": safety, "decision": decision, "frequency": frequency, "exam": exam, "core": core, "why": "test"}


def bank_of(*cards):
    return {c["id"]: c for c in cards}


def item(n, result="correct", **kw):
    return {"n": n, "result": result, "points_hit": 2 if result == "correct" else kw.pop("points_hit", 1),
            "prompts": 0, "fluency": "fluent", "confidence": None, "note": "", "retry": None, **kw}


class RateTests(unittest.TestCase):
    def r(self, **kw):
        return lib.rate({"result": "correct", "points_hit": 4, "prompts": 0, "fluency": "fluent", **kw}, 4)[0]

    def test_rules(self):
        self.assertEqual(self.r(), Rating.Easy)
        self.assertEqual(self.r(fluency="hesitant"), Rating.Good)
        self.assertEqual(self.r(confidence="unsure"), Rating.Good)
        self.assertEqual(self.r(fluency="guessed"), Rating.Hard)
        self.assertEqual(self.r(prompts=1), Rating.Hard)
        self.assertEqual(self.r(prompts=2), Rating.Again)
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
                    {"importance": {**imp(), "safety": 4}}, {"importance": {**imp(), "why": ""}}, {"level": 5},
                    {"facts": []}, {"facts": ["f1"]}, {"q": "Why " * 50}, {"points": ["a"] * 5}):
            with self.assertRaises(ValueError): lib.check_card({**card("ch01.p002.01"), **bad})

    def test_merge_adds_and_replaces(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "ch01.json"
            self.assertEqual(lib.merge_cards(f, 1, "Pre-op", chapter_file([card("ch01.p002.02"), card("ch01.p002.01")])), (2, 0))
            self.assertEqual(lib.merge_cards(f, 1, "Pre-op", {"cards": [card("ch01.p002.01", a="New.")]}), (0, 1))
            b = lib.load_bank(Path(d))
            self.assertEqual(list(b), ["ch01.p002.01", "ch01.p002.02"]); self.assertEqual(b["ch01.p002.01"]["a"], "New.")
            with self.assertRaises(ValueError): lib.merge_cards(f, 1, "Pre-op", chapter_file([card("ch02.p040.01")]))
            with self.assertRaises(ValueError):  # a card may only test facts that are on the page list
                lib.merge_cards(f, 1, "Pre-op", {"cards": [card("ch01.p002.03", facts=["p002.f02"])]})
            self.assertEqual(lib.load_bank(Path(d))["ch01.p002.01"]["a"], "New.")  # the failed merge wrote nothing

    def test_qa_page_lists_every_question_and_answer_by_topic(self):
        data = {"chapter": 1, "title": "Pre-op", **chapter_file([card("ch01.p003.01"), card("ch01.p002.01", importance=imp(3, 3, 3, 3, 3))])}
        md = lib.qa_markdown(data)
        self.assertLess(md.index("## Topic of page 2"), md.index("## Topic of page 3"))
        self.assertEqual(md.count("**Q:**"), 2); self.assertEqual(md.count("**A:**"), 2); self.assertIn("A must know", md)

    def test_figures_are_checked_cut_from_the_book_and_put_on_their_cards(self):
        data = {"chapter": 1, "title": "Pre-op", **chapter_file([card("ch01.p019.01", figure="1.5"), card("ch01.p019.02")]),
                "figures": {"1.5": {"page": 19, "title": "Angiographic views"}}}
        lib.check_chapter(data)
        with self.assertRaises(ValueError): lib.check_chapter({**data, "figures": {}})
        pdf = next((ROOT / "Cardiothoracic_Surgery_Chapters").glob("Chapter_01_*.pdf"))
        with tempfile.TemporaryDirectory() as d:
            imgs = lib.render_figures(data, pdf, Path(d) / "media")
            self.assertEqual(imgs, {"1.5": "media/fig-1-5.png"})
            self.assertGreater((Path(d) / "media" / "fig-1-5.png").stat().st_size, 2000)
        cards = {c["id"]: c for c in lib.app_manifest(data, imgs)["cards"]}
        self.assertEqual(cards["ch01.p019.01"]["image"], "media/fig-1-5.png"); self.assertNotIn("image", cards["ch01.p019.02"])

    def test_coverage_finds_missing_pages_and_untested_facts(self):
        data = chapter_file([card("ch01.p002.01")], pages={"2": {"facts": ["NYHA I", "NYHA II"]}, "3": {"skip": "full-page figure"}})
        cv = lib.coverage(data, [2, 3, 4])
        self.assertEqual((cv["pages_done"], cv["pages_missing"], cv["facts"]), (2, [4], 2))
        self.assertEqual(cv["facts_untested"], ["p002.f02"]); self.assertEqual(cv["skipped"], {"3": "full-page figure"})
        with self.assertRaises(ValueError): lib.check_pages({"2": {"facts": []}})
        with self.assertRaises(ValueError): lib.check_pages({"2": {"facts": ["x"], "skip": "y"}})

    def test_book_page_from_running_head(self):
        self.assertEqual(lib.book_page("2    CHAPTER 1 Preoperative assessment\n\nx"), 2)
        self.assertEqual(lib.book_page("\n          CARDIOVASCULAR HISTORY           3\nx"), 3)
        self.assertEqual(lib.book_page("816    CHAPTER 17 Chest trauma"), 816)

    def test_real_chapter_pages_have_numbers(self):
        pdf = next((ROOT / "Cardiothoracic_Surgery_Chapters").glob("Chapter_01_*.pdf"))
        pages = lib.page_texts(pdf)
        self.assertEqual([p["page"] for p in pages[1:6]], [2, 3, 4, 5, 6])
        self.assertEqual(next(p["page"] for p in pages if p["pdf_page"] == 11), 11)  # a page without a running head
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
        self.assertEqual(len(lib.plan_session(b, st, NOW)["topics"]), 1)
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
        self.assertIn("STEP 1, FACTS", pr); self.assertIn("1 knowledge", pr)


class VivaTests(unittest.TestCase):
    def setUp(self):  # three pages, three topics, three cards each
        self.bank = bank_of(*(card(f"ch01.p00{p}.0{k}") for p in (2, 3, 4) for k in (1, 2, 3)))
        self.state = lib.load_state(Path("/nonexistent"))

    def run_session(self, results, now=NOW, topic_marks=None, **kw):
        plan = lib.plan_session(self.bank, self.state, now, **kw)
        rep = {"session": plan["session"], "items": [item(it["n"], **results.get(it["id"], {})) for it in plan["items"]]}
        if topic_marks: rep["topics"] = [{"t": t, "mark": m} for t, m in topic_marks.items()]
        return plan, lib.mark(plan, rep, self.state, self.bank, now)

    def test_plan_is_topics_with_two_examiners_climbing_the_ladder(self):
        self.bank["ch01.p002.01"]["level"] = 3; self.bank["ch01.p002.03"]["level"] = 2
        plan = lib.plan_session(self.bank, self.state, NOW, topics=3)
        self.assertEqual([t["examiner"] for t in plan["topics"]], [1, 1, 2])
        self.assertEqual(plan["minutes"], 15)
        t1 = [self.bank[i["id"]]["level"] for i in plan["items"] if i["t"] == 1]
        self.assertEqual(t1, sorted(t1))
        self.assertEqual({t["viva"] for t in plan["topics"]}, {"critical"})
        self.assertEqual(lib.plan_session(self.bank, self.state, NOW, viva="thoracic")["items"], [])

    def test_a_topic_holds_at_most_five_questions(self):
        self.bank = bank_of(*(card(f"ch01.p002.{k:02d}") for k in range(1, 9)))
        plan = lib.plan_session(self.bank, self.state, NOW)
        self.assertEqual((len(plan["topics"]), len(plan["items"])), (1, lib.Q_PER_TOPIC))

    def test_topic_sheet_no_topic_twice_in_a_day(self):
        plan, _ = self.run_session({}, topics=1)
        again = lib.plan_session(self.bank, self.state, NOW + timedelta(hours=1), topics=3)
        self.assertNotIn(plan["topics"][0]["topic"], [t["topic"] for t in again["topics"]])

    def test_mark_schedules_scores_topics_and_refuses_twice(self):
        plan, res = self.run_session({"ch01.p002.01": {"result": "wrong"}}, topics=1, topic_marks={1: 6})
        e = self.state["cards"]
        self.assertEqual(len(e), 3); self.assertIn(plan["session"], self.state["sessions"])
        self.assertLess(datetime.fromisoformat(e["ch01.p002.01"]["fsrs"]["due"]), datetime.fromisoformat(e["ch01.p002.02"]["fsrs"]["due"]))
        v = res["viva"]
        self.assertEqual((v["topics"][0]["mark"], v["total"], v["pass_total"], v["result"]), (6, 6, 6, "pass"))
        self.assertEqual(self.state["vivas"][0]["s"], plan["session"])
        with self.assertRaises(ValueError): lib.mark(plan, {"items": []}, self.state, self.bank, NOW)

    def test_auto_mark_when_the_examiner_gives_none(self):
        _, res = self.run_session({}, topics=3)  # all fluent and complete
        self.assertEqual([t["mark"] for t in res["viva"]["topics"]], [7, 7, 7])  # 8 needs a management-level rung
        a = card("ch01.p002.01", importance=imp(3, 3, 3, 3, 3))
        self.assertEqual(lib.auto_mark([(a, Rating.Again, {"confidence": "sure"})]), 4)  # dangerous
        self.assertEqual(lib.auto_mark([(card("ch01.p002.01", level=3), Rating.Easy, {})]), 8)
        self.assertEqual(lib.auto_mark([(a, Rating.Again, {}), (card("ch01.p002.02"), Rating.Good, {})]), 5)

    def test_topic_marks_alone_save_the_viva_and_leave_the_cards(self):
        plan = lib.plan_session(self.bank, self.state, NOW, topics=2)
        res = lib.mark(plan, {"topics": [{"t": 1, "mark": 6}, {"t": 2, "mark": 5}], "items": []}, self.state, self.bank, NOW)
        self.assertEqual((res["viva"]["total"], res["viva"]["partial"], self.state["cards"]), (11, True, {}))
        self.assertNotIn(plan["session"], self.state["sessions"])  # still open for the full report
        lib.mark(plan, {"items": [item(1)]}, self.state, self.bank, NOW)
        self.assertEqual([v.get("partial") for v in self.state["vivas"]], [None])  # the full report replaced it
        with self.assertRaises(ValueError): lib.mark(lib.plan_session(self.bank, self.state, NOW), {"items": []}, self.state, self.bank, NOW)

    def test_viva_fails_when_the_total_is_short(self):
        _, res = self.run_session({}, topics=3, topic_marks={1: 5, 2: 6, 3: 4})
        self.assertEqual((res["viva"]["total"], res["viva"]["result"], res["viva"]["bad_fails"]), (15, "fail", 1))

    def test_exam_mode_gives_no_feedback_until_the_debrief(self):
        plan = lib.plan_session(self.bank, self.state, NOW)
        pr = lib.examiner_prompt(plan, self.bank, self.state)
        self.assertIn("NO feedback", pr); self.assertIn("TOPIC 1 (Examiner 1)", pr); self.assertIn("6 pass:", pr)
        self.assertIn("practice mode", lib.examiner_prompt(lib.plan_session(self.bank, self.state, NOW, mode="practice"), self.bank, self.state).lower())

    def test_due_cards_come_back_and_confident_errors_lead(self):
        self.run_session({"ch01.p003.02": {"result": "wrong", "confidence": "sure"}}, topics=6)
        plan = lib.plan_session(self.bank, self.state, NOW + timedelta(days=30), new=0)
        self.assertEqual(plan["topics"][0]["topic"], "Topic of page 3")
        self.assertTrue(all(i["kind"] == "review" for i in plan["items"]))

    def test_failure_pulls_page_siblings_forward(self):
        self.run_session({}, topics=6)  # all Easy: due in about a week
        t = NOW + timedelta(days=1)
        self.state["cards"]["ch01.p002.01"]["fsrs"]["due"] = t.isoformat()
        plan = lib.plan_session(self.bank, self.state, t, new=0)
        self.assertEqual([i["id"] for i in plan["items"]], ["ch01.p002.01"])
        rows = lib.mark(plan, {"items": [item(1, "blank", points_hit=0)]}, self.state, self.bank, t)["rows"]
        self.assertEqual({r["id"] for r in rows if r["rating"] == "moved"}, {"ch01.p002.02", "ch01.p002.03"})
        self.assertEqual(self.state["cards"]["ch01.p002.02"]["fsrs"]["due"], (t + lib.NUDGE_TO).isoformat())

    def test_retry_and_notes_and_leech(self):
        self.bank = bank_of(card("ch01.p002.01"))
        t = NOW
        for k in range(lib.LEECH_LAPSES + 1):
            plan = lib.plan_session(self.bank, self.state, t, sid=f"S2026110{k}-0900")
            rep = {"items": [item(1, "wrong", note="mixed up class III and IV", retry={"result": "correct", "points_hit": 2, "prompts": 0})]}
            lib.mark(plan, rep, self.state, self.bank, t)
            t += timedelta(days=3)
        e = self.state["cards"]["ch01.p002.01"]
        self.assertEqual(e["history"][1]["why"][:6], "retry:"); self.assertEqual(e["history"][1]["r"], 3)
        self.assertEqual(e["lapses"], lib.LEECH_LAPSES); self.assertTrue(e["leech"])
        plan = lib.plan_session(self.bank, self.state, t)
        self.assertEqual(plan["items"], [{"n": 1, "id": "ch01.p002.01", "kind": "teach", "t": 0}])
        prompt = lib.examiner_prompt(plan, self.bank, self.state)
        self.assertIn("TEACH", prompt); self.assertIn("last time: mixed up class III and IV", prompt)
        lib.mark(plan, {"items": [item(1)]}, self.state, self.bank, t)
        self.assertFalse(self.state["cards"]["ch01.p002.01"]["leech"])

    def test_parse_report_from_chat_text(self):
        text = ('Here you go:\n```json\n{"session": "S20261101-0900", "topics": [{"t": 1, "mark": 7}], '
                '"items": [{"n": 1, "result": "partial", "points_hit": 1, "retry": {"result": "correct"}}]}\n```\nGood luck!')
        rep = lib.parse_report(text)
        self.assertEqual((rep["items"][0]["result"], rep["topics"][0]["mark"]), ("partial", 7))
        with self.assertRaises(ValueError): lib.parse_report('{"items": [{"n": 1, "result": "ok"}]}')
        with self.assertRaises(ValueError): lib.parse_report('{"topics": [{"t": 1, "mark": 9}], "items": []}')

    def test_one_page_holds_the_viva_and_the_schedule(self):
        plan, _ = self.run_session({"ch01.p002.01": {"result": "wrong"}}, topics=1, topic_marks={1: 5})
        nxt = lib.plan_session(self.bank, self.state, NOW + timedelta(days=1), sid="S20261102-0900")
        page = lib.viva_page(self.bank, self.state, NOW, nxt)
        for want in ("Part 1: the viva (S20261102-0900)", "Model answer:", "Part 2: spaced repetition", "Due now",
                     "| 2026-11-01 | S", "Memory per topic", "Weakest cards", "never work it out yourself"):
            self.assertIn(want, page)
        self.assertIn("No viva is planned", lib.viva_page(self.bank, self.state, NOW, None))

    def test_state_round_trips(self):
        self.run_session({}, topics=1)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "state.json"; lib.save_state(p, self.state)
            self.assertEqual(lib.load_state(p), json.loads(json.dumps(self.state)))


if __name__ == "__main__":
    unittest.main()
