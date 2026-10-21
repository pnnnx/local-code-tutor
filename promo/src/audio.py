"""Музыка и звуковой дизайн ролика (10 с, 120 BPM, 48 кГц стерео) — синтез в numpy, без внешних сэмплов.
Карта акцентов (секунды) совпадает с таймлайном video.html:
  0.00–2.00  напряжение: фильтрованный пад Am, тики, нарастание; 1.25 — штамп ✗ (удар + «ошибка»)
  2.00       дроп: бочка, бас, щелчок-«хлыст» (whip камеры)
  2.25–2.75  печать команды; 3.00 и 3.12 — «14» и «0» (звон успеха); 3.25 — стекло (осколки ответа «6 и 6»)
  4.50       нырок в туннель: свист + саб; 5.0 / 6.0 / 7.0 — карточки на бочке (свист-пролёт)
  7.50       карточка репо (G, ожидание) → 8.00 разрешение в C; 8.50 — «Star» (колокольчик + искры)
  9.50       финальный аккорд, хвост до 10.0
"""
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter, sosfilt

SR, DUR = 48000, 10.0
N = int(SR * DUR)
rng = np.random.default_rng(3)
t_all = np.arange(N) / SR


def buf():
    return np.zeros((N, 2))


def place(dst, sig, t0, gain=1.0, pan=0.0):
    i = int(t0 * SR)
    if i >= N:
        return
    sig = sig[: N - i]
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    dst[i:i + len(sig), 0] += sig * gain * l * 1.414
    dst[i:i + len(sig), 1] += sig * gain * r * 1.414


def env(n, a=0.002, d=0.2, s=0.0, rel=0.05, length=None):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4))
    return e * np.exp(-t / max(d, 1e-4)) * (1 - s) + s * e


def bp(x, lo, hi, order=2):
    sos = butter(order, [lo / (SR / 2), min(hi / (SR / 2), .99)], btype="band", output="sos")
    return sosfilt(sos, x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f / (SR / 2), btype="high", output="sos"), x)


def lp(x, f, order=2):
    return sosfilt(butter(order, min(f / (SR / 2), .99), btype="low", output="sos"), x)


def note(n):  # MIDI → Гц
    return 440.0 * 2 ** ((n - 69) / 12)


# ---------------------------------------------------------------- инструменты
def kick(dur=0.45):
    t = np.arange(int(dur * SR)) / SR
    f = 45 + 110 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * 7.5)
    click = hp(rng.standard_normal(len(t)), 2500) * np.exp(-t * 260) * .25
    return np.tanh((body + click) * 1.6)


def snare(dur=0.25):
    t = np.arange(int(dur * SR)) / SR
    noise = bp(rng.standard_normal(len(t)), 900, 7000) * np.exp(-t * 18)
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30) * .5
    return (noise * .8 + tone)


def hat(dur=0.05, bright=1.0):
    t = np.arange(int(dur * SR)) / SR
    return hp(rng.standard_normal(len(t)), 7000) * np.exp(-t * 90) * .35 * bright


def saw(f, t):
    return 2 * ((f * t) % 1) - 1


def pad(chord, dur, cutoff_from, cutoff_to):
    t = np.arange(int(dur * SR)) / SR
    x = np.zeros(len(t))
    for n in chord:
        for det in (-0.12, 0.0, 0.11):
            x += saw(note(n + det), t)
    x /= len(chord) * 3
    # фильтр с движущейся частотой среза — блоками
    out = np.zeros_like(x)
    blk = 1024
    zi = None
    for i in range(0, len(x), blk):
        fc = cutoff_from * (cutoff_to / cutoff_from) ** (i / len(x))
        b, a = butter(2, min(fc / (SR / 2), .99), btype="low")
        if zi is None:
            zi = np.zeros(max(len(a), len(b)) - 1)
        out[i:i + blk], zi = lfilter(b, a, x[i:i + blk], zi=zi)
    a_env = np.minimum(1, t / .25) * np.minimum(1, (dur - t) / .25)
    return out * a_env


def bass(n, dur):
    t = np.arange(int(dur * SR)) / SR
    x = np.sign(np.sin(2 * np.pi * note(n) * t)) * .6 + np.sin(2 * np.pi * note(n) * t)
    return lp(x, 700) * np.minimum(1, t / .005) * np.exp(-t * 2.2) * np.minimum(1, (dur - t) / .02)


