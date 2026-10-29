"""Unit tests for voiceover.py without the voice model (numpy for the signal tests, ffmpeg for the synth tests)."""
import importlib.util, json, os, shutil, tempfile, types, unittest
from pathlib import Path
_spec = importlib.util.spec_from_file_location("voiceover_tool", Path(__file__).resolve().parents[1] / "voiceover.py")
V = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(V)

SCENE = {"qid": "Q000000001", "duration_ms": 8000, "layers": [
    {"type": "text", "text": "Title", "fixed": True},
    {"type": "text", "text": "2 · Second beat", "show": [2700, 5000]},
    {"type": "text", "text": "1 · First beat", "show": [0, 2700]},
    {"type": "text", "text": "3 · Third beat", "show": [5000, 8000]}]}


class Beats(unittest.TestCase):
    def test_beats_come_from_numbered_captions_in_time_order(self):
        b = V.beats_from_scene(SCENE)
        self.assertEqual([x["caption"] for x in b], ["First beat", "Second beat", "Third beat"])
        self.assertEqual([(x["start_ms"], x["end_ms"]) for x in b], [(0, 2700), (2700, 5000), (5000, 8000)])

    def test_script_drawn_card_declares_its_captions_with_caps(self):
        script = 'function caps(api, P, list) { return 0; }\n caps(api, P0, [[300, 3700, "Severe cold: core defended", "#1e6fb8"],\n' \
                 '  [4000, 7300, "Vasoconstriction cuts flow to the legs", "#c62828"],\n  [7600, 0, "Core stays warm — legs freeze"]]);'
        d = V.draft_doc({"qid": "Q000009371", "duration_ms": 12000, "layers": [{"type": "text", "text": "Title", "fixed": True}], "script": script})
        self.assertEqual([(b["start_ms"], b["end_ms"], b["say"]) for b in d["beats"]],
                         [(300, 3700, "Severe cold: core defended"), (4000, 7300, "Vasoconstriction cuts flow to the legs"),
                          (7600, 12000, "Core stays warm — legs freeze")])
        self.assertEqual(V.script_problems(d), [])

    def test_scene_without_captions_gets_guessed_beats_that_synth_refuses(self):
        d = V.draft_doc({"qid": "Q000000002", "duration_ms": 12000, "layers": [{"type": "text", "text": "Title", "fixed": True}]})
        self.assertEqual([(b["start_ms"], b["end_ms"]) for b in d["beats"]], [(0, 3000), (3000, 6000), (6000, 9000), (9000, 12000)])
        self.assertTrue(all(b["timing"] == V.GUESS for b in d["beats"]))
        found = V.script_problems(d)
        self.assertEqual(len(found), 1); self.assertIsNone(found[0][0]); self.assertIn("no numbered captions", found[0][1])

    def test_windows_leave_lead_tail_and_end_hold(self):
        d = V.draft_doc(SCENE)
        self.assertEqual(V.window_ms(d, 0), 2700 - V.TAIL_MS - V.FIRST_LEAD_MS)
        self.assertEqual(V.window_ms(d, 1), 5000 - V.TAIL_MS - 2700 - V.LEAD_MS)
        self.assertEqual(V.window_ms(d, 2), 8000 - V.END_HOLD_MS - 5000 - V.LEAD_MS)
        self.assertTrue(all(V.max_words(d, i) >= 4 for i in range(3)))
        self.assertEqual(V.script_problems(d), [])

    def test_script_problems_name_each_beat_and_its_fix(self):
        d = V.draft_doc(SCENE)
        d["beats"][1]["start_ms"] = 2000                      # overlaps beat 1
        d["beats"][2]["say"], d["beats"][2]["end_ms"] = "EDIT: something", 7600
        d["beats"].append({"start_ms": 7600, "end_ms": 8000, "say": "Late."})   # too short to speak in
        got = V.script_problems(d)
        self.assertEqual([i for i, _ in got], [1, 2, 3])
        self.assertIn("overlap", got[0][1]); self.assertIn("write the spoken line", got[1][1]); self.assertIn("ms to speak in", got[2][1])

    def test_retime_follows_moved_captions_and_keeps_lines(self):
        d = V.draft_doc(SCENE); d["beats"][0]["say"] = "Kept line."
        moved = json.loads(json.dumps(SCENE)); moved["duration_ms"] = 9000; moved["layers"][1]["show"] = [3000, 5500]
        moved["layers"][2]["show"] = [0, 3000]; moved["layers"][3]["show"] = [5500, 9000]
        self.assertEqual(V.retime(d, moved), (True, None))
        self.assertEqual([(b["start_ms"], b["end_ms"]) for b in d["beats"]], [(0, 3000), (3000, 5500), (5500, 9000)])
        self.assertEqual((d["duration_ms"], d["beats"][0]["say"]), (9000, "Kept line."))
        self.assertEqual(V.retime(d, moved), (False, None))
        fewer = json.loads(json.dumps(moved)); fewer["layers"].pop()
        changed, problem = V.retime(d, fewer)
        self.assertFalse(changed); self.assertIn("draft --force", problem)


