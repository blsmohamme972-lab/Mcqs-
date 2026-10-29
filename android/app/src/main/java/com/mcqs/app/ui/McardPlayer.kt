package com.mcqs.app.ui

import android.annotation.SuppressLint
import android.app.Activity
import android.content.Context
import android.content.ContextWrapper
import android.content.pm.ActivityInfo
import android.webkit.JavascriptInterface
import android.webkit.WebSettings
import android.webkit.WebView
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import java.io.File

/** The origin the lessons trust as their host (their `allowed_host_origins`). */
private const val HOST_ORIGIN = "https://kafu.blsmohamme97.workers.dev/"

/**
 * Full-screen landscape player for an MCARDS image lesson. The lesson is a sandboxed HTML card; this page is its host:
 * it connects over a MessageChannel, takes the embedded voice (Ogg Opus), plays it and uses it as the master clock,
 * ticking the card every frame so picture and voice stay in sync. Tap pauses/plays; back closes.
 */
@Composable
fun McardPlayer(entry: File, onClose: () -> Unit) {
    val activity = LocalContext.current.findActivity()
    DisposableEffect(activity) {
        val previous = activity?.requestedOrientation ?: ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED
        activity?.requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE
        activity?.window?.let { w ->
            WindowCompat.setDecorFitsSystemWindows(w, false)
            WindowInsetsControllerCompat(w, w.decorView).apply {
                hide(WindowInsetsCompat.Type.systemBars())
                systemBarsBehavior = WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
            }
        }
        onDispose {
            activity?.requestedOrientation = previous
            activity?.window?.let { w ->
                WindowInsetsControllerCompat(w, w.decorView).show(WindowInsetsCompat.Type.systemBars())
                WindowCompat.setDecorFitsSystemWindows(w, true)
            }
        }
    }
    BackHandler(onBack = onClose)
    Box(Modifier.fillMaxSize().background(Color.Black)) {
        McardWebView(entry, Modifier.fillMaxSize())
    }
}

@SuppressLint("SetJavaScriptEnabled")
@Composable
private fun McardWebView(entry: File, modifier: Modifier) {
    AndroidView(
        modifier = modifier,
        factory = { ctx ->
            WebView(ctx).apply {
                setBackgroundColor(android.graphics.Color.BLACK)
                settings.javaScriptEnabled = true
                settings.allowFileAccess = false
                settings.allowContentAccess = false
                settings.mediaPlaybackRequiresUserGesture = false
                settings.cacheMode = WebSettings.LOAD_NO_CACHE
                addJavascriptInterface(object {
                    @JavascriptInterface fun entry(): String = entry.readText()
                }, "Host")
                loadDataWithBaseURL(HOST_ORIGIN, HOST_HTML, "text/html", "utf-8", null)
            }
        },
        onRelease = { it.destroy() },
    )
}

private tailrec fun Context.findActivity(): Activity? = when (this) {
    is Activity -> this
    is ContextWrapper -> baseContext.findActivity()
    else -> null
}

// language=HTML
private val HOST_HTML = """
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>html,body{margin:0;height:100%;background:#000;overflow:hidden}iframe{border:0;width:100%;height:100%;display:block;background:#fff}
#msg{position:fixed;left:0;right:0;bottom:0;padding:6px;text-align:center;color:#fff;font:14px system-ui;background:#0008}
#tap{position:fixed;inset:0}</style></head><body>
<iframe id="f" sandbox="allow-scripts"></iframe><div id="tap"></div><div id="msg" hidden></div>
<script>
const f=document.getElementById('f'),msg=document.getElementById('msg');
const channel=Array.from(crypto.getRandomValues(new Uint8Array(18)),x=>x.toString(16).padStart(2,'0')).join('');
let port=null,qid='',duration=0,audio=null,playing=false,t=0,anchor=0,raf=0,ready=false;
const send=(type,extra)=>port&&port.postMessage(Object.assign({type,protocol:1,channel_id:channel,qid},extra||{}));
const fail=text=>{msg.hidden=false;msg.textContent=text};
function paint(type){send(type,{time_ms:Math.max(0,Math.min(duration,t))})}
function tick(now){
  if(!playing)return;
  t=audio&&!audio.paused?audio.currentTime*1000:now-anchor;
  if(t>=duration||(audio&&audio.ended)){t=duration;playing=false;paint('tick');return}
  paint('tick');raf=requestAnimationFrame(tick);
}
function play(){
  if(!ready)return;
  if(t>=duration){t=0;send('restart',{time_ms:0});if(audio)audio.currentTime=0}
  playing=true;anchor=performance.now()-t;send('play',{time_ms:t});
  if(audio){audio.currentTime=t/1000;audio.play().catch(()=>{})}
  raf=requestAnimationFrame(tick);
}
function pause(){playing=false;cancelAnimationFrame(raf);if(audio)audio.pause();send('pause',{time_ms:t})}
document.getElementById('tap').onclick=()=>playing?pause():play();
async function onVoice(m){
  const d=await crypto.subtle.digest('SHA-256',m.data),hex=Array.from(new Uint8Array(d),x=>x.toString(16).padStart(2,'0')).join('');
  if(hex!==m.sha256){fail('voice checksum failed');return}
  audio=new Audio(URL.createObjectURL(new Blob([m.data],{type:'audio/ogg; codecs=opus'})));
  if(ready&&!playing&&t===0)play();
}
function onMsg(e){
  const m=e.data;if(!m||m.channel_id!==channel)return;
  if(m.type==='ready'){duration=m.duration_ms;ready=true;setTimeout(()=>{if(!playing&&t===0)play()},400)}
  else if(m.type==='voice')onVoice(m);
  else if(m.type==='error')fail('lesson error');
}
addEventListener('message',ev=>{
  const m=ev.data;
  if(ev.source!==f.contentWindow||!m||m.type!=='kafu-motioncards-ready'||m.channel_id!==channel)return;
  qid=m.qid;const ch=new MessageChannel();port=ch.port1;port.onmessage=onMsg;
  f.contentWindow.postMessage({type:'connect',protocol:1,channel_id:channel,qid},'*',[ch.port2]);
});
try{f.src=URL.createObjectURL(new Blob([Host.entry()],{type:'text/html'}))+'#'+channel}catch(e){fail('cannot open lesson')}
</script></body></html>
""".trimIndent()