def pluck(n, dur=0.6, bright=4000):
    t = np.arange(int(dur * SR)) / SR
    f = note(n)
    x = sum(np.sin(2 * np.pi * f * k * t) / k ** 1.3 for k in range(1, 7))
    return lp(x, bright) * np.exp(-t * 7) * np.minimum(1, t / .002)


def bell(n, dur=1.4):
    t = np.arange(int(dur * SR)) / SR
    f = note(n)
    parts = [(1, 1, 3), (2.76, .5, 5), (5.4, .25, 8), (8.9, .12, 12)]
    return sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * d) for r, a, d in parts) * np.minimum(1, t / .001)


def whoosh(dur, f0, f1, peak=0.7):
    t = np.arange(int(dur * SR)) / SR
    x = rng.standard_normal(len(t))
    out = np.zeros_like(x)
    blk = 512
    for i in range(0, len(x), blk):
        u = i / len(x)
        fc = f0 * (f1 / f0) ** u
        out[i:i + blk] = bp(x[max(0, i - 2048):i + blk], fc * .7, fc * 1.4)[-len(x[i:i + blk]):]
    shape = np.exp(-((t / dur - peak) ** 2) / .03)
    return out * shape


def shatter(dur=0.9):
    t = np.arange(int(dur * SR)) / SR
    x = hp(rng.standard_normal(len(t)), 2500) * np.exp(-t * 14) * .6
    for _ in range(26):
        t0 = rng.uniform(0, .35)
        f = rng.uniform(2800, 8500)
        i = int(t0 * SR)
        tt = t[: len(t) - i]
        x[i:] += np.sin(2 * np.pi * f * tt) * np.exp(-tt * rng.uniform(18, 40)) * rng.uniform(.08, .2)
    return x


def click(dur=0.012):
    t = np.arange(int(dur * SR)) / SR
    return bp(rng.standard_normal(len(t)), 1500, 6000) * np.exp(-t * 500) * .6


def buzz(dur=0.3):
    t = np.arange(int(dur * SR)) / SR
    x = np.sign(np.sin(2 * np.pi * 98 * t)) + np.sign(np.sin(2 * np.pi * 103.5 * t))
    return lp(x, 1800) * np.exp(-t * 7) * .35


def sub_drop(dur=0.8):
    t = np.arange(int(dur * SR)) / SR
    f = 70 * np.exp(-t * 1.6) + 30
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3)


def reverb(x, secs=1.1, mix=0.25):
    n = int(secs * SR)
    ir = rng.standard_normal((n, 2)) * np.exp(-np.arange(n) / SR * 5.5)[:, None]
    ir[:, 1] = np.roll(ir[:, 1], 211)
    ir /= np.sqrt((ir ** 2).sum(0))
    from scipy.signal import fftconvolve
    wet = np.stack([fftconvolve(x[:, c], ir[:, c])[: len(x)] for c in range(2)], 1)
    return x * (1 - mix) + wet * mix * 2.2


# ---------------------------------------------------------------- аранжировка
drums, music, fx = buf(), buf(), buf()
AM, F, C, G = [57, 60, 64], [53, 57, 60], [48, 55, 60, 64], [55, 59, 62]
# 0–2: пад Am с открывающимся фильтром + тики шестнадцатыми, тихо → громче
place(music, pad(AM + [69], 2.05, 300, 2600), 0.0, .9)
for i in range(16):
    place(drums, hat(bright=.4 + .6 * i / 16), i * .125, .55 + .5 * i / 16, pan=.3 if i % 2 else -.3)
for b in (0.0, 0.5, 1.0, 1.5):                                   # глухой пульс в интро — крючок не тихий
    place(drums, lp(kick(.4), 300), b, .55)
place(fx, whoosh(.7, 400, 6000, peak=.95), 1.3, .5)            # подсос к дропу
# штамп ✗ (1.25): удар + «ошибка»
place(fx, kick(.5), 1.25, .9)
place(fx, snare(.3), 1.25, .55)
place(fx, buzz(.32), 1.27, .5)
# 2.0 — дроп
place(fx, sub_drop(.9), 2.0, .55)
place(fx, whoosh(.25, 6000, 900, peak=.25), 1.92, .45, pan=.6)   # хлыст камеры
progression = [(2.0, AM), (3.0, F), (4.0, C), (5.0, G), (6.0, AM), (7.0, F), (7.5, G), (8.0, C)]
for k, (t0, ch) in enumerate(progression):
    end = progression[k + 1][0] if k + 1 < len(progression) else 9.5
    place(music, pad(ch, end - t0 + .1, 1800, 2400), t0, .32)
    for b in np.arange(t0, end - 1e-6, .25):                       # бас восьмыми, корень аккорда
        place(music, bass(ch[0] - 12, .24), b, .42)
    arp = ch + [ch[0] + 12]
    for j, b in enumerate(np.arange(t0, end - 1e-6, .125)):
        place(music, pluck(arp[j % len(arp)] + 12, .35, 5000), b, .11, pan=-.4 if j % 2 else .4)