class Text(unittest.TestCase):
    LEX = {"say": {"INR": "I N R", "NH₃": "ammonia"}, "ipa": {"en-us": {"ketoacidosis": "kˌiːtoʊˌæsɪdˈoʊsɪs"}}}

    def test_say_rewrites_whole_tokens_only(self):
        self.assertEqual(V.spoken_text("The INR rises; NH₃ builds; WINRAR", self.LEX), "The I N R rises; ammonia builds; WINRAR")

    def test_ipa_split_marks_dictionary_words(self):
        parts = V.ipa_split("Diabetic Ketoacidosis, again.", self.LEX["ipa"]["en-us"])
        self.assertEqual(parts, [("Diabetic ", False), ("kˌiːtoʊˌæsɪdˈoʊsɪs", True), (", again.", False)])

    def test_word_score_ignores_asr_spacing_and_repeats(self):
        self.assertEqual(V.word_score("Too little prothrombin.", "too little pro thrombin"), 1.0)
        self.assertEqual(V.word_score("The INR rises.", "The INR rises. The INR rises."), 1.0)
        self.assertLess(V.word_score("Ketoacidosis", "ketosidosis"), 0.95)

    def test_symbols_next_to_words_are_spoken(self):
        lex = {"say": {"INR": "I N R", "↑": "rises", "→": ",", "°C": "degrees", "%": "percent"}}
        self.assertEqual(V.spoken_text("INR↑ to 2", lex), "I N R rises to 2")
        self.assertEqual(V.spoken_text("glucose→fat", lex), "glucose, fat")
        self.assertEqual(V.spoken_text("core 37°C, 50% lost", lex), "core 37 degrees, 50 percent lost")

    def test_one_misheard_long_word_fails_even_when_the_line_scores_high(self):
        for said, heard in [("Ketoacidosis", "ketosidosis"), ("No insulin: ketoacidosis.", "No insulin, ketosidosis."),
                            ("The liver makes clotting factors.", "The liver makes clothing factors."),
                            ("Hypokalaemia: give potassium.", "Hyperkalaemia, give potassium.")]:
            self.assertGreaterEqual(V.word_score(said, heard), 0.85, "the whole-line score alone would pass it")
            self.assertTrue(V.word_errors(said, heard), f"{said!r} -> {heard!r} must fail")
        for said, heard in [("Too little prothrombin.", "too little pro thrombin"), ("Water floods brain cells.", "Waterflood's brain cells."),
                            ("Anaemia and haemorrhage.", "Anemia and hemorrhage."), ("Ten millimoles per litre.", "10 millimoles per liter."),
                            ("A large tumour.", "A large tumor."), ("Tissues turn anaerobic.", "Tissue's turn anaerobic."),
                            ("Bilirubin rises.", "Billy Rubin rises."), ("Clotting slows.", "Cloting slows.")]:
            self.assertEqual(V.word_errors(said, heard), [], f"{said!r} -> {heard!r} must pass")

    def test_extra_speech_is_caught_but_spelt_letters_are_not(self):
        said = "Clotting slows, the INR rises."
        self.assertTrue(V.too_much_heard(said, "Clotting slows, the INR rises. So, that's what this is. We do have a great story."))
        self.assertFalse(V.too_much_heard(said, "Clotting slows, the I N R rises."))
        self.assertFalse(V.too_much_heard(said, "Clotting slows, the INR rises. is."))


