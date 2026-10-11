// node build.js <svgRoot> <outDir> : inline engine, css, scene + base64 SVG layers into standalone HTML
const fs=require('fs'),path=require('path');
const [root,out]=process.argv.slice(2);
const css=fs.readFileSync(path.join(__dirname,'style.css'),'utf8');
const eng=fs.readFileSync(path.join(__dirname,'engine.js'),'utf8');
fs.mkdirSync(out,{recursive:true});
for(const f of fs.readdirSync(path.join(__dirname,'scenes')).filter(f=>f.endsWith('.js')).sort()){
  const src=fs.readFileSync(path.join(__dirname,'scenes',f),'utf8');
  const files=[...new Set([...src.matchAll(/'(\d\d_[^']+\.svg)'/g)].map(m=>m[1]))];
  const L={}; for(const s of files) L[s]=fs.readFileSync(path.join(root,s)).toString('base64');
  const title=(src.match(/title:\s*'([^']+)'/)||[])[1]||f;
  const html=`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=1280"><title>${title.replace(/<[^>]+>/g,'')}</title><style>${css}</style></head><body><div id="root"></div><script>window.__L=${JSON.stringify(L)};</script><script>${src}</script><script>${eng}</script></body></html>`;
  fs.writeFileSync(path.join(out,f.replace(/\.js$/,'.html')),html);
  console.log(f,(html.length/1024|0)+'KB');
}
