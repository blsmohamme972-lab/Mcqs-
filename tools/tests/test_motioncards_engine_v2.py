import base64,copy,hashlib,json,os,shutil,struct,tempfile,unittest,zipfile,zlib
from pathlib import Path
from motioncards.lib.compiler import compile_scene,validate_scene,preview_host_html
from motioncards.lib.engine_v2 import lint_scene_v2,SceneV2Error
from motioncards.lib.core import adapt_exports
from motioncards.lib.package import scaffold_workspace,validate_package
from motioncards.lib.multipart import build_package_set,validate_package_part
from motioncards.lib.spec import MAX_ENTRY_BYTES
from tools.tests.test_motioncards_authoring import question,envelope

ROOT=Path(__file__).resolve().parents[2]
EXAMPLES=ROOT/"motioncards/examples"

# sha256 of v1 compiler output recorded before engine v2 existed.  Already-built v1 ZIPs are
# re-compiled by the publisher and compared byte-for-byte, so these must never change.
V1_GOLDEN={
 "flow":"fedfa7949cba1f3adfaac8521f63da5eaf068d435862f208163fa0f6416741b7",
 "flow_preview":"0a3795759824a3395b55ad1078986df0fe020a79bd08dd8e784027d0e7a60ebf",
 "flow_host":"3561fd2cbafdff8c1cc4d6eb23acf44c428209f104fec6dc767deed89ee0ef81",
 "sequence":"e84adb9239a5d2d2cdfe1d2b6e4d57ef60684a974da0768af4c272a7bb2402bf",
 "sequence_preview":"8810ed15ca195049bd890f4b1aaa16ec4821c57bff3a697c0fad0f5baeb2bd2b",
 "sequence_host":"cdb97b5ed7d21ea7219412dc6d8a5fe32309338dc25785d06ca519c53551583d",
 "custom":"f016efdfd95932a9c275d3f41068aa37b0d8c29e5b15a5c04376ed10a458cbc3",
}

def sha(text):return hashlib.sha256(text.encode()).hexdigest()

def tiny_png():
    raw=b"\x00\xff\x00\x00\xff"
    def chunk(kind,data):return struct.pack(">I",len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data)&0xffffffff)
    return b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",1,1,8,2,0,0,0))+chunk(b"IDAT",zlib.compress(raw))+chunk(b"IEND",b"")

def kitchen_sink(qid="Q000000009",ms=8000):
    """Every v2 layer type, effect and animatable feature in one scene."""
    png="data:image/png;base64,"+base64.b64encode(tiny_png()).decode()
    return {"schema_version":2,"qid":qid,"duration_ms":ms,"takeaway":"Kitchen sink renders every feature.",
     "stage":{"width":640,"height":560,"background":"url:bg"},
     "palette":{"brand":"#3a0ca3"},
     "gradients":[{"id":"bg","kind":"radial","stops":[{"offset":0,"color":"#ffffff"},{"offset":1,"color":"@surface"}]},
                  {"id":"lin","angle":0,"stops":[{"offset":0,"color":"@artery"},{"offset":1,"color":"@vein","opacity":0.8}]}],
     "assets":{"dot":png},
     "camera":{"keys":[{"t":0,"x":320,"y":280,"zoom":1},{"t":4000,"x":340,"y":290,"zoom":1.3,"ease":"sine"},{"t":7000,"zoom":1}]},
     "layers":[
      {"type":"text","text":"Title that is long enough to wrap and shrink nicely","x":320,"y":50,"size":30,"max_width":400,"fit":True,"max_lines":2,"fixed":True,"weight":800},
      {"type":"label","text":"قلب","x":80,"y":120,"size":24,"halo":"#ffffff","font":"serif","enter":"type"},
      {"type":"rect","x":40,"y":150,"width":120,"height":80,"fill":"url:lin","shadow":True,"enter":"pop","keys":[{"t":1000,"width":120},{"t":3000,"width":180,"ease":"back_out"}]},
      {"type":"highlight","x":200,"y":150,"width":100,"height":80,"enter":"grow","exit":"shrink","show":[0,6000]},
      {"type":"focus","x":320,"y":150,"width":100,"height":80,"enter":"draw","exit":"fade","show":[500,7000]},
      {"type":"circle","cx":480,"cy":190,"r":40,"fill":"@brand","glow":"#ffd166","repeat":{"every_ms":1000,"times":4},"keys":[{"t":0,"scale":1},{"t":500,"scale":1.2,"ease":"sine"},{"t":1000,"scale":1}]},
      {"type":"ellipse","cx":580,"cy":190,"rx":40,"ry":25,"stroke":"@ink","stroke_width":3,"enter":"draw","keys":[{"t":2000,"fill":"#ffffff"},{"t":4000,"fill":"@good"}]},
      {"type":"line","x1":40,"y1":260,"x2":200,"y2":260,"dash":[8,6],"enter":"slide_left","keys":[{"t":1000,"x2":200},{"t":3000,"x2":260}]},
      {"type":"arrow","x1":240,"y1":300,"x2":420,"y2":300,"bend":-40,"head":"both","enter":"draw","keys":[{"t":2000,"bend":-40},{"t":4000,"bend":40}]},
      {"type":"path","d":"M 450 260 C 480 230 520 230 550 260","stroke":"@nerve","stroke_width":5,"enter":"slide_up","keys":[{"t":1000,"d":"M 450 260 C 480 230 520 230 550 260"},{"t":3000,"d":"M 450 270 C 480 300 520 300 550 270"}]},
      {"type":"polygon","points":[[60,340],[120,320],[150,380],[80,400]],"fill":"@mucosa","enter":"slide_right"},
      {"type":"polyline","points":[[180,400],[220,340],[260,390],[300,330]],"stroke":"@info","enter":"draw","exit":"slide_down","show":[0,7500]},
      {"type":"group","x":10,"y":0,"enter":"fade","keys":[{"t":0,"rotate":0},{"t":8000,"rotate":10}],"layers":[
        {"type":"circle","cx":380,"cy":380,"r":12,"fill":"@accent","along":{"d":"M 340 380 C 380 330 440 330 480 380","rotate":True},"keys":[{"t":0,"progress":0},{"t":6000,"progress":1}]},
        {"type":"rect","x":0,"y":0,"width":16,"height":10,"origin":[8,5],"fill":"@drug","along":{"d":"M 300 420 L 460 420"},"keys":[{"t":0,"progress":0},{"t":8000,"progress":1}]},
        {"type":"image","asset":"dot","x":500,"y":340,"width":60,"height":60,"fit":"cover"},
        {"type":"group","layers":[{"type":"text","text":"nested","x":560,"y":420,"size":16,"box":{"fill":"#ffffff","stroke":"@line"}}]}
      ]},
      {"type":"particles","d":"M 40 480 L 600 480","count":30,"r":6,"shape":"rbc","spread":30,"speed":120,"guide":{"stroke":"@line","stroke_width":20,"opacity":0.5},"keys":[{"t":2000,"speed":120},{"t":5000,"speed":-60}]},
      {"type":"particles","d":"M 40 530 L 600 530","count":12,"r":5,"shape":"ring","stroke":"@vein","phase":0.3,"seed":3,"fade_ends":False,"keys":[{"t":0,"stroke":"#3b6fb6"},{"t":6000,"stroke":"#d64545"}]},
      {"type":"spotlight","x":200,"y":120,"width":260,"height":140,"rx":20,"dim":0.4,"show":[5000,8000],"enter":"fade","keys":[{"t":5000,"x":200},{"t":7000,"x":260,"dim":0.5}]},
      {"type":"spotlight","cx":320,"cy":300,"r":80,"show":[6000,7000],"enter":"fade","exit":"fade","keys":[{"t":6000,"r":80},{"t":6900,"r":140}]}
     ],
     "custom_renderer":"function renderCustom(layer,t,h){h.el('circle',{cx:20+t/50,cy:20,r:6,fill:'@accent'});}"}

