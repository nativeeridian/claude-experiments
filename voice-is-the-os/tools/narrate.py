#!/usr/bin/env python3
"""Pre-record the page narration with ElevenLabs.

Reads ../index.html, extracts every narrated line in the same order and with the
same ids the page uses (track intro = "<track>-0", then each [data-say] element
"<track>-1", "<track>-2", ...), and writes ../audio/<id>.mp3 plus
../audio/manifest.json. Lines whose text hasn't changed are skipped.

  ELEVENLABS_API_KEY=...  python3 tools/narrate.py --key chris --name Chris --note "Down-to-earth" --narrator VOICE_ID
  python3 tools/narrate.py --design OUT_DIR "voice description"   # Voice Design previews
  python3 tools/narrate.py --save-designed GENERATED_ID "Name" "description"
  python3 tools/narrate.py --dry-run            # list lines and character count
  python3 tools/narrate.py --list-voices        # voices on your account
  python3 tools/narrate.py --list-models
  python3 tools/narrate.py --samples OUT_DIR VOICE_ID [VOICE_ID ...]
"""
import argparse, hashlib, json, os, re, sys, time, urllib.error, urllib.request
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
API = "https://api.elevenlabs.io/v1"
FMT = "mp3_44100_64"           # 64 kbps: small files, clear speech
KBPS = 64
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class Node:
    def __init__(self, tag, attrs, parent):
        self.tag, self.a, self.c, self.p = tag, dict(attrs), [], parent


class Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", [], None)
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, self.cur)
        self.cur.c.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        self.cur.c.append(Node(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        x = self.cur
        while x is not self.root and x.tag != tag:
            x = x.p
        if x is not self.root:
            self.cur = x.p

    def handle_data(self, d):
        self.cur.c.append(d)


def walk(n):
    yield n
    for ch in n.c:
        if isinstance(ch, Node):
            yield from walk(ch)


def text_of(n, skip=()):
    out = []
    def rec(x):
        for ch in x.c:
            if isinstance(ch, str):
                out.append(ch)
            elif ch.tag not in skip:
                out.append(" "); rec(ch); out.append(" ")
    rec(n)
    t = re.sub(r"\s+", " ", "".join(out)).strip()
    return re.sub(r"\s+([.,;:!?)’”])", r"\1", t)


def extract(path):
    b = Builder()
    b.feed(open(path, encoding="utf-8").read())
    lines = []
    for t in [n for n in walk(b.root) if "data-track" in n.a]:
        tid = t.a.get("id")
        if tid == "liner":
            break
        if t.a.get("data-intro"):
            lines.append({"id": f"{tid}-0", "parts": [("narrator", t.a["data-intro"])]})
        says = [n for n in walk(t) if n is not t and "data-say" in n.a]
        for j, el in enumerate(says, 1):
            if el.a.get("data-text"):
                parts = [("narrator", el.a["data-text"])]
            elif el.tag == "blockquote":
                quote = text_of(el, skip=("cite",))
                cite = next((text_of(c) for c in walk(el) if c.tag == "cite"), "")
                parts = [("quote", quote)] + ([("narrator", cite + ".")] if cite else [])
            else:
                parts = [("narrator", text_of(el))]
            lines.append({"id": f"{tid}-{j}", "parts": parts})
    return lines


def key():
    # In the Claude Code cloud sandbox the proxy injects the real key; elsewhere set ELEVENLABS_API_KEY.
    return os.environ.get("ELEVENLABS_API_KEY", "proxy-injected")


def call(method, url, body=None, accept="application/json"):
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(5):
        req = urllib.request.Request(url, data=data, method=method, headers={
            "xi-api-key": key(), "Content-Type": "application/json", "Accept": accept})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:400]
            if e.code in (429, 500, 502, 503) and attempt < 4:
                time.sleep(2 ** attempt * 2); continue
            raise SystemExit(f"HTTP {e.code} from {url}: {msg}")


def tts(text, voice, model, prev=None, nxt=None):
    body = {"text": text, "model_id": model}
    if prev: body["previous_text"] = prev[-600:]
    if nxt: body["next_text"] = nxt[:300]
    return call("POST", f"{API}/text-to-speech/{voice}?output_format={FMT}", body, accept="audio/mpeg")


def h(parts, voices, model):
    raw = json.dumps([parts, voices, model], ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--narrator"); ap.add_argument("--quote")
    ap.add_argument("--key", help="voice folder under audio/ (e.g. chris)")
    ap.add_argument("--name"); ap.add_argument("--note", default="")
    ap.add_argument("--default", action="store_true", help="make this the page's default voice")
    ap.add_argument("--design", nargs=2, metavar=("OUT_DIR", "DESCRIPTION"))
    ap.add_argument("--save-designed", nargs=3, metavar=("GENERATED_ID", "NAME", "DESCRIPTION"))
    ap.add_argument("--model", default="eleven_multilingual_v2")
    ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--force", action="store_true")
    ap.add_argument("--no-context", action="store_true", help="don't send previous/next text")
    ap.add_argument("--list-voices", action="store_true"); ap.add_argument("--list-models", action="store_true")
    ap.add_argument("--samples", nargs="+", metavar=("OUT_DIR", "VOICE_ID"))
    a = ap.parse_args()

    if a.list_voices:
        for v in json.loads(call("GET", f"{API}/voices"))["voices"]:
            lab = ", ".join(f"{k}: {val}" for k, val in (v.get("labels") or {}).items())
            print(f'{v["voice_id"]}  {v["name"]:<28} {v.get("category",""):<12} {lab}')
        return
    if a.list_models:
        for m in json.loads(call("GET", f"{API}/models")):
            print(m["model_id"], "|", m.get("name"), "| tts:", m.get("can_do_text_to_speech"))
        return

    if a.design:
        import base64
        out, desc = a.design
        os.makedirs(out, exist_ok=True)
        text = next(t for l in extract(os.path.join(ROOT, "index.html")) if l["id"] == "intro-1" for _, t in l["parts"])
        try:
            res = json.loads(call("POST", f"{API}/text-to-voice/design", {"voice_description": desc, "text": text}))
        except SystemExit as e:
            print("design endpoint failed, trying create-previews:", e)
            res = json.loads(call("POST", f"{API}/text-to-voice/create-previews", {"voice_description": desc, "text": text}))
        for k, pv in enumerate(res.get("previews", []), 1):
            fn = os.path.join(out, f"preview-{k}-{pv['generated_voice_id']}.mp3")
            open(fn, "wb").write(base64.b64decode(pv["audio_base_64"]))
            print("wrote", fn)
        return
    if a.save_designed:
        gid, name, desc = a.save_designed
        v = json.loads(call("POST", f"{API}/text-to-voice", {"voice_name": name, "voice_description": desc, "generated_voice_id": gid}))
        print("saved voice", v.get("voice_id"), name)
        return

    lines = extract(os.path.join(ROOT, "index.html"))
    chars = sum(len(t) for l in lines for _, t in l["parts"])
    if a.dry_run:
        for l in lines:
            print(l["id"], "|", " + ".join(f"[{v}] {t[:70]}" for v, t in l["parts"]))
        print(f"\n{len(lines)} lines, {chars} characters")
        return
    if a.samples:
        out, ids = a.samples[0], a.samples[1:]
        os.makedirs(out, exist_ok=True)
        text = next(t for l in lines if l["id"] == "intro-1" for _, t in l["parts"])
        for vid in ids:
            open(os.path.join(out, f"sample-{vid}.mp3"), "wb").write(tts(text, vid, a.model))
            print("wrote sample", vid)
        return

    if not (a.narrator and a.key):
        sys.exit("--key and --narrator are required")
    voices = {"narrator": a.narrator, "quote": a.quote or a.narrator}
    adir = os.path.join(ROOT, "audio", a.key); os.makedirs(adir, exist_ok=True)
    mpath = os.path.join(adir, "manifest.json")
    old = json.load(open(mpath)) if os.path.exists(mpath) else {"lines": {}}
    man = {"model": a.model, "voices": voices, "format": FMT, "lines": {}}
    flat = [t for l in lines for v, t in l["parts"] if v == "narrator"]
    done = 0
    for i, l in enumerate(lines):
        hh = h(l["parts"], voices, a.model)
        f = l["id"] + ".mp3"; fp = os.path.join(adir, f)
        prev = old["lines"].get(l["id"])
        if not a.force and prev and prev.get("h") == hh and os.path.exists(fp):
            man["lines"][l["id"]] = prev; continue
        audio = b""
        for v, t in l["parts"]:
            ctx_prev = ctx_next = None
            if v == "narrator" and not a.no_context:
                k = flat.index(t) if t in flat else -1
                ctx_prev = flat[k - 1] if k > 0 else None
                ctx_next = flat[k + 1] if 0 <= k < len(flat) - 1 else None
            audio += tts(t, voices[v], a.model, ctx_prev, ctx_next)
        open(fp, "wb").write(audio)
        man["lines"][l["id"]] = {"file": f, "h": hh, "sec": round(len(audio) * 8 / (KBPS * 1000), 2)}
        done += 1
        print(f"[{i+1}/{len(lines)}] {l['id']}  {man['lines'][l['id']]['sec']}s")
    man["v"] = hashlib.sha256(json.dumps(man["lines"], sort_keys=True).encode()).hexdigest()[:8]
    json.dump(man, open(mpath, "w"), indent=1)
    for stale in set(os.listdir(adir)) - {x["file"] for x in man["lines"].values()} - {"manifest.json"}:
        os.remove(os.path.join(adir, stale))
    vpath = os.path.join(ROOT, "audio", "voices.json")
    reg = json.load(open(vpath)) if os.path.exists(vpath) else {"default": a.key, "voices": []}
    entry = {"key": a.key, "name": a.name or a.key.title(), "note": a.note}
    reg["voices"] = [entry if v["key"] == a.key else v for v in reg["voices"]]
    if not any(v["key"] == a.key for v in reg["voices"]): reg["voices"].append(entry)
    if a.default or not reg.get("default"): reg["default"] = a.key
    json.dump(reg, open(vpath, "w"), indent=1)
    total = sum(x["sec"] for x in man["lines"].values())
    print(f"generated {done}, total {len(man['lines'])} lines, {total/60:.1f} min")


if __name__ == "__main__":
    main()
