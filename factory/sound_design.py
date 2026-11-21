"""Event-driven sound design and mastering (quality overhaul, brief section 8).

Every sound is synthesised here (no third-party samples, no licensing risk) and placed from
simulation or timeline events, with parameters taken from the physics where possible:

  latch      gripper release: two-stage metallic click plus a short tension "tick"
  coil       one coil-to-coil contact; pitch and level follow the stack size and impact speed
  impact     a body landing; level and brightness scale with speed, with a metallic rattle decay
  tink       a struck steel bar (free-free bar mode ratios 1 : 2.756 : 5.404)
  swish      soft air transition (used sparingly, only on a few cuts)
  rewind     reverse tape-like sweep
  rise       gentle filtered swell into a reveal
  ding       end chime

The music bed is an original procedural composition (soft pad, plucked arpeggio, sub bass, light
shaker) that ducks under the voice and drops out during "suspension" windows so the hover reads.
Master: voice EQ and compression, music sidechain ducking, loudness normalised with ffmpeg
(two-pass loudnorm) to about -15 LUFS integrated and -1.5 dBTP true peak, limited to -3.1 dBFS sample peak because AAC encoding adds up to ~1.7 dB of inter-sample overshoot (QA blocks above -0.3 dBTP).
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

SR = 48000


def _t(n):
    return np.arange(n) / SR


def _env(n, a, d):
    t = _t(n)
    return np.clip(t / max(a, 1e-4), 0, 1) * np.exp(-np.maximum(t - a, 0) / d)


def _bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def _lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, btype="low", fs=SR, output="sos"), x)


def _hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, btype="high", fs=SR, output="sos"), x)


def _norm(y, peak=1.0):
    m = float(np.max(np.abs(y))) or 1.0
    return (y / m * peak).astype(np.float32)


def _modes(freqs, amps, decays, dur, rng=None, detune=0.0):
    n = int(dur * SR); t = _t(n); y = np.zeros(n)
    for f, a, d in zip(freqs, amps, decays):
        f2 = f * (1 + (rng.uniform(-detune, detune) if rng is not None else 0))
        y += a * np.sin(2 * np.pi * f2 * t + (rng.uniform(0, 6.28) if rng is not None else 0)) * np.exp(-t / d)
    return y


# ------------------------------------------------------------------ one-shots
def latch(seed=1):
    rng = np.random.default_rng(seed)
    n = int(0.25 * SR)
    y = np.zeros(n)
    for k, (t0, g) in enumerate([(0.0, 0.7), (0.018, 1.0)]):          # pawl, then jaw release
        i = int(t0 * SR); m = int(0.05 * SR)
        click = _bp(rng.standard_normal(m), 2500, 9000) * _env(m, 0.0003, 0.004)
        ring = _modes([3150, 4870, 7300], [0.5, 0.35, 0.2], [0.03, 0.02, 0.012], 0.05, rng, 0.02)
        y[i:i + m] += g * (click + 0.4 * ring)
    body = _modes([620, 1240], [0.25, 0.1], [0.04, 0.02], 0.25)          # small mechanism body
    y += body * _env(len(body), 0.001, 0.05)
    return _norm(y, 0.9)


def coil(stack_frac=0.0, speed=1.0, seed=0):
    """One coil landing on the stack. Bigger stack = slightly lower, duller; faster = brighter, louder."""
    rng = np.random.default_rng(seed)
    base = 5200 - 2200 * stack_frac
    y = _modes([base, base * 1.53, base * 2.31], [0.6, 0.35, 0.2], [0.012, 0.008, 0.005], 0.04, rng, 0.04)
    y += 0.5 * _bp(rng.standard_normal(len(y)), 3000, 10000) * _env(len(y), 0.0002, 0.003)
    return (y * (0.25 + 0.75 * min(1.0, speed))).astype(np.float32)


def impact(speed=2.5, seed=3, slow=1.0):
    """Body landing on stone. Level/brightness scale with speed; slow motion stretches the decay."""
    rng = np.random.default_rng(seed)
    s = min(1.0, speed / 4.0)
    dur = 0.9 * min(3.0, slow ** 0.35)
    n = int(dur * SR); t = _t(n)
    thump = np.sin(2 * np.pi * (95 + 40 * s) * t * (1 - 0.15 * t)) * np.exp(-t / (0.07 * min(2.5, slow ** 0.3)))
    crack = _lp(rng.standard_normal(n), 1800 + 3000 * s) * _env(n, 0.0005, 0.012)
    rattle = np.zeros(n)
    for k in range(14):                                                    # coils settling, metallic
        i = int(rng.uniform(0.01, 0.35 * min(2, slow ** 0.3)) * SR)
        c = coil(rng.uniform(0.5, 1.0), rng.uniform(0.2, 0.6), seed=seed * 31 + k)
        j = min(n, i + len(c)); rattle[i:j] += c[: j - i] * np.exp(-i / SR / 0.25)
    y = 0.9 * thump + 0.35 * crack * s + 0.45 * rattle
    return _norm(y, 0.55 + 0.4 * s)


def tink(seed=5, pitch=1.0, ring=1.0):
    """Small metal tink. Vary `seed`/`pitch` between uses: one identical bell sample repeated over and
    over is the most annoying sound we have made (chain fountain, 2026-11-19)."""
    rng = np.random.default_rng(seed)
    f0 = 1180 * pitch
    y = _modes([f0, f0 * 2.756, f0 * 5.404, f0 * 8.933], [1.0, 0.55, 0.3, 0.12],
               [0.9 * ring, 0.5 * ring, 0.25 * ring, 0.12 * ring], 1.4 * max(0.2, ring), rng, 0.002)
    m = int(0.004 * SR); y[:m] += _hp(rng.standard_normal(m), 4000) * 0.6
    return _norm(y, 0.7)


def swish(seed=7, dur=0.55):
    rng = np.random.default_rng(seed)
    n = int(dur * SR); x = rng.standard_normal(n)
    y = np.zeros(n)
    for k, fc in enumerate(np.linspace(600, 2600, 8)):
        seg = slice(k * n // 8, (k + 1) * n // 8)
        y[seg] = _bp(x, fc * 0.7, fc * 1.4)[seg]
    return _norm(y * np.sin(np.linspace(0, np.pi, n)) ** 2, 0.5)


def rewind(seed=9, dur=1.0):
    rng = np.random.default_rng(seed)
    n = int(dur * SR); t = _t(n)
    f = 300 + 2600 * (t / dur) ** 2
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.25
    hiss = _bp(rng.standard_normal(n), 1500, 6000) * 0.4
    flutter = 1 + 0.3 * np.sin(2 * np.pi * 23 * t)
    return _norm((tone + hiss) * flutter * np.sin(np.linspace(0, np.pi, n)) ** 1.5, 0.45)


def rise(dur=1.6, seed=11):
    rng = np.random.default_rng(seed)
    n = int(dur * SR); t = _t(n); x = rng.standard_normal(n)
    y = np.zeros(n)
    for k in range(10):
        seg = slice(k * n // 10, (k + 1) * n // 10)
        fc = 400 * 2 ** (k * 0.35)
        y[seg] = _bp(x, fc * 0.8, fc * 1.25)[seg]
    y += 0.3 * np.sin(2 * np.pi * (220 + 220 * t / dur) * t)
    return _norm(y * (t / dur) ** 2.2, 0.35)


def ding():
    y = _modes([1318.5, 2637, 3955], [1.0, 0.35, 0.12], [0.6, 0.3, 0.15], 1.4)
    return _norm(y, 0.45)


def blip(seed=13, pitch=1.0):
    """Soft UI blip for a HUD number update: a short, rounded sine pair, no metallic ring.
    `pitch` follows the value (a rising counter is heard rising); `seed` varies each instance slightly."""
    rng = np.random.default_rng(seed)
    n = int(0.07 * SR); t = _t(n)
    f = 880 * pitch * (1 + rng.uniform(-0.015, 0.015))
    y = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t)) * _env(n, 0.002, 0.018)
    return _norm(_lp(y, 6000), 0.5)


def lock(seed=17, pitch=1.0):
    """A value landing on its target: low soft thump plus a short two-note confirmation (no bell tail)."""
    rng = np.random.default_rng(seed)
    n = int(0.32 * SR); t = _t(n)
    thump = np.sin(2 * np.pi * (90 * pitch) * t * (1 + 0.6 * np.exp(-t / 0.02))) * _env(n, 0.002, 0.07)
    y = 0.8 * thump
    for k, (t0, f) in enumerate([(0.0, 660), (0.06, 990)]):
        i = int(t0 * SR); m = int(0.12 * SR); tt = _t(m)
        y[i:i + m] += 0.35 * np.sin(2 * np.pi * f * pitch * (1 + rng.uniform(-0.01, 0.01)) * tt) * _env(m, 0.003, 0.035)
    return _norm(_lp(y, 7000), 0.8)


def bark(seed=19, distant=1.0):
    """A distant dog's 'woof-woof' heard from indoors: two short voiced bursts (a falling ~420 Hz
    fundamental with harmonics through a mouth-like formant) plus breath noise, low-passed and with a
    touch of room tail so it sits outside the window, not in the room."""
    rng = np.random.default_rng(seed)
    out = np.zeros(int(0.9 * SR))
    for k, (t0, f0) in enumerate([(0.0, 430.0), (0.27, 400.0)]):
        n = int(0.17 * SR); t = _t(n)
        f = f0 * (1.25 - 0.45 * t / 0.17) * (1 + rng.uniform(-0.03, 0.03))
        ph = 2 * np.pi * np.cumsum(f) / SR
        v = sum((0.9 ** h) * np.sin((h + 1) * ph) for h in range(8))
        v = _bp(v, 500, 1900) + 0.25 * _bp(rng.standard_normal(n), 700, 2500)
        env = np.clip(t / 0.012, 0, 1) * np.exp(-np.maximum(t - 0.03, 0) / 0.05)
        i = int(t0 * SR); out[i:i + n] += v * env
    out = _lp(out, 2600 / max(distant, 0.5))
    tail = signal.lfilter([1.0], [1, -0.0], out) * 0.0
    for d, g in ((0.031, 0.35), (0.057, 0.22), (0.089, 0.14)):           # small early reflections
        j = int(d * SR); tail[j:] += g * out[:-j]
    return _norm(out + tail, 0.7)


ONE_SHOTS = {"bark": bark, "blip": blip, "lock": lock, "latch": latch, "pop": latch, "impact": impact, "thud": impact, "tink": tink, "tick": tink,
             "swish": swish, "whoosh": rewind, "rewind": rewind, "rise": rise, "ding": ding}


# ------------------------------------------------------------------ music bed
NOTE = {n: i for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}


def _hz(name, octave):
    return 440.0 * 2 ** ((NOTE[name] + 12 * (octave - 4) - 9) / 12)


def _pluck(f, dur, seed):
    """Karplus-Strong plucked string: warm, light, mobile-speaker friendly."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR); p = max(2, int(SR / f))
    buf = rng.uniform(-1, 1, p); y = np.zeros(n)
    for i in range(n):
        y[i] = buf[i % p]
        buf[i % p] = 0.5 * (buf[i % p] + buf[(i + 1) % p]) * 0.996
    return _lp(y, 3500) * _env(n, 0.002, dur * 0.5)