class EngineV2Tests(unittest.TestCase):
    def test_v1_compiler_output_is_byte_identical(self):
        for n in ["flow","sequence"]:
            s=json.loads((EXAMPLES/f"{n}.scene.json").read_text())
            self.assertEqual(sha(compile_scene(s)),V1_GOLDEN[n])
            self.assertEqual(sha(compile_scene(s,["http://127.0.0.1:8767"],preview=True)),V1_GOLDEN[n+"_preview"])
            self.assertEqual(sha(preview_host_html(s,["A"],8767)),V1_GOLDEN[n+"_host"])
        s=json.loads((EXAMPLES/"flow.scene.json").read_text());s["custom_renderer"]="function renderCustom(art,t,h){art.setAttribute('data-t',String(t));}"
        self.assertEqual(sha(compile_scene(s)),V1_GOLDEN["custom"])

    def test_gold_examples_and_kitchen_sink_validate_lint_clean_and_compile_deterministically(self):
        scenes=[json.loads(p.read_text()) for p in sorted(EXAMPLES.glob("v2-*.scene.json"))]+[kitchen_sink()]
        self.assertGreaterEqual(len(scenes),3)
        for s in scenes:
            validate_scene(s,s["qid"],s["duration_ms"])
            if s["qid"]!="Q000000009":self.assertEqual(lint_scene_v2(s),[],s["qid"])
            a=compile_scene(s);b=compile_scene(copy.deepcopy(s))
            self.assertEqual(a,b)
            self.assertLess(len(a.encode()),MAX_ENTRY_BYTES)
            self.assertIn('data-engine="2"',a)
            self.assertEqual(a.lower().count("<script"),3);self.assertEqual(a.lower().count("</script"),3)
            # The production entry must only trust the production host origin.
            self.assertIn('"allowed_host_origins":["https://kafu.blsmohamme97.workers.dev"]',a)

    def test_compiled_bytes_do_not_depend_on_crlf_in_custom_code(self):
        s=kitchen_sink();t=copy.deepcopy(s)
        t["custom_renderer"]=s["custom_renderer"].replace("{","{\r\n",1)
        s["custom_renderer"]=s["custom_renderer"].replace("{","{\n",1)
        self.assertEqual(compile_scene(s),compile_scene(t))

    def test_invalid_scenes_fail_with_precise_field_paths(self):
        base=kitchen_sink()
        cases=[
         (lambda s:s["layers"][2].update(strokeWidth=3),"layers[2]:unknown fields for rect: strokeWidth"),
         (lambda s:s["layers"][2].update(fill="redish"),"layers[2].fill:invalid colour"),
         (lambda s:s["layers"][2].update(fill="@nope"),"unknown colour token @nope"),
         (lambda s:s["layers"][2].update(fill="url:missing"),"unknown gradient missing"),
         (lambda s:s["layers"][2].update(start_ms=0),"schema v2 uses show/enter/exit/keys"),
         (lambda s:s["layers"][2].update(show=[3000,1000]),"layers[2].show:end must be after start"),
         (lambda s:s["layers"][2].update(show=[0,9000]),"layers[2].show[1]:must be between 0 and 8000"),
         (lambda s:s["layers"][2].update(enter="zoom"),"layers[2].enter:unknown effect"),
         (lambda s:s["layers"][2]["keys"].append({"t":500,"width":10}),"keyframes must be in time order"),
         (lambda s:s["layers"][2]["keys"].append({"t":3500,"r":10}),"property not animatable for rect: r"),
         (lambda s:s["layers"][2]["keys"].append({"t":3500,"fill":"red"}),"animated colours must be"),
         (lambda s:s["layers"][2]["keys"].append({"t":3500,"opacity":2}),"must be between 0 and 1"),
         (lambda s:s["layers"][2]["keys"].append({"t":3500}),"keyframe animates nothing"),
         (lambda s:s["layers"][2]["keys"].append({"t":3500,"width":5,"ease":"bouncy"}),"unknown easing"),
         (lambda s:s["layers"][9]["keys"].append({"t":4000,"d":"M 1 2 L 3 4"}),"morph target must have exactly the same commands"),
         (lambda s:s["layers"][9].update(d="M 0 0 L 10 10 <script>"),"path may only contain SVG path commands"),
         (lambda s:s["layers"][9].update(d="L 0 0"),"path must start with M"),
         (lambda s:s["layers"][1].update(enter="draw"),"draw only works on stroked shapes"),
         (lambda s:s["layers"][2].update(enter="type"),"type only works on text"),
         (lambda s:s["layers"][1].update(text="EDIT: write a title"),"unfinished EDIT: placeholder"),
         (lambda s:s["layers"][0].pop("max_width"),"fit/max_lines need max_width"),
         (lambda s:s["layers"][12]["layers"][0].update(fixed=True),"fixed (ignore the camera) is only allowed on top-level layers"),
         (lambda s:s["layers"][12]["layers"][2].update(asset="nope"),"unknown asset id"),
         (lambda s:s.update(assets={"dot":"data:image/png;base64,"+base64.b64encode(b"GIF89a....").decode()}),"asset bytes are not a real png image"),
         (lambda s:s.update(assets={"dot":"data:image/svg+xml;base64,PHN2Zz4="}),"asset must be data:image/png|jpeg|webp|avif"),
         (lambda s:s["layers"][14].update(count=500),"layers[14].count:must be between 1 and 200"),
         (lambda s:s["layers"][15].update(r=20),"spotlight needs either cx/cy/r"),
         (lambda s:s.update(custom_renderer="function renderCustom(l,t,h){\n'</script>'}"),"custom_renderer:line 2: '</script' would end the page's script element"),
         (lambda s:s.update(custom_renderer="function other(){}"),"must define function renderCustom"),
         (lambda s:s.update(script="function render(t,api){\n var x='<!--';}"),"script:line 2: '<!--'"),
         (lambda s:s.update(script="function draw(t){}"),"script:must define function render(t, api)"),
         (lambda s:s.update(svg="<svg><g>\n<rect></g></svg>"),"svg:not well-formed XML at line 2"),
         (lambda s:s.update(svg="<g/>"),"root element must be <svg>"),
         (lambda s:s.update(svg="<!DOCTYPE svg><svg/>"),"remove <!DOCTYPE>"),
         (lambda s:s.update(svg="<svg><script>alert(1)</script></svg>"),"<script> inside svg is not run"),
         (lambda s:s.update(svg='<svg><image href="https://example.com/a.png"/></svg>'),"external URLs are blocked in production"),
         (lambda s:s.update(svg='<svg><rect style="fill:url(//x.com/a)"/></svg>'),"external url() is blocked"),
         (lambda s:s.update(svg='<svg><style>@import url(https://x.com/a.css);</style></svg>'),"<style> loads external CSS"),
         (lambda s:s.update(svg='<svg><image href="asset:nope"/></svg>'),"unknown asset id"),
         (lambda s:s.update(svg='<svg><rect fill="@nope"/></svg>'),"unknown colour token"),
         (lambda s:s.update(extra=1),"unknown top-level fields extra"),
         (lambda s:s["camera"]["keys"].append({"t":100,"zoom":20}),"camera.keys"),
         (lambda s:s.update(takeaway="EDIT: later"),"takeaway_unfinished_placeholder"),
         (lambda s:s.update(replace="yes"),"replace_intent_must_be_boolean"),
         (lambda s:s["layers"].append({"type":"group","layers":[{"type":"circle","r":1} for _ in range(390)]}),"more than 400 layers in total"),
         (lambda s:s["layers"].extend([{"type":"circle","r":1}]*400),"layers must be a list of 1..400"),
         (lambda s:s["layers"][5].update(repeat={"every_ms":50}),"repeat.every_ms:must be between 100"),
        ]
        for mutate,expected in cases:
            s=copy.deepcopy(base);mutate(s)
            with self.assertRaises(ValueError,msg=expected) as ctx:validate_scene(s,s["qid"],s["duration_ms"])
            self.assertIn(expected,str(ctx.exception))
        s=copy.deepcopy(base);s["qid"]="Q000000001"
        with self.assertRaises(ValueError):validate_scene(s,"Q000000009",8000)
        with self.assertRaises(ValueError):validate_scene(base,"Q000000009",9000)

    def test_free_mode_example_and_script_only_scene_are_valid(self):
        s=json.loads((EXAMPLES/"v2-free-o2-curve.scene.json").read_text())
        validate_scene(s,s["qid"],s["duration_ms"]);self.assertEqual(lint_scene_v2(s),[])
        bare={"schema_version":2,"qid":"Q000000001","duration_ms":3000,"takeaway":"x","script":"function render(t,api){}"}
        validate_scene(bare,"Q000000001",3000)
        html=compile_scene({**bare,"svg":"<svg><circle r='3'/></svg>"})
        self.assertIn('xmlns=\\"http://www.w3.org/2000/svg\\"',html)  # namespace added for DOMParser
        with self.assertRaises(ValueError):validate_scene({**bare,"script":None},"Q000000001",3000)
        w=" ".join(lint_scene_v2({**bare,"script":"function render(t,api){const r=Math.random();const n=Date.now();}"}))
        self.assertIn("Math.random",w);self.assertIn("wall clock",w)

    def test_lint_flags_empty_first_frame_and_overflowing_text(self):
        s={"schema_version":2,"qid":"Q000000001","duration_ms":4000,"takeaway":"x",
           "layers":[{"type":"text","text":"A very long label that will certainly run off the edge of the stage","x":320,"y":40,"size":30,"enter":"fade"}]}
        w=" ".join(lint_scene_v2(s))
        self.assertIn("first frame",w);self.assertIn("add max_width",w)

    def test_v2_package_builds_validates_and_rejects_tampering(self):
        qs=[question(f"Q{n:09d}") for n in (7341,7342,7343)]
        b=adapt_exports([envelope(qs)])
        with tempfile.TemporaryDirectory() as td:
            ws=Path(td)/"ws";scaffold_workspace(b,ws,"V2DEMO",1,[q["id"] for q in qs],None,9000)
            scenes=sorted((ws/"scenes").glob("*.json"))
            for p in scenes:
                d=json.loads(p.read_text());self.assertEqual(d["schema_version"],2)
                with self.assertRaises(ValueError):validate_scene(d,d["qid"],9000)  # EDIT takeaway must block
                d["takeaway"]="Validated v2 scene.";p.write_text(json.dumps(d))
            gold=json.loads((EXAMPLES/"v2-synapse-steps.scene.json").read_text());gold["qid"]=qs[1]["id"];gold["duration_ms"]=9000
            scenes[1].write_text(json.dumps(gold,ensure_ascii=False))
            sink=kitchen_sink(qs[2]["id"],9000);scenes[2].write_text(json.dumps(sink,ensure_ascii=False))
            out=Path(td)/"MCARDS_V2DEMO_r1.zip";paths=build_package_set(b,ws,out)
            self.assertEqual(len(paths),1)
            m=validate_package(paths[0])
            self.assertEqual(m["runtime_version"],1);self.assertEqual(m["protocol_version"],1)
            self.assertEqual(len(m["animations"]),3)
            with zipfile.ZipFile(paths[0]) as z:
                entry=z.read(f"entries/{qs[1]['id']}.html").decode()
                self.assertIn('data-engine="2"',entry)
                names=z.namelist();files={n:z.read(n) for n in names}
            # An attacker who edits the scene (even updating checksums) cannot smuggle a different entry.
            bad=Path(td)/"MCARDS_V2DEMO_r2.zip"
            scene_path=f"scenes/{qs[1]['id']}.scene.json";sc=json.loads(files[scene_path]);sc["layers"][0]["text"]="Changed"
            files[scene_path]=(json.dumps(sc,ensure_ascii=False,indent=2)+"\n").encode()
            man=json.loads(files["motioncards-manifest.json"])
            for r in man["animations"]:
                if r["qid"]==qs[1]["id"]:r["scene_sha256"]=hashlib.sha256(files[scene_path]).hexdigest()
            files["motioncards-manifest.json"]=(json.dumps(man,ensure_ascii=False,indent=2)+"\n").encode()
            with zipfile.ZipFile(bad,"w",zipfile.ZIP_DEFLATED) as z:
                for n,data in files.items():z.writestr(n,data)
            with self.assertRaises(ValueError) as ctx:validate_package(bad)
            self.assertIn("compiled_entry_scene_mismatch",str(ctx.exception))

    def test_v1_and_v2_scenes_mix_in_one_package_and_multipart(self):
        qs=[question(f"Q{n:09d}") for n in range(7341,7347)]
        b=adapt_exports([envelope(qs)])
        with tempfile.TemporaryDirectory() as td:
            ws=Path(td)/"ws";scaffold_workspace(b,ws,"MIXED",1,[q["id"] for q in qs],None,8000)
            for i,p in enumerate(sorted((ws/"scenes").glob("*.json"))):
                if i%2:
                    d=json.loads((EXAMPLES/"flow.scene.json").read_text());d["qid"]=p.name.split(".")[0]
                else:
                    d=json.loads(p.read_text())
                d["takeaway"]="Mixed engines.";p.write_text(json.dumps(d))
            paths=build_package_set(b,ws,Path(td)/"MCARDS_MIXED_r1.zip")
            total=sum(len(validate_package_part(p)["animations"]) for p in paths)
            self.assertEqual(total,6)

