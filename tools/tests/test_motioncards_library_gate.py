import json,os,shutil,subprocess,tempfile,unittest
from pathlib import Path
from motioncards.lib.library_gate import check

ROOT=Path(__file__).resolve().parents[2]
BROWSER=bool(shutil.which("chromium") or os.environ.get("MOTIONCARDS_CHROMIUM") or os.environ.get("MOTIONCARDS_BROWSER_TESTS")=="1")
NEW_ART='''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect x="5" y="5" width="90" height="90" rx="20" fill="#2a7f62"/>
<path d="M20 70L50 20L80 70Z" fill="#f3c74b" stroke="#7a5a00" stroke-width="3"/><circle cx="50" cy="55" r="9" fill="#fff"/></svg>'''
ENTRY={"file":"art/test-shape.svg","view":"test shape for the gate","use":"gate tests","license":"CC0","source":"https://example.org/test-shape.svg",
       "reason":"Adds a drawing no existing entry covers, used to prove the gate.","used_in":["Q000009349"],"credit":"Test shape: Example, CC0","style":"other"}

class LibraryGateTests(unittest.TestCase):
    def setUp(self):
        self.td=tempfile.mkdtemp();self.repo=Path(self.td)/"repo"
        subprocess.run(["git","clone","-q","--local",str(ROOT),str(self.repo)],check=True)
        self.base=subprocess.run(["git","rev-parse","HEAD"],cwd=self.repo,capture_output=True,text=True,check=True).stdout.strip()
        self.lib=self.repo/"motioncards/library"
    def tearDown(self):shutil.rmtree(self.td,ignore_errors=True)
    def idx(self):return json.loads((self.lib/"library.json").read_text(encoding="utf-8"))
    def save(self,d):(self.lib/"library.json").write_text(json.dumps(d,indent=2,ensure_ascii=False),encoding="utf-8")
    def add_art(self,entry=ENTRY,svg=NEW_ART,name="test-shape"):
        (self.lib/entry["file"]).write_text(svg,encoding="utf-8");d=self.idx();d["art"][name]=dict(entry);self.save(d)
    def run_gate(self,render=False):return check(self.base,render=render,root=self.repo)

    def test_documented_new_art_passes_static_checks(self):
        self.add_art();r=self.run_gate()
        self.assertTrue(r.passed,r.markdown())

    def test_missing_fields_or_unsafe_licence_fail(self):
        bad=dict(ENTRY);bad.pop("reason");bad["license"]="CC BY-NC 4.0";bad["credit"]="Shape: X, CC BY-NC 4.0"
        self.add_art(bad);r=self.run_gate()
        self.assertFalse(r.passed);txt=r.markdown()
        self.assertIn("missing reason",txt)
        bad=dict(ENTRY);bad["license"]="CC BY-NC 4.0";bad["credit"]="Shape: X, CC BY-NC 4.0";self.save(json.loads(json.dumps(self.idx()))|{})
        d=self.idx();d["art"]["test-shape"]=bad;self.save(d);r=self.run_gate()
        self.assertIn("not in",r.markdown());self.assertIn("NC",r.markdown())

    def test_changing_existing_entries_files_or_recipes_needs_a_human(self):
        d=self.idx();d["art"]["heart"]["view"]="edited";self.save(d)
        r=self.run_gate();self.assertFalse(r.passed);self.assertIn("existing entry 'heart'",r.markdown())
        subprocess.run(["git","checkout","--","."],cwd=self.repo,check=True)
        (self.repo/"tools/motioncards.py").write_text("# changed\n",encoding="utf-8");self.add_art()
        r=self.run_gate();self.assertFalse(r.passed);self.assertIn("outside the library",r.markdown())
        subprocess.run(["git","checkout","--","."],cwd=self.repo,check=True)
        rec=(self.lib/"recipes.js").read_text(encoding="utf-8").replace("period = o.period || 1300","period = o.period || 999")
        (self.lib/"recipes.js").write_text(rec,encoding="utf-8")
        r=self.run_gate();self.assertIn("existing recipe 'flow'",r.markdown())

    def test_new_recipe_requires_a_demo(self):
        rec=(self.lib/"recipes.js").read_text(encoding="utf-8")
        member='  wobble(api, el, t, amp) { api.set(el, {transform: `translate(${(amp * Math.sin(t / 200)).toFixed(2)} 0)`}); },\n'
        rec=rec.replace("  // Debug only:",member+"  // Debug only:",1);(self.lib/"recipes.js").write_text(rec,encoding="utf-8")
        r=self.run_gate();self.assertFalse(r.passed);self.assertIn("add motioncards/library/demos/wobble.js",r.markdown())
        (self.lib/"demos").mkdir(exist_ok=True)
        (self.lib/"demos/wobble.js").write_text("let c;function setup(api){c=api.el('circle',{cx:100,cy:100,r:30,fill:'url(#kit-tissue)'},api.svg);}\nfunction render(t,api){R.wobble(api,c,t,10);}\n",encoding="utf-8")
        r=self.run_gate();self.assertTrue(r.passed,r.markdown())

    @unittest.skipUnless(BROWSER,"needs Chromium (set MOTIONCARDS_CHROMIUM or MOTIONCARDS_BROWSER_TESTS=1)")
    def test_browser_checks_render_and_reject_duplicates(self):
        try:import playwright  # noqa: F401
        except ImportError:self.skipTest("playwright not installed")
        self.add_art();r=self.run_gate(render=True);self.assertTrue(r.passed,r.markdown())
        subprocess.run(["git","checkout","--","."],cwd=self.repo,check=True);(self.lib/"art/test-shape.svg").unlink()
        dup=dict(ENTRY,file="art/heart-copy.svg");self.add_art(dup,svg=(self.lib/"art/heart.svg").read_text(encoding="utf-8"),name="heart-copy")
        r=self.run_gate(render=True);self.assertFalse(r.passed);self.assertIn("near-duplicate of existing 'heart'",r.markdown())
        (self.lib/"demos").mkdir(exist_ok=True)
        rec=(self.lib/"recipes.js").read_text(encoding="utf-8").replace("  // Debug only:",'  wobble(api, el, t, amp) { api.set(el, {transform: `translate(${(amp * Math.sin(t / 200)).toFixed(2)} 0)`}); },\n  // Debug only:',1)
        (self.lib/"recipes.js").write_text(rec,encoding="utf-8")
        subprocess.run(["git","checkout","--","motioncards/library/library.json"],cwd=self.repo,check=True);(self.lib/"art/heart-copy.svg").unlink()
        (self.lib/"demos/wobble.js").write_text("let c;function setup(api){c=api.el('circle',{cx:100,cy:100,r:30,fill:'url(#kit-tissue)'},api.svg);}\nfunction render(t,api){R.wobble(api,c,t,10);}\n",encoding="utf-8")
        r=self.run_gate(render=True);self.assertTrue(r.passed,r.markdown());self.assertIn("deterministic seeking",r.markdown())

if __name__=="__main__":unittest.main()
