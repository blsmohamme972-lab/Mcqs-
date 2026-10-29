"""Image lessons (motioncards/lib/lesson.py): spec checks and a scene that passes the real v2 validator."""
import importlib.util
import unittest
from types import SimpleNamespace as NS
from motioncards.lib import lesson
from motioncards.lib.lesson import check_lesson, build_scene
from motioncards.lib.compiler import validate_scene

QID = "Q000000001"
AVIF = b"\x00\x00\x00\x1cftypavif" + b"\x00" * 64            # header is what the asset check reads
SPEC = {"qid": QID, "image": "a.png", "takeaway": "PSC: beaded bile ducts.", "engine": "breeze",
        "voices": {"D": "doctor-man", "S": "student-woman"}, "names": {"D": "Doctor", "S": "Student"},
        "shots": [{"x": 800, "y": 450, "z": 1}, {"x": 1200, "y": 160, "z": 2.5, "spot": [1200, 160, 190]}],
        "lines": [{"who": "D", "text": "(clears throat) Good morning.", "shot": 0, "tag": "voice design"},
                  {"who": "S", "text": "So what happens to the ducts?", "shot": 1, "dir": "curious"}]}
TRACK = {"track_ms": 6400, "cues": [{"t_ms": 500, "end_ms": 2500, "text": "(clears throat) Good morning."},
                                    {"t_ms": 2950, "end_ms": 5800, "text": "So what happens to the ducts?"}]}


class Lessons(unittest.TestCase):
    def test_spec_defaults_and_errors_name_the_field(self):
        s = check_lesson(dict(SPEC), QID)
        self.assertEqual((s["gap_ms"], s["tempo"], s["lang"]), (450, 1.0, "en-us"))
        bad = [({**SPEC, "qid": "Q000000002"}, "qid must be"), ({**SPEC, "shots": []}, "shots must be"),
               ({**SPEC, "lines": [{"text": "x", "shot": 5}]}, r"lines\[0\].shot"), ({**SPEC, "colour": 1}, "unknown fields colour"),
               ({**SPEC, "shots": [{"x": 1, "y": 1, "z": 9}]}, r"shots\[0\].z"), ({**SPEC, "takeaway": "x" * 241}, "240")]
        for spec, msg in bad:
            with self.subTest(msg):
                with self.assertRaisesRegex(ValueError, msg): check_lesson(spec, QID)

    def test_scene_is_landscape_valid_and_lasts_past_the_voice(self):
        scene = build_scene(check_lesson(dict(SPEC), QID), QID, AVIF, 1600, 900, TRACK)
        self.assertEqual((scene["stage"]["width"], scene["stage"]["height"]), (960, 540))
        self.assertGreaterEqual(scene["duration_ms"], TRACK["track_ms"] + 300)
        self.assertTrue(scene["assets"]["img"].startswith("data:image/avif;base64,"))
        validate_scene(scene, QID, scene["duration_ms"])
        self.assertIn('"who":"S"', scene["script"]); self.assertIn("function render(t, api)", scene["script"])

    def test_intro_question_then_answer_then_explanation(self):
        spec = {**SPEC, "question": {"text": "Which ducts are beaded?"}, "answer": {"text": "The bile ducts", "say": "The bile ducts."}}
        bad = [({**SPEC, "question": {"text": "x"}}, "go together"), ({**spec, "answer": {"text": "x" * 111}}, r"answer.text"),
               ({**spec, "question": {"text": "q", "colour": 1}}, "question: unknown fields")]
        for b, msg in bad:
            with self.subTest(msg):
                with self.assertRaisesRegex(ValueError, msg): check_lesson(b, QID)
        track = {"track_ms": 12000, "cues": [{"t_ms": 500, "end_ms": 2500, "text": "Which ducts are beaded?", "kind": "question"},
                                             {"t_ms": 2950, "end_ms": 4000, "text": "The bile ducts", "kind": "answer"}]
                 + [{**c, "t_ms": c["t_ms"] + 5000, "end_ms": c["end_ms"] + 5000} for c in TRACK["cues"]]}
        scene = build_scene(check_lesson(spec, QID), QID, AVIF, 1600, 900, track)
        validate_scene(scene, QID, scene["duration_ms"])
        self.assertIn('"intro":{"q":{"t":500', scene["script"]); self.assertIn('"out":4350', scene["script"])
        self.assertIn('id="lesson-q-text"', scene["svg"]); self.assertIn("ANSWER", scene["svg"])
        self.assertIn('{"x":800.0,"y":450.0,"z":1}', scene["script"])   # the whole picture behind the intro

    @unittest.skipUnless(importlib.util.find_spec("numpy"), "numpy is only installed in the voice venv")
    def test_word_times_follow_the_heard_words_and_fill_the_rest(self):
        import numpy as np
        clip = np.zeros(24000 * 3, np.float32); clip[2400:24000 * 3 - 2400] = 0.1     # speech from 100 to 2900 ms
        heard = [("A", 0.10, 0.25), ("thirty", 0.30, 0.60), ("five", 0.60, 0.90), ("year", 0.95, 1.20), ("old", 1.20, 1.40),
                 ("man's", 1.45, 1.80), ("ECG", 1.90, 2.40)]
        class Fake:
            def transcribe(self, x, **kw):
                return [NS(words=[NS(word=" " + w, start=a, end=b) for w, a, b in heard])], None
        lesson._ASR[:] = [Fake()]
        try: times = lesson.word_times(clip, 24000, "A 35-year-old man's ECG")
        finally: lesson._ASR[:] = []
        self.assertEqual(times[0], [100, 250]); self.assertEqual(times[2], [1450, 1800]); self.assertEqual(times[3], [1900, 2400])
        self.assertEqual(times[1], [250, 1450])                  # "35-year-old" was not heard as one word: it fills the gap
        lesson._ASR[:] = [None]                                  # a broken recogniser: words share the spoken span by length
        try: times = lesson.word_times(clip, 24000, "one two three")
        finally: lesson._ASR[:] = []
        self.assertEqual((times[0][0], times[-1][1]), (100, 2900))
        self.assertTrue(all(b[0] >= a[0] for a, b in zip(times, times[1:])))


if __name__ == "__main__":
    unittest.main()
