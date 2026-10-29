#!/usr/bin/env python3
"""Cut single drawings out of Servier Medical Art (SMART) PowerPoint sets as clean, cropped SVG.

SMART (smart.servier.com, CC BY 4.0) publishes its everyday art (people, lifestyle, food, equipment)
as vector shapes inside .pptx sets, not as SVG files. Each drawing on a slide is one top-level group.

  python3 tools/motioncards_smart.py list SMART-People.pptx            # slide titles and group names
  python3 tools/motioncards_smart.py extract SMART-People.pptx 14 "Group 903" woman.svg
  python3 tools/motioncards_smart.py extract SMART-Risk-Factors.pptx 7 "Group 3" woman.svg --also "Group 824"   # body + clothes
  python3 tools/motioncards.py import-svg woman.svg --scene … --id woman --box … \\
    --credit "Woman: Servier Medical Art (smart.servier.com), CC BY 4.0"

Needs LibreOffice (soffice), poppler (pdftocairo) and playwright + Chromium (MOTIONCARDS_CHROMIUM).
"""
from __future__ import annotations
import argparse,os,re,shutil,subprocess,sys,tempfile,zipfile
import xml.etree.ElementTree as ET
P="http://schemas.openxmlformats.org/presentationml/2006/main";A="http://schemas.openxmlformats.org/drawingml/2006/main"
def _slides(z):return sorted((int(m.group(1)),n) for n in z.namelist() if (m:=re.fullmatch(r"ppt/slides/slide(\d+)\.xml",n)))
def _tree(xml):return ET.fromstring(xml).find(f".//{{{P}}}spTree")
def cmd_list(a):
    z=zipfile.ZipFile(a.deck)
    for no,name in _slides(z):
        tree=_tree(z.read(name));groups=[]
        title=" ".join(t.text or "" for t in tree.iter(f"{{{A}}}t") if t.text).strip()[:40]
        for c in tree:
            if c.tag.endswith("}grpSp"):
                nv=c.find(f".//{{{P}}}cNvPr");off=c.find(f"./{{{P}}}grpSpPr/{{{A}}}xfrm/{{{A}}}off")
                groups.append(f'"{nv.get("name")}"@x={int(off.get("x"))//12700 if off is not None else "?"}')
        if groups:print(f"{no:3}  {title:40}  {'  '.join(groups)}")
def cmd_extract(a):
    from playwright.sync_api import sync_playwright
    src=zipfile.ZipFile(a.deck);name=f"ppt/slides/slide{a.slide}.xml";tmp=tempfile.mkdtemp()
    try:
        one=os.path.join(tmp,"one.pptx")
        with zipfile.ZipFile(one,"w",zipfile.ZIP_DEFLATED) as z:
            for i in src.infolist():
                data=src.read(i.filename)
                if i.filename==name:
                    s=data.decode()
                    for pre,uri in re.findall(r'xmlns:(\w+)="([^"]+)"',s):ET.register_namespace(pre,uri)
                    root=ET.fromstring(s);tree=root.find(f".//{{{P}}}spTree");found=False
                    for c in list(tree):
                        if c.tag.endswith(("}sp","}pic","}grpSp","}graphicFrame","}cxnSp")):
                            nv=c.find(f".//{{{P}}}cNvPr")
                            if c.tag.endswith("}grpSp") and nv is not None and nv.get("name") in [a.group]+a.also:found=True
                            else:tree.remove(c)
                    if not found:sys.exit(f"no top-level group named {a.group!r} on slide {a.slide}; run: list")
                    root.set("showMasterSp","0")                     # hide the slide master (background, logo, footer)
                    data=ET.tostring(root,xml_declaration=True,encoding="UTF-8")
                z.writestr(i,data)
        subprocess.run(["soffice","--headless","--convert-to","pdf","--outdir",tmp,one],check=True,capture_output=True)
        svg=os.path.join(tmp,"p.svg")
        subprocess.run(["pdftocairo","-svg","-f",str(a.slide),"-l",str(a.slide),os.path.join(tmp,"one.pdf"),svg],check=True)
        s=re.sub(r"<image\b[^>]*/>","",open(svg).read())
        with sync_playwright() as pw:
            exe=os.environ.get("MOTIONCARDS_CHROMIUM");b=pw.chromium.launch(**({"executable_path":exe} if exe else {}));pg=b.new_page();pg.set_content(s)
            # drop page-sized backgrounds, then crop the viewBox to what is left
            s,bb=pg.evaluate("""()=>{const svg=document.querySelector('svg'),W=svg.viewBox.baseVal.width,H=svg.viewBox.baseVal.height;
              for(const el of [...svg.querySelectorAll('path,rect')]){if(el.closest('defs,clipPath,mask,symbol'))continue;const r=el.getBBox();if(r.width>W*0.9&&r.height>H*0.9)el.remove();}
              const r=svg.getBBox();return [svg.outerHTML,[r.x,r.y,r.width,r.height]]}""");b.close()
        x,y,w,h=bb;pad=2
        s=re.sub(r'<svg([^>]*?) width="[^"]*" height="[^"]*" viewBox="[^"]*"',f'<svg\\1 viewBox="{x-pad:.1f} {y-pad:.1f} {w+2*pad:.1f} {h+2*pad:.1f}"',s,count=1)
        open(a.out,"w").write(s);print(f"{a.out}: {len(s)} bytes, {w:.0f}x{h:.0f}")
    finally:shutil.rmtree(tmp,ignore_errors=True)
def main():
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);sub=ap.add_subparsers(dest="cmd",required=True)
    l=sub.add_parser("list");l.add_argument("deck");l.set_defaults(f=cmd_list)
    e=sub.add_parser("extract");e.add_argument("deck");e.add_argument("slide",type=int);e.add_argument("group");e.add_argument("out");e.add_argument("--also",action="append",default=[],metavar="GROUP",help="keep another group too (e.g. clothes drawn over a body)");e.set_defaults(f=cmd_extract)
    a=ap.parse_args();a.f(a)
if __name__=="__main__":main()