for b in np.arange(2.0, 9.5, .5):                                  # бочка на долях
    if 4.40 < b < 4.60:
        continue
    place(drums, kick(), b, .9)
for b in np.arange(2.5, 9.5, 1.0):                                  # хлопок на 2 и 4
    place(drums, snare(), b, .45, pan=.1)
for b in np.arange(2.0, 9.5, .125):
    place(drums, hat(), b + (.012 if int(b * 8) % 2 else 0), .22, pan=.35 if int(b * 8) % 2 else -.35)
# печать команды 2.25–2.75
for j in range(19):
    place(fx, click(), 2.25 + j * .5 / 19 + rng.uniform(-.004, .004), .45, pan=rng.uniform(-.2, .2))
# «14» и «0»: звон успеха
place(fx, bell(76, 1.2), 3.0, .32, pan=-.15)
place(fx, bell(81, 1.2), 3.12, .26, pan=.15)
# стекло: осколки ответа «6 и 6» (3.25)
place(fx, shatter(), 3.25, .65, pan=-.35)
place(fx, kick(.3), 3.25, .35)
# нырок в туннель (4.5)
place(fx, whoosh(.6, 300, 7000, peak=.7), 4.1, .7)
place(fx, sub_drop(1.0), 4.5, .75)
place(fx, kick(.6), 4.5, .8)
place(fx, snare(.35), 4.5, .35)
# карточки пролетают (5.05, 6.05, 7.05)
for k, tc in enumerate((5.0, 6.0, 7.0)):
    place(fx, whoosh(.45, 900, 4500, peak=.75), tc - .34, .45, pan=(-.5, .5, -.5)[k])
    place(fx, pluck(88 + k * 2, .5, 9000), tc, .12, pan=(-.5, .5, -.5)[k])
# карточка репо (7.5) → разрешение (8.0) → «Star» (8.5)
place(fx, whoosh(.5, 600, 3000, peak=.6), 7.2, .4)
place(fx, bell(72, 1.5), 8.0, .22)
place(fx, bell(84, 1.6), 8.5, .3, pan=-.2)
place(fx, bell(88, 1.6), 8.56, .22, pan=.2)
for j in range(10):
    place(fx, bell(96 + (j % 3) * 2, .4), 8.52 + j * .025, .05, pan=rng.uniform(-.7, .7))
# финальный аккорд 9.5
place(music, pad(C + [72, 76], .55, 3000, 1200), 9.5, .45)
place(fx, kick(.5), 9.5, .7)
place(fx, bell(72, .6), 9.5, .25)

mix = drums * .85 + reverb(music, 1.2, .3) * 1.0 + reverb(fx, .9, .18) * 1.0
# сайдчейн: пад и бас «дышат» от бочки (после дропа)
duck = np.ones(N)
for b in np.arange(2.0, 9.5, .5):
    i = int(b * SR)
    n = int(.18 * SR)
    duck[i:i + n] = np.minimum(duck[i:i + n], .55 + .45 * np.linspace(0, 1, n))
mix = drums * .85 + reverb(music, 1.2, .3) * duck[:, None] + reverb(fx, .9, .18)
# мягкое ограничение, затухание хвоста, нормировка −1 dBFS
mix = mix / np.abs(mix).max()
mix = np.tanh(mix * 1.6) / np.tanh(1.6)            # мягкий лимитер
fade = np.ones(N)
fade[int(9.62 * SR):] = np.linspace(1, 0, N - int(9.62 * SR)) ** 1.5
fade[:int(.004 * SR)] = np.linspace(0, 1, int(.004 * SR))
mix *= fade[:, None]
mix /= np.abs(mix).max() / 10 ** (-4.5 / 20)          # −3 dBFS: запас под перекодирование AAC/TikTok
wavfile.write("audio.wav", SR, (mix * 32767).astype(np.int16))
print("peak dBFS", round(20 * np.log10(np.abs(mix).max()), 2), "rms dBFS", round(20 * np.log10(np.sqrt((mix ** 2).mean())), 1))
