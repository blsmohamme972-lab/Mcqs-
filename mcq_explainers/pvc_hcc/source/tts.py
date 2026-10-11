# usage: python3 tts.py voice "text" out.mp3 out.vtt
import sys, asyncio, certifi, aiohttp
certifi.where = lambda: '/root/.ccr/ca-bundle.crt'
_orig = aiohttp.ClientSession.__init__
def _init(self, *a, **k): k['trust_env'] = True; _orig(self, *a, **k)
aiohttp.ClientSession.__init__ = _init
import edge_tts
voice, text, out, vtt = sys.argv[1:5]
async def main():
    c = edge_tts.Communicate(text, voice, rate='+0%', boundary='SentenceBoundary')
    sub = edge_tts.SubMaker()
    with open(out, 'wb') as f:
        async for ch in c.stream():
            if ch['type'] == 'audio': f.write(ch['data'])
            elif ch['type'] in ('WordBoundary', 'SentenceBoundary'): sub.feed(ch)
    open(vtt, 'w').write(sub.get_srt())
asyncio.run(main())