class AssetImportTests(unittest.TestCase):
    SRC="""<?xml version="1.0"?><!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" viewBox="10 20 200 100" inkscape:version="1.2">
<metadata>junk</metadata><title>t</title><style>.a{fill:url(#g)}</style>
<defs><linearGradient id="g"><stop offset="0.123456" stop-color="red"/></linearGradient></defs>
<path class="a" d="M1.005.5l2-3" onclick="alert(1)" inkscape:label="x"/><use xlink:href="#g"/></svg>"""
    def test_import_cleans_scales_and_namespaces_ids(self):
        from motioncards.lib.assets import prepare_svg
        g=prepare_svg(self.SRC,"heart",(0,0,400,400))
        self.assertTrue(g.startswith('<g id="heart" transform="translate(-20 60) scale(2 2)">'),g[:80])
        for gone in ("metadata","<title","inkscape","onclick","DOCTYPE"):self.assertNotIn(gone,g)
        self.assertIn('id="heart-0"',g);self.assertIn("url(#heart-0)",g);self.assertIn('href="#heart-0"',g)
        self.assertIn(".heart-a{",g);self.assertIn('class="heart-a"',g)
        self.assertIn('d="M1 .5l2-3"',g)           # rounded numbers never merge
        self.assertIn('offset="0.12"',g)           # offsets keep 2 decimals even when paths use fewer
        self.assertIn('d="M1 0L3-2"',prepare_svg(self.SRC,"heart",(0,0,400,400),0))

    def test_path_optimizer_has_no_drift_and_parses_back(self):
        import random,re as _re
        from motioncards.lib.assets import optimize_path,PATH_TOKEN
        def ends(d):                                # absolute end point of every segment
            toks=PATH_TOKEN.findall(d);out=[];x=y=sx=sy=0.0;i=0;cmd=""
            n={"M":2,"L":2,"H":1,"V":1,"C":6,"S":4,"Q":4,"T":2,"A":7,"Z":0}
            while i<len(toks):
                if toks[i].isalpha():cmd=toks[i];i+=1
                U=cmd.upper();r=cmd.islower();a=[float(v) for v in toks[i:i+n[U]]];i+=n[U]
                if U=="Z":x,y=sx,sy;cmd=""
                elif U=="H":x=x+a[0] if r else a[0]
                elif U=="V":y=y+a[0] if r else a[0]
                else:
                    x,y=(x+a[-2],y+a[-1]) if r else (a[-2],a[-1])
                    if U=="M":sx,sy=x,y;cmd="l" if r else "L"
                out.append((round(x,6),round(y,6)))
            return out
        rnd=random.Random(7)
        parts=["m%.3f %.3f"%(rnd.uniform(0,300),rnd.uniform(0,300))]
        for k in range(400):
            c=rnd.choice("clhvsz");f=lambda:"%.3f"%rnd.uniform(-9,9)
            parts.append(c+" ".join(f() for _ in range({"c":6,"l":2,"h":1,"v":1,"s":4,"z":0}[c])))
            if c=="z":parts.append("m%s %s"%(f(),f()))
        d="".join(parts)
        for dec in (0,1,2):
            o=optimize_path(d,dec)
            self.assertLess(len(o),len(d))
            for (x0,y0),(x1,y1) in zip(ends(d),ends(o)):
                self.assertLessEqual(max(abs(x0-x1),abs(y0-y1)),0.5*10**-dec+1e-9)   # error never accumulates
        self.assertEqual(optimize_path("M0 0A5 5 0 0 1 10 0z",2),"M0 0A5 5 0 0 1 10 0z")
        self.assertEqual(optimize_path("M.5.5l.25.25",2),"M.5.5L.75.75")

    def test_auto_precision_and_colour_shortening(self):
        from motioncards.lib.assets import auto_decimals,prepare_svg
        self.assertEqual(auto_decimals(0.45),1);self.assertEqual(auto_decimals(1.2),1);self.assertEqual(auto_decimals(2.5),2)
        g=prepare_svg('<svg viewBox="0 0 10 10"><path d="M1.23456 1L2 2" fill="#ffcc00" stroke="#12ab34"/></svg>',"c",(0,0,10,10))
        self.assertIn('fill="#fc0"',g);self.assertIn('stroke="#12ab34"',g);self.assertIn('d="M1.2 1L2 2"',g)

    def test_two_imports_validate_together_and_template_goes_to_defs(self):
        from motioncards.lib.assets import prepare_svg,prepare_template,add_to_scene,AssetImportError
        scene={"schema_version":2,"qid":"Q000000001","duration_ms":3000,"takeaway":"x","script":"function render(t,api){}"}
        add_to_scene(scene,prepare_svg(self.SRC,"one",(0,0,100,100)),"Art: Example, CC BY 4.0")
        add_to_scene(scene,prepare_template(self.SRC,"two",40,40),"Art: Example, CC BY 4.0")
        self.assertEqual(scene["credits"],["Art: Example, CC BY 4.0"])
        self.assertIn('<defs><g id="two"',scene["svg"])
        validate_scene(scene,"Q000000001",3000)
        self.assertIn("Art: Example",compile_scene(scene))
        with self.assertRaises(AssetImportError):add_to_scene(scene,prepare_svg(self.SRC,"one",(0,0,10,10)))

    def test_restricted_licences_are_refused_and_flagged(self):
        from motioncards.lib.assets import prepare_svg,add_to_scene,AssetImportError
        scene={"schema_version":2,"qid":"Q000000001","duration_ms":3000,"takeaway":"x","script":"function render(t,api){}"}
        frag=prepare_svg(self.SRC,"one",(0,0,100,100))
        for bad in ["Art: X, CC BY-NC 4.0","Art: X, CC-BY-ND","Art: X, non-commercial use only","Art: X, CC BY NC SA"]:
            with self.assertRaises(AssetImportError):add_to_scene(dict(scene),frag,bad)
        add_to_scene(scene,frag,"Heart: Servier Medical Art, CC BY 4.0")
        self.assertEqual(lint_scene_v2(scene),[])
        scene["credits"].append("Cell: Y, CC BY-NC-SA 4.0")
        self.assertTrue(any("NC/ND" in w for w in lint_scene_v2(scene)))

    def test_lint_warns_on_complex_organic_morph(self):
        d="M 0 0 "+" ".join(f"C {i} {i+1} {i+2} {i+3} {i+4} {i+5}" for i in range(12))
        d2="M 1 1 "+" ".join(f"C {i} {i+2} {i+2} {i+3} {i+4} {i+6}" for i in range(12))
        s={"schema_version":2,"qid":"Q000000001","duration_ms":3000,"takeaway":"x",
           "layers":[{"type":"path","d":d,"keys":[{"t":0,"d":d},{"t":3000,"d":d2}]}]}
        validate_scene(s,"Q000000001",3000)
        self.assertTrue(any("cross-fade" in w for w in lint_scene_v2(s)))
        self.assertFalse(any("cross-fade" in w for w in lint_scene_v2(json.loads((EXAMPLES/"v2-stenosis-flow.scene.json").read_text()))))

    def test_bundled_art_library_imports_and_validates(self):
        from motioncards.lib.assets import library_index,library_art,prepare_svg,add_to_scene,LIBRARY_DIR
        idx=library_index()
        self.assertTrue(idx["art"])
        for name,item in idx["art"].items():
            self.assertTrue((LIBRARY_DIR/item["file"]).is_file(),name)
            text,credit=library_art(name)
            scene={"schema_version":2,"qid":"Q000000001","duration_ms":3000,"takeaway":"x","script":"function render(t,api){}"}
            add_to_scene(scene,prepare_svg(text,"art",(0,0,300,300)),credit)
            validate_scene(scene,"Q000000001",3000)
            self.assertEqual(lint_scene_v2(scene),[],name)

    def test_style_kit_is_added_once_and_needs_no_runtime_change(self):
        from motioncards.lib.assets import add_style_kit
        scene={"schema_version":2,"qid":"Q000000001","duration_ms":3000,"takeaway":"x",
               "svg":'<svg xmlns="http://www.w3.org/2000/svg"><circle r="5" fill="url(#kit-tissue)" filter="url(#kit-volume)"/></svg>',
               "script":"function render(t,api){}"}
        self.assertTrue(add_style_kit(scene));self.assertFalse(add_style_kit(scene))
        self.assertEqual(scene["svg"].count('id="kit"'),1)
        self.assertTrue(scene["svg"].startswith('<svg xmlns="http://www.w3.org/2000/svg"><defs id="kit">'))
        for kid in ("kit-volume","kit-volume-sm","kit-gloss","kit-shadow","kit-glow","kit-tissue","kit-muscle","kit-nerve"):self.assertIn(f'id="{kid}"',scene["svg"])
        validate_scene(scene,"Q000000001",3000)
        self.assertIn('id=\\"kit-volume\\"',compile_scene(scene))

    def test_recipes_are_added_once_and_validate(self):
        from motioncards.lib.assets import add_recipes,add_style_kit,RECIPES_BEGIN
        scene={"schema_version":2,"qid":"Q000000001","duration_ms":3000,"takeaway":"x","script":"function render(t,api){}"}
        self.assertTrue(add_recipes(scene));self.assertFalse(add_recipes(scene))
        self.assertEqual(scene["script"].count(RECIPES_BEGIN),1)
        self.assertTrue(scene["script"].endswith("function render(t,api){}"))
        add_style_kit(scene);validate_scene(scene,"Q000000001",3000)
        self.assertEqual(lint_scene_v2(scene),[])
        scene["script"]+="\nfunction setup(api){R.grid(api);}"
        self.assertTrue(any("R.grid" in w for w in lint_scene_v2(scene)))

    def test_illustrator_exports_import_but_other_entities_are_refused(self):
        from motioncards.lib.assets import prepare_svg,AssetImportError
        ai=("<?xml version=\"1.0\"?><!-- Generator: Adobe Illustrator -->"
            "<!DOCTYPE svg PUBLIC \"-//W3C//DTD SVG 1.1//EN\" \"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd\" [\n"
            "\t<!ENTITY ns_extend \"http://ns.adobe.com/Extensibility/1.0/\">\n\t<!ENTITY ns_ai \"http://ns.adobe.com/AdobeIllustrator/10.0/\">\n]>"
            "<svg xmlns:x=\"&ns_extend;\" xmlns:i=\"&ns_ai;\" xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 10 10\">"
            "<switch><foreignObject requiredExtensions=\"&ns_ai;\" x=\"0\" y=\"0\" width=\"1\" height=\"1\"><i:pgf>PRIVATE</i:pgf></foreignObject>"
            "<g i:extraneous=\"self\"><rect width=\"4\" height=\"4\" fill=\"#a59983\"/></g></switch></svg>")
        g=prepare_svg(ai,"bone",(0,0,100,100))
        self.assertIn("<rect",g);self.assertNotIn("foreignObject",g);self.assertNotIn("PRIVATE",g);self.assertNotIn("&",g)
        for bad in ['<!DOCTYPE svg [<!ENTITY a "http://x.com/">]><svg viewBox="0 0 1 1"><text>&a;</text></svg>',   # URL entity used in text
                    '<!DOCTYPE svg [<!ENTITY a "plain">]><svg xmlns:a="&a;" viewBox="0 0 1 1"/>',                    # not a URL
                    '<!DOCTYPE svg [<!ENTITY a SYSTEM "file:///etc/passwd">]><svg viewBox="0 0 1 1"/>',              # external entity
                    '<!DOCTYPE svg [<!ENTITY % p "x">]><svg viewBox="0 0 1 1"/>',                                     # parameter entity
                    '<!DOCTYPE svg [<!ENTITY a "http://x.com/"><!ELEMENT svg ANY>]><svg viewBox="0 0 1 1"/>']:       # other declarations
            with self.assertRaises(AssetImportError,msg=bad):prepare_svg(bad,"x",(0,0,10,10))

    def test_import_rejects_external_resources_and_entities(self):
        from motioncards.lib.assets import prepare_svg,AssetImportError
        for bad in ['<svg viewBox="0 0 1 1"><image href="https://x.com/a.png"/></svg>',
                    '<svg viewBox="0 0 1 1"><style>@import url(//x.com/a.css);</style></svg>',
                    '<!DOCTYPE svg [<!ENTITY a "b">]><svg viewBox="0 0 1 1"><text>&a;</text></svg>',
                    '<svg><rect/></svg>']:
            with self.assertRaises(AssetImportError):prepare_svg(bad,"x",(0,0,10,10))

