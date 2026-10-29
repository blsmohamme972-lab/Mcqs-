"""Real-browser test of app/modules/motioncards-voice.js with a real Opus track.

Drives the controller the way motioncards-player.js would (anchor clock + requestAnimationFrame)
and checks Golden rule 7: picture time and voice time stay within 60 ms through play, seek and pause,
and picture and voice stop together when something outside the app pauses the voice.
Needs playwright + Chromium (run voiceover/bootstrap.sh, or set MOTIONCARDS_CHROMIUM) and a sample track (voiceover/samples/*.opus).
"""
import base64, importlib.util, json, os, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
SAMPLE = next(iter(sorted((HERE / "samples").rglob("*.opus"))), None)

PAGE = """<!doctype html><meta charset=utf-8><body><script>%s</script><script>
const bytes=Uint8Array.from(atob('%s'),c=>c.charCodeAt(0)).buffer;
const V=KafuMotionCards.voice; let anchor=0, playing=false, t=0, interrupts=0;
const v=V.create(bytes,{onInterrupt:()=>{interrupts++; if(playing) api.pause();}});   // as motioncards-player.js wires it
function frame(now){ if(!playing) return; t=v.clock(now-anchor); anchor=now-t; requestAnimationFrame(frame); }
window.api={
  supported:()=>V.supported(),
  play:()=>{ v.play(t); playing=true; anchor=performance.now()-t; requestAnimationFrame(frame); },
  pause:()=>{ if(playing) t=performance.now()-anchor; playing=false; v.pause(t); },
  restart:()=>{ playing=false; t=0; v.pause(0); },
  seek:(ms)=>{ t=ms; anchor=performance.now()-t; v.seek(ms,playing); },
  state:()=>({t, a:window.__a.currentTime*1000, paused:window.__a.paused, playing, interrupts}),
};
</script>"""


@unittest.skipUnless(SAMPLE, "no sample track")
class VoiceSyncBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        js = (HERE.parent / "app" / "modules" / "motioncards-voice.js").read_text()
        # expose the audio element so the test can read its clock
        js = js.replace('const a=(opts.audio||(()=>root.document.createElement("audio")))();',
                        'const a=(opts.audio||(()=>root.document.createElement("audio")))();root.__a=a;')
        assert "root.__a=a;" in js, "the audio element line in motioncards-voice.js changed: update this test"
        cls.html = PAGE % (js, base64.b64encode(SAMPLE.read_bytes()).decode())
        spec = importlib.util.spec_from_file_location("voiceover_tool", HERE / "voiceover.py")
        V = importlib.util.module_from_spec(spec); spec.loader.exec_module(V)
        exe = V.chromium()   # MOTIONCARDS_CHROMIUM, else the Chromium `voiceover.py setup` found
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"], **({"executable_path": exe} if exe else {}))

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.pw.stop()

    def page(self):
        pg = self.browser.new_page(); pg.set_content(self.html)
        self.assertTrue(pg.evaluate("api.supported()"), "Chromium must report Ogg Opus support")
        return pg

    def test_sync_through_play_seek_pause(self):
        pg = self.page()
        pg.evaluate("api.play()"); pg.wait_for_timeout(1500)
        s = pg.evaluate("api.state()")
        self.assertGreater(s["a"], 1000, f"audio did not advance: {s}")
        self.assertLess(abs(s["t"] - s["a"]), 60, f"picture/voice drift while playing: {s}")
        pg.evaluate("api.seek(5000)"); pg.wait_for_timeout(600)
        s = pg.evaluate("api.state()")
        self.assertTrue(5000 <= s["a"] <= 6000, f"seek did not move the voice: {s}")
        self.assertLess(abs(s["t"] - s["a"]), 60, f"drift after seek: {s}")
        pg.evaluate("api.pause()"); a1 = pg.evaluate("window.__a.currentTime"); pg.wait_for_timeout(400)
        self.assertEqual(a1, pg.evaluate("window.__a.currentTime"), "voice kept playing after pause")
        pg.evaluate("api.seek(2000)"); pg.wait_for_timeout(400)
        s = pg.evaluate("api.state()")
        self.assertTrue(s["paused"] and abs(s["a"] - 2000) < 1, f"seek while paused must move the voice and keep it paused: {s}")
        pg.evaluate("api.play()"); pg.wait_for_timeout(600)
        s = pg.evaluate("api.state()")
        self.assertLess(abs(s["t"] - s["a"]), 60, f"drift after resume: {s}")
        pg.evaluate("api.restart()"); pg.wait_for_timeout(500)
        s = pg.evaluate("api.state()")
        self.assertTrue(s["paused"] and s["a"] == 0 and s["t"] == 0, f"restart must stop the voice at 0: {s}")
        pg.close()

    def test_outside_pause_stops_the_picture_and_outside_play_is_refused(self):
        pg = self.page()
        pg.evaluate("api.play()"); pg.wait_for_timeout(800)
        pg.evaluate("window.__a.pause()"); pg.wait_for_timeout(300)        # a call, an unplugged headset, the lock screen
        s = pg.evaluate("api.state()")
        self.assertEqual(s["interrupts"], 1, f"outside pause must be reported: {s}")
        self.assertFalse(s["playing"], f"the picture must pause with the voice: {s}")
        self.assertLess(abs(s["t"] - s["a"]), 60, f"picture and voice must stop together: {s}")
        pg.evaluate("window.__a.play()"); pg.wait_for_timeout(400)          # lock-screen play without the app's Play
        s = pg.evaluate("api.state()")
        self.assertTrue(s["paused"], f"only the app's Play may start the voice: {s}")
        pg.evaluate("api.play()"); pg.wait_for_timeout(600)
        s = pg.evaluate("api.state()")
        self.assertTrue(s["playing"] and not s["paused"], f"Play must resume after an interruption: {s}")
        self.assertLess(abs(s["t"] - s["a"]), 60, f"drift after resuming: {s}")
        pg.close()

    def test_fast_play_pause_play_keeps_the_voice_as_the_clock(self):
        pg = self.page()
        pg.evaluate("api.play(); api.pause(); api.play();")                # one task: the first play() is rejected late
        pg.wait_for_timeout(800)
        s = pg.evaluate("api.state()")
        self.assertTrue(s["playing"] and not s["paused"], f"voice must keep playing: {s}")
        self.assertLess(abs(s["t"] - s["a"]), 60, f"picture must follow the voice: {s}")
        pg.close()


if __name__ == "__main__":
    unittest.main()
