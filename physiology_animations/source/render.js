// node render.js htmlDir outDir  -> 8 s, 30 fps H.264 MP4 per scene
const { chromium } = require('playwright'); const fs=require('fs'),path=require('path'),{spawn}=require('child_process');
(async()=>{
 const [dir,out]=process.argv.slice(2); fs.mkdirSync(out,{recursive:true});
 const b=await chromium.launch();
 const files=fs.readdirSync(dir).filter(f=>f.endsWith('.html')&&(!process.argv[4]||f.startsWith(process.argv[4]))).sort();
 await Promise.all([0,1,2].map(async w=>{
  const p=await b.newPage({viewport:{width:1280,height:720},deviceScaleFactor:1});
  p.on('pageerror',e=>console.log('ERR',e.message));
  for(const f of files.filter((_,i)=>i%3==w)){
   await p.goto('file://'+path.join(dir,f)+'?capture'); await p.waitForTimeout(500);
   const mp4=path.join(out,f.replace('.html','.mp4'));
   const ff=spawn('ffmpeg',['-loglevel','error','-y','-f','image2pipe','-framerate','30','-i','-','-c:v','libx264','-preset','slow','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',mp4]);
   for(let i=0;i<240;i++){ await p.evaluate(t=>renderFrame(t),i/30); const buf=await p.screenshot({type:'png'}); if(!ff.stdin.write(buf)) await new Promise(r=>ff.stdin.once('drain',r)); }
   ff.stdin.end(); await new Promise(r=>ff.on('close',r)); console.log('done',f);
  }
 }));
 await b.close();
})();
