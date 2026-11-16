#!/usr/bin/env python3
"""Record the voices for the bonus track's wormhole with ElevenLabs.

Each talking machine gets a one-off voice made with Voice Design (the preview audio is
used directly, so nothing is saved to your voice library), then an era-appropriate sound
treatment with ffmpeg. The narrator uses the album's Wildlife Narrator voice.

  ELEVENLABS_API_KEY=...  python3 tools/wormhole_voices.py --cache /tmp/wormhole
  python3 tools/wormhole_voices.py --dry-run        # list lines and character count
  python3 tools/wormhole_voices.py --only radio     # redo one machine
  python3 tools/wormhole_voices.py --pick radio 2   # use preview 2 instead of the default pick

Writes ../bonus/audio/<key>.mp3. Raw previews stay in --cache (not published).
"""
import argparse, base64, json, os, shutil, sys, time, urllib.error, urllib.request
import subprocess  # nosec B404: only runs ffmpeg/ffprobe with argument lists, never a shell

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "bonus", "audio")
API = "https://api.elevenlabs.io/v1"
FFMPEG, FFPROBE = shutil.which("ffmpeg"), shutil.which("ffprobe")   # absolute paths
NARRATOR = "roJPMmP5mjyGkZmeuQgA"   # Wildlife Narrator (Voice Is the OS), an original designed voice

# Voice descriptions are generic archetypes: no real person is imitated.
MACHINES = [
    {"key": "phonograph", "voice": "An excitable old-timey carnival barker from the 1890s, a nasal, theatrical man who speaks fast with rolling showman enthusiasm, recorded on a scratchy wax cylinder.",
     "text": "Step right up, step right up! Free merchandise, ladies and gentlemen, just around the corner! Why, this line can't be more than a dozen souls long!",
     "fx": "highpass=f=450,lowpass=f=2800,acrusher=bits=9:mix=0.25,volume=1.6", "noise": ("brown", 0.035)},
    {"key": "telephone", "voice": "A polite, slightly flustered young woman working as a 1910s telephone switchboard operator, crisp old-fashioned diction, heard through a thin, tinny early telephone line.",
     "text": "Hello, operator? Yes, I'm trying to reach the front of the merchandise line. No, I can't see it from here. Could you tell me where it actually ends?",
     "fx": "highpass=f=380,lowpass=f=3000,acrusher=bits=11:mix=0.2,volume=1.5", "noise": ("white", 0.006)},
    {"key": "radio", "voice": "A booming, urgent 1940s radio news announcer, a middle-aged man with dramatic, fast-paced delivery and big vintage broadcast energy, warm AM radio sound.",
     "text": "This just in from Lincoln Center! The merchandise line now wraps around the entire floor of David Geffen Hall. Witnesses report no end in sight!",
     "fx": "highpass=f=220,lowpass=f=4300,volume=1.3", "noise": ("pink", 0.012)},
    {"key": "transistor", "voice": "A smooth, upbeat 1960s AM radio disc jockey, a friendly baritone man, laid-back and reassuring, with a smile in his voice.",
     "text": "Stay tuned, folks, it's moving! Well, it moved a little. Keep that chin up and hold your place in line, because those booths are just around the bend.",
     "fx": "highpass=f=280,lowpass=f=5200,equalizer=f=1800:t=q:w=1:g=4", "noise": None},
    {"key": "walkman", "voice": "A bored, deadpan man in his twenties in the 1980s, flat and slightly sarcastic, speaking slowly with long, heavy sighs.",
     "text": "Okay, that's side A. Flipping the tape. Still in line. Still staring at the same wall. Pretty sure I've memorized every inch of it by now.",
     "fx": "lowpass=f=8000,vibrato=f=0.7:d=0.04", "noise": ("white", 0.004)},
    {"key": "answering", "voice": "A cheerful but slightly weary woman recording a 1990s home answering machine greeting, friendly and a little rehearsed.",
     "text": "Hi, you've reached us! We can't make it to the next session right now, because we're still in the merch line. Please leave a message after the beep.",
     "fx": "highpass=f=320,lowpass=f=3500,acrusher=bits=12:mix=0.15,volume=1.4", "noise": ("white", 0.005), "beep": True},
    {"key": "ipod", "voice": "A dreamy, mellow young adult from the 2000s, soft and spacey, drifting and a little lost in thought, gentle and relaxed.",
     "text": "Shuffle's been going for who knows how long. Is it still morning? Did we miss a session? Honestly, I've lost track of why we're even standing here.",
     "fx": "aecho=0.85:0.6:45:0.12", "noise": None},
    {"key": "phone", "voice": "An excited young woman whispering a voice memo into her smartphone, breathless and hopeful, very close to the microphone.",
     "text": "Wait, wait, we're finally at the corner. I can see the end of the wall, and I think those are the booths! Why is everyone wearing headphones?",
     "fx": "highpass=f=140", "noise": None},
    {"key": "agent", "voice": "A polished, warm and friendly AI voice assistant, clear and natural with perfect diction, upbeat and helpful, modern high-fidelity studio quality.",
     "text": "Hi there! Great pick. Before I can hand that over, I just need you to answer three quick questions. First one: what is A S R?",
     "fx": None, "noise": None},
]
NARRATION = [
    {"key": "narrator-in", "text": "Two people walk into a summit about making technology effortless. They join a line for free merch. They're about to fall through a century of talking machines."},
    {"key": "narrator-out", "text": "Every machine in this tunnel was built to make talking easier. The newest one did. It also made an hour-long line. Friction doesn't disappear. It moves."},
]


