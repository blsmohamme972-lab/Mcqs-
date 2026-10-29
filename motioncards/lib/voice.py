"""Voice-over tracks for MotionCards (see voiceover/).

A card's voice is one Ogg Opus file. The compiler embeds it in the entry HTML as base64, and the card
hands the bytes to the host over its existing MessageChannel right after `ready`. The card never plays
media itself (its CSP keeps media-src 'none'); the host verifies the SHA-256 and plays it on the
student's Play tap, using the voice as the master clock so picture and sound stay in sync.
"""
from __future__ import annotations
import base64, hashlib
from .spec import VOICE_MIME, MAX_VOICE_BYTES, MAX_VOICE_CUES

VOICE_JS = r"""(function(){
const el=document.getElementById('kafu-voice'),C=typeof __MC_BOOT==='object'&&__MC_BOOT.config;if(!el||!C)return;let sent=false;
addEventListener('message',ev=>{
 if(sent||ev.source!==parent||!C.allowed_host_origins.includes(ev.origin))return;
 const m=ev.data,port=ev.ports&&ev.ports[0];
 if(!m||m.type!=='connect'||m.protocol!==1||!C.channel_id||m.channel_id!==C.channel_id||m.qid!==C.qid||!port)return;
 sent=true;const b=atob(el.textContent.trim()),u=new Uint8Array(b.length);for(let i=0;i<b.length;i++)u[i]=b.charCodeAt(i);
 port.postMessage({type:'voice',protocol:1,channel_id:C.channel_id,qid:C.qid,mime:el.dataset.mime,sha256:el.dataset.sha256,data:u.buffer},[u.buffer]);
});
})();"""


def ogg_opus_duration_ms(data: bytes) -> int:
    """Real length of an Ogg Opus stream: last page granule position minus pre-skip, at 48 kHz."""
    head = data.find(b"OpusHead")
    if head < 0 or len(data) < head + 12: raise ValueError("voice_not_ogg_opus")
    pre_skip = int.from_bytes(data[head + 10:head + 12], "little")
    last = data.rfind(b"OggS")
    if last < 0 or len(data) < last + 14: raise ValueError("voice_not_ogg_opus")
    granule = int.from_bytes(data[last + 6:last + 14], "little", signed=True)
    if granule <= pre_skip: raise ValueError("voice_empty")
    return round((granule - pre_skip) / 48)


def validate_voice(data: bytes, track: dict, duration_ms: int) -> dict:
    """Check one card's voice file and timing; returns the manifest `voice` block (without path)."""
    if not isinstance(data, (bytes, bytearray)) or not data: raise ValueError("voice_missing_bytes")
    if len(data) > MAX_VOICE_BYTES: raise ValueError("voice_too_large")
    if data[:4] != b"OggS" or b"OpusHead" not in data[:200]: raise ValueError("voice_not_ogg_opus")
    if not isinstance(track, dict): raise ValueError("voice_track_invalid")
    track_ms = track.get("track_ms")
    if not isinstance(track_ms, int) or isinstance(track_ms, bool) or not 0 < track_ms <= duration_ms:
        raise ValueError("voice_track_longer_than_card")
    real_ms = ogg_opus_duration_ms(bytes(data))
    if real_ms > duration_ms or abs(real_ms - track_ms) > 120: raise ValueError("voice_track_length_mismatch")
    cues = track.get("cues")
    if not isinstance(cues, list) or not 1 <= len(cues) <= MAX_VOICE_CUES: raise ValueError("voice_cues_invalid")
    out, last = [], -1
    for c in cues:
        if not isinstance(c, dict): raise ValueError("voice_cue_invalid")
        t, e, text = c.get("t_ms"), c.get("end_ms"), c.get("text")
        if not all(isinstance(x, int) and not isinstance(x, bool) for x in (t, e)) or not last < t <= e <= duration_ms:
            raise ValueError("voice_cue_timing_invalid")
        if not isinstance(text, str) or not text.strip() or len(text) > 200: raise ValueError("voice_cue_text_invalid")
        out.append({"t_ms": t, "end_ms": e, "text": text}); last = t
    return {"mime": VOICE_MIME, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "track_ms": track_ms, "cues": out}


def embed_voice(html: str, data: bytes) -> str:
    """Append the voice and its hand-over script to a compiled v2 entry (deterministic)."""
    tail = "</body></html>"
    if not html.endswith(tail): raise ValueError("voice_embed_entry_unexpected")
    sha = hashlib.sha256(data).hexdigest()
    block = ('<script type="application/octet-stream" id="kafu-voice" data-mime="' + VOICE_MIME + '" data-sha256="' + sha + '">'
             + base64.b64encode(bytes(data)).decode("ascii") + "</script>\n<script>" + VOICE_JS + "</script>")
    return html[:-len(tail)] + block + tail
