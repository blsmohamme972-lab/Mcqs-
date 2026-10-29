import json, re, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from booklessons import lib
from motioncards.lib.lesson import check_lesson
from motioncards.lib.spec import QID_RE


class BookLessonTests(unittest.TestCase):
    def setUp(self):
        self.ch = json.loads((ROOT / "booklessons/chapters/ch01.json").read_text(encoding="utf-8"))

    def test_qids_pass_the_engine_rule_and_are_unique(self):
        ids = [lib.qid_for(1, t["n"]) for t in self.ch["topics"]]
        self.assertTrue(all(QID_RE.fullmatch(q) for q in ids)); self.assertEqual(len(ids), len(set(ids)))

    def test_every_topic_makes_a_valid_lesson_of_about_a_minute(self):
        for t in self.ch["topics"]:
            q = lib.qid_for(1, t["n"]); spec = lib.lesson_spec(t, q, "../images/x.png", 1600, 900, "breeze")
            check_lesson(spec, q)
            words = sum(len(l["text"].split()) for l in spec["lines"])
            self.assertTrue(95 <= words <= 140, (t["id"], words))
            self.assertTrue(all(ln["shot"] < len(spec["shots"]) for ln in spec["lines"]))
            self.assertNotIn("question", spec)

    def test_spoken_forms_are_kept(self):
        t = next(x for x in self.ch["topics"] if x["id"].endswith("mi-pci"))
        self.assertTrue(any("say" in lib.line_obj(l) for l in t["lines"]))

    def test_prompts_carry_the_story_rules(self):
        self.assertIn(lib.STORY_RULES, lib.prompt_for(self.ch["topics"][1], self.ch["chapter_title"]))


if __name__ == "__main__":
    unittest.main()