def key():
    # In the Claude Code cloud sandbox the proxy injects the real key; elsewhere set ELEVENLABS_API_KEY.
    return os.environ.get("ELEVENLABS_API_KEY", "proxy-injected")


def call(method, url, body=None, accept="application/json"):
    if not url.startswith(API + "/"):
        raise SystemExit(f"refusing to open a non-ElevenLabs URL: {url}")
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(5):
        req = urllib.request.Request(url, data=data, method=method, headers={
            "xi-api-key": key(), "Content-Type": "application/json", "Accept": accept})
        try:
            # The URL is pinned to https://api.elevenlabs.io by the check above.
            with urllib.request.urlopen(req, timeout=180) as r:  # nosec B310
                return r.read()
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:400]
            if e.code in (429, 500, 502, 503) and attempt < 4:
                time.sleep(2 ** attempt * 2); continue
            raise SystemExit(f"HTTP {e.code} from {url}: {msg}")


def probe(path):
    out = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout.strip()  # nosec B603: fixed args, local file
    return float(out or 0)


def treat(src, dst, m):
    """Era sound: filters, optional noise bed, optional answering-machine beep, then loudness-normalise."""
    chain = (m.get("fx") + "," if m.get("fx") else "") + "aformat=channel_layouts=mono"
    graph = f"[0:a]{chain}[v]"
    inputs, last = ["-i", src], "[v]"
    if m.get("noise"):
        color, amp = m["noise"]
        inputs += ["-f", "lavfi", "-i", f"anoisesrc=c={color}:a={amp}:r=44100"]
        graph += f";[1:a]aformat=channel_layouts=mono[n];{last}[n]amix=inputs=2:duration=first:normalize=0[m]"
        last = "[m]"
    if m.get("beep"):
        k = inputs.count("-i")
        inputs += ["-f", "lavfi", "-i", "sine=f=1000:d=0.45:r=44100"]
        graph += f";[{k}:a]volume=0.35,aformat=channel_layouts=mono,adelay=250[b];{last}[b]concat=n=2:v=0:a=1[c]"
        last = "[c]"
    graph += f";{last}loudnorm=I=-17:TP=-1.5:LRA=11[out]"
    # nosec B603: argument list (no shell); filters come from the MACHINES table above, paths are local
    subprocess.run([FFMPEG, "-y", "-v", "error", *inputs, "-filter_complex", graph, "-map", "[out]",  # nosec B603
                    "-ar", "44100", "-ac", "1", "-b:a", "80k", "-map_metadata", "-1", dst], check=True)


def design(m, cache):
    body = {"voice_description": m["voice"], "text": m["text"], "model_id": "eleven_ttv_v3"}
    try:
        res = json.loads(call("POST", f"{API}/text-to-voice/design", body))
    except SystemExit as e:
        print("  v3 design failed, retrying with the default model:", e)
        body.pop("model_id")
        res = json.loads(call("POST", f"{API}/text-to-voice/design", body))
    files = []
    for k, pv in enumerate(res.get("previews", []), 1):
        fn = os.path.join(cache, f"{m['key']}-{k}.mp3")
        open(fn, "wb").write(base64.b64decode(pv["audio_base_64"]))
        files.append(fn)
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=os.path.join(HERE, ".wormhole-cache"))
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--pick", nargs=2, metavar=("KEY", "N"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    items = MACHINES + NARRATION
    if a.dry_run:
        for m in items: print(m["key"], len(m["text"]), "|", m["text"])
        print(sum(len(m["text"]) for m in items), "characters"); return
    if not (FFMPEG and FFPROBE):
        raise SystemExit("ffmpeg and ffprobe are required (https://ffmpeg.org)")
    os.makedirs(a.cache, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    report = {}
    for m in MACHINES:
        if a.only and m["key"] not in a.only: continue
        if a.pick and a.pick[0] == m["key"]:
            files = sorted(f for f in os.listdir(a.cache) if f.startswith(m["key"] + "-"))
            choice = os.path.join(a.cache, f"{m['key']}-{a.pick[1]}.mp3")
        else:
            print("designing", m["key"])
            files = design(m, a.cache)
            durs = sorted((probe(f), f) for f in files)
            choice = durs[len(durs) // 2][1]          # the median-length take: skips rushed or stretched reads
        treat(choice, os.path.join(OUT, m["key"] + ".mp3"), m)
        report[m["key"]] = {"take": os.path.basename(choice), "sec": round(probe(os.path.join(OUT, m["key"] + ".mp3")), 2)}
    for m in NARRATION:
        if a.only and m["key"] not in a.only: continue
        print("narrating", m["key"])
        raw = os.path.join(a.cache, m["key"] + ".mp3")
        open(raw, "wb").write(call("POST", f"{API}/text-to-speech/{NARRATOR}?output_format=mp3_44100_128",
                                   {"text": m["text"], "model_id": "eleven_v4"}, accept="audio/mpeg"))
        treat(raw, os.path.join(OUT, m["key"] + ".mp3"), {"fx": "aecho=0.8:0.55:60:0.1"})
        report[m["key"]] = {"sec": round(probe(os.path.join(OUT, m["key"] + ".mp3")), 2)}
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    sys.exit(main())
