#!/usr/bin/env python3
from __future__ import annotations
import argparse,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILES=[
 "motioncards/__init__.py","motioncards/README.md","motioncards/PROJECT_BRIEF.md","motioncards/MASTER_PROMPT.md","motioncards/TOOLKIT.md","motioncards/AGENTS.md",
 "motioncards/schema/motioncards-manifest.schema.json","motioncards/schema/scene.schema.json","motioncards/golden/canonical-v1.json",
 "motioncards/lib/__init__.py","motioncards/lib/spec.py","motioncards/lib/core.py","motioncards/lib/compiler.py","motioncards/lib/package.py","motioncards/lib/multipart.py","motioncards/lib/engine_v2.py","motioncards/lib/render.py","motioncards/lib/assets.py","motioncards/lib/voice.py","motioncards/AUTHORING_V2.md",
 "motioncards/library/library.json","motioncards/library/style_kit.svg","motioncards/library/recipes.js",
 "motioncards/examples/flow.scene.json","motioncards/examples/sequence.scene.json","motioncards/examples/v2-stenosis-flow.scene.json","motioncards/examples/v2-synapse-steps.scene.json","motioncards/examples/v2-free-o2-curve.scene.json","motioncards/examples/v2-imported-art-sickle.scene.json","tools/motioncards.py"
]
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--out",type=Path,required=True);a=ap.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(a.out,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  # The bundled art library is read by `library`, `import-svg lib:<name>`, `style-kit` and `recipes`.
  art=sorted(p.relative_to(ROOT).as_posix() for p in (ROOT/"motioncards/library/art").glob("*.svg"))
  for name in FILES+art:z.write(ROOT/name,name)
 print(a.out)
if __name__=="__main__":main()
