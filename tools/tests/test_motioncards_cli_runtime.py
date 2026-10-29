import json,os,socket,subprocess,sys,tempfile,time,unittest,urllib.request,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def run_clean(args,cwd,timeout=30):
    env=os.environ.copy();env.pop("PYTHONPATH",None)
    return subprocess.run([sys.executable,*args],cwd=cwd,env=env,text=True,capture_output=True,timeout=timeout)

def free_port():
    s=socket.socket();s.bind(("127.0.0.1",0));port=s.getsockname()[1];s.close();return port

class MotionCardsCliRuntimeTests(unittest.TestCase):
    def test_fresh_authoring_kit_scaffold_preview_package_validate(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);source=root/"source";kit_zip=root/"kit.zip";kit=root/"kit"
            p=run_clean(["tools/motioncards_example.py","--out",str(source)],ROOT)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            p=run_clean(["tools/motioncards_bundle.py","--out",str(kit_zip)],ROOT)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            with zipfile.ZipFile(kit_zip) as z:z.extractall(kit)
            (kit/"exported.json").write_bytes((source/"synthetic-export.json").read_bytes())
            cmd=["tools/motioncards.py","scaffold","exported.json","--out","work/batch","--package-id","FRESH","--revision","1","--qids","Q000000001","--duration-ms","4000"]
            p=run_clean(cmd,kit);self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            scene=kit/"work/batch/scenes/Q000000001.scene.json";data=json.loads(scene.read_text());data["takeaway"]="Pressure moves from higher toward lower pressure.";scene.write_text(json.dumps(data))
            # The unpacked kit alone must run the art library, style kit and recipes (no repo checkout).
            for cmd in (["tools/motioncards.py","library"],["tools/motioncards.py","style-kit",str(scene)],["tools/motioncards.py","recipes",str(scene)],
                        ["tools/motioncards.py","import-svg","lib:heart","--scene",str(scene),"--id","heart","--box","40,110,300,320"],
                        ["tools/motioncards.py","lint","--workspace","work/batch"]):
                p=run_clean(cmd,kit);self.assertEqual(p.returncode,0,cmd[1]+": "+p.stdout+p.stderr)
            data=json.loads(scene.read_text())
            self.assertIn('id="kit"',data["svg"]);self.assertIn('id="heart"',data["svg"]);self.assertIn("// @recipes v1 begin",data["script"])
            self.assertIn("Servier Medical Art",data["credits"][0])
            port=free_port();env=os.environ.copy();env.pop("PYTHONPATH",None)
            proc=subprocess.Popen([sys.executable,"tools/motioncards.py","preview","--workspace","work/batch","--port",str(port)],cwd=kit,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            try:
                deadline=time.time()+10;body=None
                while time.time()<deadline:
                    try:
                        body=urllib.request.urlopen(f"http://127.0.0.1:{port}/",timeout=1).read().decode();break
                    except Exception:time.sleep(.1)
                self.assertIsNotNone(body)
                self.assertIn("Q000000001-preview.html",body)
                self.assertNotIn('href="/Q000000001.html"',body)
                host=urllib.request.urlopen(f"http://127.0.0.1:{port}/Q000000001-preview.html",timeout=2).read().decode()
                self.assertIn("MessageChannel",host);self.assertIn('id="play"',host);self.assertIn("Correct answer",host)
                child=urllib.request.urlopen(f"http://127.0.0.1:{port}/Q000000001.html",timeout=2).read().decode()
                self.assertIn("http://127.0.0.1:"+str(port),child)
            finally:
                proc.terminate()
                try:proc.wait(timeout=3)
                except subprocess.TimeoutExpired:proc.kill()
            # New cards carry voice by default (voiceover/): packaging a silent card must be refused with a clear fix.
            p=run_clean(["tools/motioncards.py","package","exported.json","--workspace","work/batch","--out","MCARDS_FRESH_r1.zip"],kit)
            self.assertNotEqual(p.returncode,0);self.assertIn("voice_missing:Q",p.stdout+p.stderr);self.assertIn("voiceover.py make",p.stdout+p.stderr)
            # The offline kit has no voice model, so it packages explicitly silent.
            p=run_clean(["tools/motioncards.py","package","exported.json","--workspace","work/batch","--out","MCARDS_FRESH_r1.zip","--no-voice"],kit)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            p=run_clean(["tools/motioncards.py","validate","MCARDS_FRESH_r1.zip"],kit)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertIn('"status": "PASS"',p.stdout)

    def test_smoke_module_entrypoint_has_no_accidental_pythonpath_dependency(self):
        p=run_clean(["-m","tools.motioncards.smoke","--help"],ROOT)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        direct=run_clean(["tools/motioncards/smoke.py","--help"],ROOT)
        self.assertEqual(direct.returncode,0,direct.stdout+direct.stderr)

if __name__=="__main__":unittest.main()
