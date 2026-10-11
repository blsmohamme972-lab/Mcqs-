// node render1.js page.html seconds out.mp4 audio.wav
const { chromium } = require('playwright'); const {spawn}=require('child_process');
(async()=>{
 const [f,secs,out,aud]=process.argv.slice(2); const N=Math.round(+secs*30);
 const b=await chromium.launch(); const p=await b.newPage({viewport:{width:1280,height:720}});
 p.on('pageerror',e=>console.log('ERR',e.message));
 await p.goto('file://'+f+'?capture'); await p.waitForTimeout(500);
 const ff=spawn('ffmpeg',['-loglevel','error','-y','-f','image2pipe','-framerate','30','-i','-','-i',aud,'-c:v','libx264','-preset','slow','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-shortest','-movflags','+faststart',out]);
 for(let i=0;i<N;i++){await p.evaluate(t=>renderFrame(t),i/30); const buf=await p.screenshot({type:'jpeg',quality:95}); if(!ff.stdin.write(buf)) await new Promise(r=>ff.stdin.once('drain',r));}
 ff.stdin.end(); await new Promise(r=>ff.on('close',r)); await b.close();
})();