@unittest.skipUnless(shutil.which("chromium") or os.environ.get("MOTIONCARDS_CHROMIUM") or os.environ.get("MOTIONCARDS_BROWSER_TESTS")=="1","browser runtime tests need Chromium (set MOTIONCARDS_BROWSER_TESTS=1 or MOTIONCARDS_CHROMIUM)")
class EngineV2BrowserTests(unittest.TestCase):
    def test_every_feature_renders_without_errors_and_seeks_deterministically(self):
        try:import playwright  # noqa: F401
        except ImportError:self.skipTest("playwright not installed")
        from motioncards.lib.render import render_scenes
        scenes=[json.loads(p.read_text()) for p in sorted(EXAMPLES.glob("v2-*.scene.json"))]+[kitchen_sink()]
        with tempfile.TemporaryDirectory() as td:
            reports=render_scenes(scenes,Path(td),frames=7,sizes=["phone","tablet"],sheet=False)
            self.assertEqual(len(reports),len(scenes))
            for r in reports:self.assertEqual(len(r["frames"]),14)

    def test_every_recipe_runs_and_seeks_deterministically(self):
        try:import playwright  # noqa: F401
        except ImportError:self.skipTest("playwright not installed")
        from motioncards.lib.render import render_scenes
        from motioncards.lib.assets import add_recipes,add_style_kit
        script="""let a,b,c,d,e,f,g,h,k,m,n,st,L;
function setup(api){const P=api.svg;st=api.el("rect",{x:20,y:20,width:200,height:120,fill:"#ddd"},P);st=R.wrap(api,st);
 a=R.tube(api,P,"M40 200C120 160 220 240 300 200","artery",8,{behind:st});b=R.tube(api,P,"M40 260C120 240 220 280 300 250","nerve",5);
 c=R.flow(api,P,a.p,{n:5});d=R.impulses(api,P,b.p,{reverse:true});e=R.bleed(api,P,320,120,{gravity:30});f=R.drip(api,P,360,60);
 g=R.lump(api,P,450,300,"cyst");h=R.lump(api,P,520,200,"tumour");k=R.ulcer(api,P,250,90);m=R.glow(api,P,100,320);
 n=R.travel(api,P,"M380 360C420 400 480 420 560 430",{width:20});L=R.callout(api,P,"Label\\ntwo lines",400,60,"#b3202a",[320,120]);}
function render(t,api){const s=t/3000;R.seeThrough(api,st,s);R.drawOn(api,b,s);R.squeeze(api,a,s,8,3);c.update(t,1);d.update(t,1);e.update(t,s);f.update(t,1-s);
 g.update(t,s,60,40,true);h.update(t,s,30);k.update(t,s);m.update(t,1);n.update(t,s);R.fade(api,L,t,0,500,2500,3000);R.scaleAbout(api,h.el,1+0.1*s);}"""
        scene={"schema_version":2,"qid":"Q000000007","duration_ms":3000,"takeaway":"Recipes test.","script":script}
        add_recipes(scene);add_style_kit(scene)
        validate_scene(scene,"Q000000007",3000)
        with tempfile.TemporaryDirectory() as td:
            r=render_scenes([scene],Path(td),frames=5,sizes=["phone","tablet"],sheet=False)
            self.assertEqual(len(r[0]["frames"]),10)

    def _bare(self,script,svg=None,qid="Q000000006"):
        s={"schema_version":2,"qid":qid,"duration_ms":2000,"takeaway":"Free mode test.","script":script}
        if svg:s["svg"]=svg
        return s

    def test_free_mode_errors_are_reported_with_location_and_runtime_names_cannot_collide(self):
        try:import playwright  # noqa: F401
        except ImportError:self.skipTest("playwright not installed")
        from motioncards.lib.render import render_scenes
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)
            # Author globals that shadow runtime internals must not break the card.
            ok=self._bare("const W=1,H=2,D=3,svg=null,cam=null,MC=null,CONFIG=null,root=null;function clamp(){return 0}\n"
                          "let n=0;function setup(api){n=api.$$('circle').length;}\n"
                          "function render(t,api){api.set(api.$('#c'),{cx:20+t/20,fill:'@accent'});setTimeout(()=>{throw new Error('timer ran')},0);requestAnimationFrame(()=>{throw new Error('raf ran')});}",
                          "<svg><circle id='c' cx='20' cy='20' r='10'/></svg>")
            r=render_scenes([ok],out,frames=3,sizes=["phone"],sheet=False)
            self.assertTrue(any("inert" in x for x in r[0]["notes"]),r[0]["notes"])
            with self.assertRaises(RuntimeError) as ctx:render_scenes([self._bare("function render(t,api){\n  let x = ;\n}")],out,frames=2,sizes=["phone"],sheet=False)
            self.assertIn("script line 2",str(ctx.exception))
            with self.assertRaises(RuntimeError) as ctx:render_scenes([self._bare("function render(t,api){ if(t>1500) api.set(api.$('#missing'),{x:1}); }")],out,frames=3,sizes=["phone"],sheet=False)
            self.assertIn("render(t=2000): api.set: element not found",str(ctx.exception))
            with self.assertRaises(RuntimeError) as ctx:render_scenes([self._bare("let x=0;function render(t,api){x+=1;api.el('rect',{x:x,width:5,height:5});}")],out,frames=3,sizes=["phone"],sheet=False)
            self.assertIn("differs depending on the previous frame",str(ctx.exception))

    def test_scale_and_rotate_happen_around_the_shape_centre_and_errors_are_reported(self):
        try:from playwright.sync_api import sync_playwright
        except ImportError:self.skipTest("playwright not installed")
        from motioncards.lib import render as R
        scene={"schema_version":2,"qid":"Q000000005","duration_ms":2000,"takeaway":"Centre stays fixed.",
               "layers":[{"type":"circle","id":"c","cx":150,"cy":225,"r":72,"keys":[{"t":0,"scale":0.5},{"t":2000,"scale":1}]},
                         {"type":"rect","x":300,"y":200,"width":100,"height":50,"keys":[{"t":0,"rotate":0},{"t":2000,"rotate":90}]}]}
        html=compile_scene(scene,[R.ORIGIN],preview=True)
        with sync_playwright() as p:
            browser=R._launch(p)
            try:
                ctx=browser.new_context();blocked=[];ctx.route("**/*",R._router(html,scene["qid"],blocked))
                page=ctx.new_page();page.goto(R.HOST_URL)
                page.evaluate("([s,q])=>mcLoad(s,q,640,560)",[R.ORIGIN+"/Q000000005.html","Q000000005"])
                page.wait_for_function("window.mcReady===true",timeout=8000)
                frame=page.frames[1]
                centres=[]
                for t in (0,1000,2000):
                    page.evaluate("ms=>mcSeek(ms)",t)
                    centres.append(frame.evaluate("""()=>{const svg=document.getElementById('stage'),m=svg.getScreenCTM().inverse();
                      const box=e=>{const b=e.getBoundingClientRect(),p=svg.createSVGPoint();p.x=b.left+b.width/2;p.y=b.top+b.height/2;const q=p.matrixTransform(m);return[q.x,q.y]};
                      return [box(document.querySelector('circle')),box(document.querySelector('#stage rect:not([width="5760"])')),document.querySelector('circle').getBoundingClientRect().width]}"""))
                for c,_,_ in centres:
                    self.assertAlmostEqual(c[0],150,delta=1);self.assertAlmostEqual(c[1],225,delta=1)
                for _,r,_ in centres:
                    self.assertAlmostEqual(r[0],350,delta=1);self.assertAlmostEqual(r[1],225,delta=1)
                self.assertLess(centres[0][2],centres[2][2]*0.6)
                self.assertEqual(blocked,[])
            finally:
                browser.close()

if __name__=="__main__":unittest.main()