def music_bed(duration: float, mutes: list[tuple[float, float]] = (), bpm: float = 96, seed: int = 21,
              swell_at: list[float] = ()) -> np.ndarray:
    """Original procedural underscore (stereo). `mutes`: windows where only a soft pad remains."""
    rng = np.random.default_rng(seed)
    n = int((duration + 1) * SR)
    L = np.zeros(n); Rr = np.zeros(n)
    beat = 60 / bpm; bar = 4 * beat
    prog = [("A", ["A", "C", "E", "G"]), ("F", ["F", "A", "C", "E"]), ("C", ["C", "E", "G", "B"]), ("G", ["G", "B", "D", "E"])]
    # pad: detuned saw stack, low-passed, slow attack, one chord per two bars
    n_chords = int(duration / (2 * bar)) + 2
    for c in range(n_chords):
        root, tones = prog[c % 4]
        t0 = c * 2 * bar; m = int(2 * bar * SR) + int(0.6 * SR)
        i = int(t0 * SR)
        if i >= n:
            break
        t = _t(m); pad = np.zeros(m)
        for k, tn in enumerate(tones):
            f = _hz(tn, 3 if k == 0 else 4)
            for dt in (-0.004, 0.004):
                pad += signal.sawtooth(2 * np.pi * f * (1 + dt) * t) * 0.12
        pad = _lp(pad, 1100) * np.clip(t / 0.6, 0, 1) * np.clip((m / SR - t) / 0.6, 0, 1)
        j = min(n, i + m); L[i:j] += pad[: j - i] * 0.55; Rr[i:j] += pad[: j - i] * 0.55
        # sub bass on beats 1 and 3
        for b in (0, 2, 4, 6):
            bi = i + int(b * beat * SR); bm = int(beat * 1.6 * SR)
            if bi >= n:
                continue
            tb = _t(bm); sub = np.sin(2 * np.pi * _hz(root, 2) * tb) * _env(bm, 0.01, 0.35) * 0.5
            bj = min(n, bi + bm); L[bi:bj] += sub[: bj - bi]; Rr[bi:bj] += sub[: bj - bi]
        # arpeggio: eighth notes, panned gently left/right
        arp = [tones[0], tones[1], tones[2], tones[3], tones[2], tones[1], tones[2], tones[3]]
        for e in range(16):
            ei = i + int(e * beat / 2 * SR)
            if ei >= n:
                continue
            f = _hz(arp[e % 8], 5 if e % 8 in (3, 7) else 4)
            pl = _pluck(f, beat * 1.5, seed + c * 16 + e) * 0.16
            ej = min(n, ei + len(pl)); pan = 0.5 + 0.25 * np.sin(e * 0.9)
            L[ei:ej] += pl[: ej - ei] * (1 - pan) * 2 * 0.5; Rr[ei:ej] += pl[: ej - ei] * pan * 2 * 0.5
        # shaker on 16ths after the first 8 bars
        if t0 >= 8 * beat:
            for s in range(32):
                si = i + int(s * beat / 4 * SR); sm = int(0.05 * SR)
                if si + sm >= n:
                    continue
                sh = _hp(rng.standard_normal(sm), 7000) * _env(sm, 0.001, 0.012) * (0.05 if s % 2 else 0.028)
                L[si:si + sm] += sh * 0.8; Rr[si:si + sm] += sh
    # suspension windows: drop arpeggio/bass/shaker, keep a quiet pad (crossfaded)
    g = np.ones(n)
    tt = _t(n)
    for a, b in mutes:
        fade = np.clip(np.minimum((tt - a) / 0.25, (b - tt) / 0.4), 0, 1)
        g = np.minimum(g, 1 - 0.85 * fade)
    L *= g; Rr *= g
    for s in swell_at:
        r = rise(1.6); i = int(max(0, s - 1.6) * SR); j = min(n, i + len(r))
        L[i:j] += r[: j - i] * 0.6; Rr[i:j] += r[: j - i] * 0.6
    return np.stack([L, Rr], axis=1)[: int(duration * SR)]