class Signal(unittest.TestCase):
    def test_onsets_and_trim(self):
        import numpy as np
        sr = 16000; x = np.zeros(sr * 3, np.float32)
        x[int(0.5 * sr):int(0.9 * sr)] = 0.3; x[int(1.7 * sr):int(2.2 * sr)] = 0.3
        on = V.speech_onsets(x, [{"t_ms": 500, "end_ms": 900}, {"t_ms": 1650, "end_ms": 2200}], sr=sr)
        self.assertEqual(on[0], 0); self.assertEqual(on[1], 50)
        y = np.concatenate([np.zeros(V.SR // 5, np.float32), np.full(V.SR // 2, 0.2, np.float32)])
        self.assertLess(abs(len(V.trim_lead(y)) - (V.SR // 2 + V.SR * 8 // 1000)), V.SR // 200 + 1)

    def test_onset_ignores_the_previous_lines_tail(self):
        import numpy as np
        sr = 16000; x = np.zeros(sr * 3, np.float32)
        x[int(0.2 * sr):int(1.45 * sr)] = 0.3          # line 1 runs until 240 ms before line 2's cue
        x[int(1.69 * sr):int(2.5 * sr)] = 0.3          # line 2 starts on time (cue at 1690 ms)
        on = V.speech_onsets(x, [{"t_ms": 200, "end_ms": 1450}, {"t_ms": 1690, "end_ms": 2500}], sr=sr)
        self.assertEqual(on, [0, 0])

    def test_onset_ignores_the_previous_beats_tail(self):
        import numpy as np
        sr = 16000; x = np.zeros(sr * 3, np.float32)
        x[int(0.5 * sr):int(1.38 * sr)] = 0.3; x[int(1.5 * sr):int(2.0 * sr)] = 0.3   # line 1 ends 120 ms before line 2
        on = V.speech_onsets(x, [{"t_ms": 500, "end_ms": 1380}, {"t_ms": 1500, "end_ms": 2000}], sr=sr)
        self.assertEqual(on, [0, 0])

    def test_stray_sound_outside_the_lines(self):
        import numpy as np
        sr = 16000; x = np.zeros(sr * 4, np.float32)
        x[int(0.5 * sr):int(1.0 * sr)] = 0.3
        cues = [{"t_ms": 500, "end_ms": 1000}]
        self.assertEqual(V.stray_sound(x, cues, sr=sr), [])
        x[int(2.5 * sr):int(2.6 * sr)] = 0.05          # a click 1.5 s after the line, -16 dB under its peak
        self.assertEqual(V.stray_sound(x, cues, sr=sr), [2500])

    def test_each_line_is_heard_on_its_own(self):
        cues = [{"t_ms": 250, "end_ms": 1918}, {"t_ms": 2820, "end_ms": 4330}, {"t_ms": 5120, "end_ms": 6934}]
        self.assertEqual([V.cue_span(cues, k, 7034) for k in range(3)], [(100, 2068), (2670, 4480), (4970, 7034)])


class Browser(unittest.TestCase):
    def test_explicit_chromium_wins(self):
        old = os.environ.get("MOTIONCARDS_CHROMIUM")
        try:
            os.environ["MOTIONCARDS_CHROMIUM"] = "/x/chrome"; self.assertEqual(V.chromium(), "/x/chrome")
        finally:
            if old is None: os.environ.pop("MOTIONCARDS_CHROMIUM", None)
            else: os.environ["MOTIONCARDS_CHROMIUM"] = old


@unittest.skipUnless(shutil.which("ffmpeg"), "needs ffmpeg")
class Synth(unittest.TestCase):
    """synth with a stand-in voice: tone bursts as long as the text needs at 2.6 words per second."""
    def setUp(self):
        import numpy as np
        self.tmp = Path(tempfile.mkdtemp()); self.d = self.tmp / "voice"; self.d.mkdir()
        def speak(text, voice, lang, speed, lex, engine="kokoro"):
            n = int(V.SR * len(text.split()) / 2.6 / speed); t = np.arange(n) / V.SR
            return (0.3 * np.sin(2 * np.pi * 220 * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 3 * t))).astype(np.float32)
        self._speak, V.speak = V.speak, speak

    def tearDown(self):
        V.speak = self._speak; shutil.rmtree(self.tmp)

    def write(self, doc):
        (self.d / f"{doc['qid']}.voice.json").write_text(json.dumps(doc), encoding="utf-8")

    def test_a_line_that_fits_only_at_the_speed_cap_is_kept(self):
        import numpy as np
        V.speak = lambda text, voice, lang, speed, lex, engine="kokoro": np.full(int(V.SR * (2.6 if speed < 1.2 else 1.9)), 0.2, np.float32)  # not 1/speed
        doc = V.draft_doc(SCENE); doc["beats"][1]["say"] = "Liver disease means less prothrombin."
        for b in (0, 2): doc["beats"][b]["say"] = "Short."
        info = V.synth_one(doc, self.d, {})
        self.assertEqual(info["cues"][1]["speed"], V.MAX_SPEED)
        V.speak = lambda text, voice, lang, speed, lex, engine="kokoro": np.full(int(V.SR * 2.6), 0.2, np.float32)
        with self.assertRaises(ValueError) as e: V.synth_one(doc, self.d, {})
        self.assertIn("(5 words) needs 2600 ms even at 1.2x, the beat allows 2060 ms: cut it to about 3 words", str(e.exception))

    def test_check_flags_missing_orphan_and_empty(self):
        ws = self.tmp; (ws / "scenes").mkdir()
        (ws / "scenes" / "Q000000001.scene.json").write_text(json.dumps(SCENE), encoding="utf-8")
        (self.d / "Q000000009.track.json").write_text("{}", encoding="utf-8")
        a = types.SimpleNamespace(workspace=str(ws), qids=None)
        got = V.run_check(a)
        self.assertTrue(any(m.startswith("Q000000009: voice for a card that is not in scenes/") for m in got), got)
        self.assertTrue(any(m.startswith("Q000000001: no voice track") for m in got), got)
        empty = Path(tempfile.mkdtemp())
        try: self.assertTrue(V.run_check(types.SimpleNamespace(workspace=str(empty), qids=None))[0].startswith("nothing to check"))
        finally: shutil.rmtree(empty)

    def test_one_pass_lists_every_problem_and_writes_only_good_cards(self):
        good = V.draft_doc(SCENE)
        good["beats"][0]["say"], good["beats"][1]["say"], good["beats"][2]["say"] = "Plasma osmolality falls.", "Water floods brain cells.", "Brain cells swell: confusion."
        long = json.loads(json.dumps(good)); long["qid"] = "Q000000002"
        long["beats"][1]["say"] = "Water moves by osmosis into the brain cells, which then swell up badly"
        long["beats"][2]["say"] = "EDIT: later"
        guessed = V.draft_doc({"qid": "Q000000003", "duration_ms": 8000, "layers": []})
        for doc in (good, long, guessed): self.write(doc)
        (self.d / "Q000000002.opus").write_bytes(b"stale")                  # from an earlier run: must not survive a failed synth
        a = types.SimpleNamespace(workspace=str(self.tmp), qids=None)
        bad, failed = V.run_synth(a)
        self.assertEqual(failed, {"Q000000002", "Q000000003"})
        text = "\n".join(bad)
        self.assertIn("Q000000002 beat 2", text); self.assertIn("cut it to about", text)
        self.assertIn("Q000000002 beat 3: write the spoken line", text); self.assertIn("Q000000003: the scene has no numbered captions", text)
        self.assertFalse((self.d / "Q000000002.opus").exists())
        info = json.loads((self.d / "Q000000001.track.json").read_text())
        self.assertEqual((info["bitrate"], info["script_sha256"]), ("16k", V.script_sha(good)))
        self.assertLessEqual(info["bytes"], V.MAX_VOICE_BYTES)
        self.assertEqual([c["t_ms"] for c in info["cues"]], [250, 2820, 5120])
        first = info["sha256"]; V.run_synth(types.SimpleNamespace(workspace=str(self.tmp), qids=["Q000000001"]))
        self.assertEqual(json.loads((self.d / "Q000000001.track.json").read_text())["sha256"], first, "encoding must be bit-exact")


class Engines(unittest.TestCase):
    """The owner chooses the voice engine; the agent must ask, and the choice is kept in each script."""
    def setUp(self): self.tmp = Path(tempfile.mkdtemp())
    def tearDown(self): shutil.rmtree(self.tmp)

    def test_make_refuses_to_guess_the_engine(self):
        with self.assertRaises(SystemExit) as e: V.need_engine(types.SimpleNamespace(engine=None))
        self.assertIn("ASK THE OWNER", str(e.exception))
        V.need_engine(types.SimpleNamespace(engine="elevenlabs"))

    def test_draft_records_and_switches_the_engine_keeping_lines(self):
        ws = self.tmp; (ws / "scenes").mkdir()
        (ws / "scenes" / "Q000000001.scene.json").write_text(json.dumps(SCENE), encoding="utf-8")
        a = types.SimpleNamespace(workspace=str(ws), qids=None, force=False, engine="kokoro", voice=None, lang="en-us")
        V.run_draft(a); p = ws / "voice" / "Q000000001.voice.json"; doc = json.loads(p.read_text())
        self.assertEqual((doc["engine"], doc["voice"]), ("kokoro", "af_heart"))
        doc["beats"][0]["say"] = "Kept line."; p.write_text(json.dumps(doc), encoding="utf-8")
        a.engine = "elevenlabs"; V.run_draft(a); doc = json.loads(p.read_text())
        self.assertEqual((doc["engine"], doc["voice"], doc["beats"][0]["say"]), ("elevenlabs", V.engine_voice("elevenlabs", doc["qid"]), "Kept line."))
        a.engine = None; V.run_draft(a); self.assertEqual(json.loads(p.read_text())["engine"], "elevenlabs")

    def test_elevenlabs_rotates_women_and_men_and_is_high_quality(self):
        ids = [V.engine_voice("elevenlabs", f"Q{n:09d}") for n in range(79, 85)]
        self.assertEqual(len(set(ids)), 6)
        sexes = [next(g for _, v, g in V.ELEVEN_VOICES if v == i) for i in ids]
        self.assertTrue(all(a != b for a, b in zip(sexes, sexes[1:])))
        self.assertEqual(V.engine_voice("elevenlabs", "Q000000079"), V.engine_voice("elevenlabs", "Q000000079"))
        self.assertEqual(V.engine_voice("kokoro", "Q000000079"), "af_heart")
        self.assertEqual(V.doc_quality({"engine": "elevenlabs"}), "high")
        self.assertEqual(V.doc_quality({"engine": "kokoro"}), "standard")
        self.assertEqual(V.doc_quality({}), "standard")
        doc = {"qid": "Q000000080", "engine": "kokoro", "voice": "af_heart"}
        self.assertTrue(V.set_engine(doc, "elevenlabs", None))
        self.assertEqual((doc["voice"], doc["quality"]), (V.engine_voice("elevenlabs", "Q000000080"), "high"))

    def test_breeze_designs_once_then_clones_and_directs(self):
        self.assertEqual(V.breeze_args("Hi.", None, design="A calm voice."), ["--text", "Hi.", "--instruction", "A calm voice.", "--cfg-scale", "4"])
        self.assertEqual(V.breeze_args("Hi.", Path("r.wav")), ["--text", "Hi.", "--ref-audio", "r.wav", "--ref-text", V.BREEZE_REF_TEXT])
        self.assertEqual(V.breeze_args("Hi.", Path("r.wav"), "worried")[-4:], ["--instruction", "worried", "--cfg-scale", "4"])
        self.assertEqual(V.breeze_text("(sigh) Primary sclerosing cholangitis.", {"say_breeze": {"sclerosing": "skler-OH-sing"}}),
                         "(sigh) Primary skler-OH-sing cholangitis.")
        self.assertEqual(V.doc_quality({"engine": "breeze"}), "medium")
        # a different Breeze voice per question, women and men taking turns; a question keeps its voice
        self.assertEqual(V.engine_voice("breeze", "Q000000079"), "doctor-man")
        self.assertEqual(V.engine_voice("breeze", "Q000000080"), "student-woman")
        self.assertEqual(V.engine_voice("breeze", ""), "lecturer-woman")
        self.assertTrue(set(V.BREEZE_ROTATION) <= set(V.BREEZE_VOICES))

    def test_breeze_is_cached_and_needs_setup(self):
        old = V.CACHE; V.CACHE = self.tmp
        try:
            with self.assertRaises(ValueError) as e: V.breeze_wav("Hello.", "lecturer-woman")
            self.assertIn("setup --engine breeze", str(e.exception))
            runs = []
            real = V._breeze_run
            V._breeze_run = lambda args, out: runs.append(args) or (out.parent.mkdir(parents=True, exist_ok=True), out.write_bytes(b"x"))
            try:
                a = V.breeze_wav("Hello.", "lecturer-woman"); b = V.breeze_wav("Hello.", "lecturer-woman")
                c = V.breeze_wav("Hello.", "lecturer-woman", "excited")
            finally: V._breeze_run = real
            self.assertEqual(a, b); self.assertNotEqual(a, c)
            self.assertEqual(len(runs), 3, "one design run, then one run per new line; the repeat comes from the cache")
            self.assertIn("--instruction", runs[0]); self.assertIn("--ref-audio", runs[1])
        finally: V.CACHE = old

    def test_old_scripts_without_an_engine_are_kokoro(self):
        doc = {"voice": "af_heart"}
        self.assertFalse(V.set_engine(doc, None, None)); self.assertEqual(doc["engine"], "kokoro")

    def test_elevenlabs_is_cached_and_needs_a_key(self):
        import numpy as np
        old_cache, old_key = V.CACHE, os.environ.pop("ELEVENLABS_API_KEY", None); V.CACHE = self.tmp
        try:
            with self.assertRaises(ValueError) as e: V.eleven_pcm("Hello.", "v", 1.0)
            self.assertIn("ELEVENLABS_API_KEY", str(e.exception))
            calls = []
            class R:
                def __enter__(s): return s
                def __exit__(s, *x): pass
                def read(s): return (np.ones(2400, "<i2") * 1000).tobytes()
            real, V.urllib.request.urlopen = V.urllib.request.urlopen, lambda req, timeout: calls.append(req) or R()
            os.environ["ELEVENLABS_API_KEY"] = "test"
            try:
                a = V.speak("INR rises.", "v", "en-us", 1.0, {"say": {"INR": "I N R"}}, "elevenlabs")
                b = V.speak("INR rises.", "v", "en-us", 1.0, {"say": {"INR": "I N R"}}, "elevenlabs")
            finally: V.urllib.request.urlopen = real
            self.assertEqual(len(calls), 1, "the second call must come from the cache")
            self.assertIn("pcm_24000", calls[0].full_url); self.assertIn(b'"I N R rises."', calls[0].data)
            self.assertTrue(np.array_equal(a, b)); self.assertEqual(a.dtype, np.float32)
            with self.assertRaises(ValueError): V.speak("x", "v", "en-us", 1.0, {}, "nope")
        finally:
            V.CACHE = old_cache; os.environ.pop("ELEVENLABS_API_KEY", None)
            if old_key is not None: os.environ["ELEVENLABS_API_KEY"] = old_key


if __name__ == "__main__":
    unittest.main()