# ------------------------------------------------------------------ assembly + master
def _place(buf, t, y, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= len(buf) or i < 0:
        return
    j = min(len(buf), i + len(y))
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[i:j, 0] += y[: j - i] * gain * l * 1.414
    buf[i:j, 1] += y[: j - i] * gain * r * 1.414


def _biquad(kind, f0, gain_db, q=0.9):
    """RBJ cookbook peaking / high-shelf filter coefficients."""
    A, w = 10 ** (gain_db / 40), 2 * np.pi * f0 / SR
    al, cw = np.sin(w) / (2 * q), np.cos(w)
    if kind == "peak":
        b = [1 + al * A, -2 * cw, 1 - al * A]; a = [1 + al / A, -2 * cw, 1 - al / A]
    else:   # high shelf
        sA = 2 * np.sqrt(A) * al
        b = [A * ((A + 1) + (A - 1) * cw + sA), -2 * A * ((A - 1) + (A + 1) * cw), A * ((A + 1) + (A - 1) * cw - sA)]
        a = [(A + 1) - (A - 1) * cw + sA, 2 * ((A - 1) - (A + 1) * cw), (A + 1) - (A - 1) * cw - sA]
    return np.array(b) / a[0], np.array(a) / a[0]


def _voice_chain(v):
    """Narration polish: high-pass, less mud and boxiness, presence and air, de-essing, compression."""
    v = _hp(v, 80)
    for kind, f, g, q in (("peak", 280, -2.5, 1.0), ("peak", 520, -1.2, 1.4), ("shelf", 9500, 1.5, 0.7)):
        b, a = _biquad(kind, f, g, q); v = signal.lfilter(b, a, v)
    b, a = signal.iirpeak(3200, 1.2, fs=SR)            # gentle presence lift
    v = v + 0.18 * signal.lfilter(b, a, v)
    # de-esser: duck the 5-9 kHz band when it gets loud relative to the whole voice
    s_band = _bp(v, 5000, 9000)
    es = np.sqrt(signal.lfilter([0.01], [1, -0.99], s_band * s_band) + 1e-12)
    ev = np.sqrt(signal.lfilter([0.01], [1, -0.99], v * v) + 1e-12)
    red = np.clip(1.0 - 1.8 * np.maximum(0, es / ev - 0.35), 0.5, 1.0)
    v = v - s_band * (1 - red)
    # light compression (RMS follower, 3:1 above -20 dBFS)
    env = np.sqrt(signal.lfilter([0.002], [1, -0.998], v * v) + 1e-9)
    db = 20 * np.log10(env); over = np.maximum(0, db + 20)
    return v * 10 ** (-(over * (1 - 1 / 3)) / 20)


def render_cue(name: str, p: dict, t: float) -> np.ndarray:
    """The exact samples one cue contributes (before its gain), as build_mix places them."""
    if name == "coil":
        return coil(p.get("stack", 0.0), p.get("speed", 1.0), seed=int(t * 1000) % 9973)
    fn = ONE_SHOTS.get(name)
    if fn is None:
        raise ValueError(f"unknown sound {name!r}")
    kw = {k: p[k] for k in ("speed", "slow") if k in p and name in ("impact", "thud")}
    kw.update({k: p[k] for k in ("seed",) if k in p and name in ("tink", "tick", "latch", "pop", "swish", "bark")})
    if name in ("tink", "tick"):
        kw.update({k: p[k] for k in ("pitch", "ring") if k in p})
    if name in ("blip", "lock"):
        kw.update({k: p[k] for k in ("pitch", "seed") if k in p})
    if name in ("rise", "swish") and "dur" in p:
        kw["dur"] = float(p["dur"])
    return fn(**kw)


def stems(voice_wav: Path, events: list, duration: float | None = None, music: dict | None = None,
          sfx_gain: float = 0.5) -> dict:
    """voice / sfx / music stems exactly as they are summed into the mix (factory/qa/sound.py measures
    these: repetition, density, masking of the voice, music balance)."""
    v, sr = sf.read(voice_wav, dtype="float64")
    if v.ndim > 1:
        v = v.mean(axis=1)
    if sr != SR:
        v = signal.resample_poly(v, SR, sr)
    duration = duration or len(v) / SR
    n = int(duration * SR)
    v = np.pad(v, (0, max(0, n - len(v))))[:n]
    v = _voice_chain(v)
    fx = np.zeros((n, 2))
    for ev in events:
        t, name = ev[0], ev[1]
        p = dict(ev[2]) if len(ev) > 2 and ev[2] else {}
        _place(fx, t, render_cue(name, p, t), p.get("gain", 0.35 if name == "coil" else 1.0), pan=p.get("pan", 0.0))
    fx *= sfx_gain
    bed = np.zeros((n, 2))
    if music is not False:
        mcfg = music or {}
        b = music_bed(duration, mcfg.get("mutes", []), mcfg.get("bpm", 96), swell_at=mcfg.get("swells", []))
        # sidechain ducking under the voice (fast attack, slow release)
        env = np.abs(v)
        rel = np.exp(-1 / (mcfg.get("duck_release", 0.35) * SR))
        e = signal.lfilter([1 - rel], [1, -rel], env)
        e = e / (np.percentile(e, 99) or 1)
        duck = 1 - 0.65 * np.clip(e, 0, 1)
        bed = b * (mcfg.get("gain", 0.16) * duck)[:, None]
        nf = int(1.2 * SR)                       # fade the music out over the last 1.2 s (clean loop)
        if n > nf:
            bed[-nf:] *= np.linspace(1.0, 0.0, nf)[:, None]
    return {"voice": v, "fx": fx, "bed": bed, "sr": SR, "duration": duration}


def build_mix(voice_wav: Path, events: list, out_wav: Path, duration: float | None = None,
              music: dict | None = None, sfx_gain: float = 0.5) -> dict:
    """Mix voice + designed SFX + music and master. `events`: (t, name) or (t, name, params)."""
    st = stems(voice_wav, events, duration, music, sfx_gain)
    mix = st["fx"] + st["bed"]
    mix[:, 0] += st["voice"]; mix[:, 1] += st["voice"]
    tmp = out_wav.with_suffix(".premaster.wav")
    sf.write(tmp, (mix / max(1.0, np.max(np.abs(mix)))).astype(np.float32), SR)
    stats = master(tmp, out_wav)
    tmp.unlink(missing_ok=True)
    return stats


def master(src: Path, dst: Path, I: float = -15.0, TP: float = -1.5, LRA: float = 9.0) -> dict:
    """Two-pass ffmpeg loudnorm (linear mode) to the delivery target; returns measured stats."""
    p1 = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(src), "-af",
                         f"loudnorm=I={I}:TP={TP}:LRA={LRA}:print_format=json", "-f", "null", "-"],
                        capture_output=True, text=True)
    js = json.loads(p1.stderr[p1.stderr.rindex("{"):p1.stderr.rindex("}") + 1])
    af = (f"loudnorm=I={I}:TP={TP}:LRA={LRA}:measured_I={js['input_i']}:measured_TP={js['input_tp']}:"
          f"measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-af", af + ",alimiter=limit=0.70:level=false",
                    "-ar", str(SR), "-ac", "2", str(dst)], check=True)
    return measure(dst)


def measure(path: Path) -> dict:
    p = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "loudnorm=print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    js = json.loads(p.stderr[p.stderr.rindex("{"):p.stderr.rindex("}") + 1])
    return {"lufs": float(js["input_i"]), "true_peak_db": float(js["input_tp"]), "lra": float(js["input_lra"])}
