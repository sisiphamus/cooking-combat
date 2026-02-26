"""
sound.py - Audio generation and playback module for Cooking Combat.

All sound effects and music are generated procedurally using math and the
array module. No external audio files are required.

Mixer is initialized at 22050 Hz, 16-bit signed mono (single channel).
All Sound objects are created from array.array('h', ...) buffers.
"""

import pygame
import math
import array
import random

try:
    from config import SAMPLE_RATE
except ImportError:
    SAMPLE_RATE = 22050

# ---------------------------------------------------------------------------
# Musical note frequency constants (Hz)
# ---------------------------------------------------------------------------

# Octave 3 (full chromatic set)
C3  = 130.81
Db3 = 138.59
D3  = 146.83
Eb3 = 155.56
E3  = 164.81
F3  = 174.61
Gb3 = 185.00
G3  = 196.00
Ab3 = 207.65
A3  = 220.00
Bb3 = 233.08
B3  = 246.94

# Octave 4
C4  = 261.63
Db4 = 277.18
D4  = 293.66
Eb4 = 311.13
E4  = 329.63
F4  = 349.23
Gb4 = 369.99
G4  = 392.00
Ab4 = 415.30
A4  = 440.00
Bb4 = 466.16
B4  = 493.88

# Octave 5
C5  = 523.25
Db5 = 554.37
D5  = 587.33
Eb5 = 622.25
E5  = 659.25
F5  = 698.46
Gb5 = 739.99
G5  = 783.99
Ab5 = 830.61
A5  = 880.00
Bb5 = 932.33
B5  = 987.77

# Silence marker
REST = 0.0

# Max amplitude for 16-bit signed audio
_INT16_MAX = 32767

# ---------------------------------------------------------------------------
# Low-level waveform generators
# ---------------------------------------------------------------------------

def generate_sine(freq, duration, volume=0.5, sample_rate=SAMPLE_RATE):
    """Generate a sine wave tone.

    Args:
        freq: Frequency in Hz.
        duration: Duration in seconds.
        volume: Peak amplitude in the range [0.0, 1.0].
        sample_rate: Samples per second.

    Returns:
        A list of float samples in the range [-1.0, 1.0].
    """
    num_samples = int(sample_rate * duration)
    if freq <= 0.0 or num_samples == 0:
        return [0.0] * max(num_samples, 0)
    two_pi_freq_over_sr = 2.0 * math.pi * freq / sample_rate
    return [volume * math.sin(two_pi_freq_over_sr * i) for i in range(num_samples)]


def generate_square(freq, duration, volume=0.3, sample_rate=SAMPLE_RATE):
    """Generate a square wave tone (chiptune style).

    The square wave alternates between +volume and -volume at the given
    frequency, producing the classic 8-bit synthesizer timbre.

    Args:
        freq: Frequency in Hz.
        duration: Duration in seconds.
        volume: Peak amplitude in the range [0.0, 1.0].
        sample_rate: Samples per second.

    Returns:
        A list of float samples in the range [-1.0, 1.0].
    """
    num_samples = int(sample_rate * duration)
    if freq <= 0.0 or num_samples == 0:
        return [0.0] * max(num_samples, 0)
    period = sample_rate / freq
    samples = []
    for i in range(num_samples):
        phase = (i % period) / period  # 0.0 to <1.0
        samples.append(volume if phase < 0.5 else -volume)
    return samples


def generate_triangle(freq, duration, volume=0.4, sample_rate=SAMPLE_RATE):
    """Generate a triangle wave.

    Triangle waves have a softer timbre than square waves while still
    retaining some harmonic content above a pure sine.

    Args:
        freq: Frequency in Hz.
        duration: Duration in seconds.
        volume: Peak amplitude in the range [0.0, 1.0].
        sample_rate: Samples per second.

    Returns:
        A list of float samples in the range [-1.0, 1.0].
    """
    num_samples = int(sample_rate * duration)
    if freq <= 0.0 or num_samples == 0:
        return [0.0] * max(num_samples, 0)
    period = sample_rate / freq
    samples = []
    for i in range(num_samples):
        phase = (i % period) / period  # 0.0 to <1.0
        # Rise from -1 to +1 in first half, fall from +1 to -1 in second half
        if phase < 0.5:
            value = -1.0 + 4.0 * phase
        else:
            value = 3.0 - 4.0 * phase
        samples.append(volume * value)
    return samples


def generate_noise(duration, volume=0.3, sample_rate=SAMPLE_RATE):
    """Generate white noise.

    Args:
        duration: Duration in seconds.
        volume: Peak amplitude in the range [0.0, 1.0].
        sample_rate: Samples per second.

    Returns:
        A list of float samples in the range [-volume, volume].
    """
    num_samples = int(sample_rate * duration)
    # Use a seeded generator so noise is deterministic across calls,
    # which makes individual sound effects reproducible.
    rng = random.Random(42)
    return [volume * (rng.random() * 2.0 - 1.0) for _ in range(num_samples)]


def generate_noise_unseeded(duration, volume=0.3, sample_rate=SAMPLE_RATE):
    """Generate white noise with a fresh random seed each call.

    Used internally where variation between calls is acceptable.
    """
    num_samples = int(sample_rate * duration)
    return [volume * (random.random() * 2.0 - 1.0) for _ in range(num_samples)]


# ---------------------------------------------------------------------------
# Envelope and mixing utilities
# ---------------------------------------------------------------------------

def apply_envelope(samples, attack, decay, sustain, release):
    """Apply an ADSR envelope to a sample list.

    The envelope is time-based: attack, decay, and release are expressed as
    fractions of the total sample length. sustain is an amplitude level
    [0.0, 1.0] held through the middle portion.

    Args:
        samples: List of float samples.
        attack:  Fraction of total duration spent rising from 0 to 1.
        decay:   Fraction of total duration spent falling from 1 to sustain.
        sustain: Amplitude level held during the sustain phase.
        release: Fraction of total duration spent falling from sustain to 0.
                 The sustain phase fills whatever time remains.

    Returns:
        A new list with the envelope applied.
    """
    n = len(samples)
    if n == 0:
        return []

    attack_end  = int(n * attack)
    decay_end   = attack_end + int(n * decay)
    release_start = max(decay_end, n - int(n * release))
    result = []

    for i, s in enumerate(samples):
        if i < attack_end:
            # Attack: linear ramp 0 -> 1
            env = i / attack_end if attack_end > 0 else 1.0
        elif i < decay_end:
            # Decay: linear ramp 1 -> sustain
            span = decay_end - attack_end
            progress = (i - attack_end) / span if span > 0 else 1.0
            env = 1.0 - progress * (1.0 - sustain)
        elif i < release_start:
            # Sustain
            env = sustain
        else:
            # Release: linear ramp sustain -> 0
            span = n - release_start
            progress = (i - release_start) / span if span > 0 else 1.0
            env = sustain * (1.0 - progress)
        result.append(s * env)

    return result


def apply_exponential_decay(samples, decay_rate=5.0):
    """Apply an exponential amplitude decay over the sample list.

    Args:
        samples: List of float samples.
        decay_rate: Higher values produce faster decay. A value of 5 decays
                    to roughly e^-5 (~0.007) of the original by the end.

    Returns:
        A new list with decay applied.
    """
    n = len(samples)
    if n == 0:
        return []
    return [s * math.exp(-decay_rate * i / n) for i, s in enumerate(samples)]


def mix_sounds(*sound_arrays):
    """Mix multiple equal-length sound arrays, normalizing to prevent clipping.

    All arrays must contain float samples. If they differ in length, shorter
    arrays are zero-padded on the right to match the longest.

    Args:
        *sound_arrays: Any number of lists of float samples.

    Returns:
        A list of float samples normalized to fit within [-1.0, 1.0].
    """
    if not sound_arrays:
        return []

    # Pad all arrays to the same length
    max_len = max(len(a) for a in sound_arrays)
    padded = []
    for a in sound_arrays:
        if len(a) < max_len:
            padded.append(list(a) + [0.0] * (max_len - len(a)))
        else:
            padded.append(a)

    # Sum
    mixed = [sum(padded[j][i] for j in range(len(padded))) for i in range(max_len)]

    # Normalize
    peak = max(abs(s) for s in mixed) if mixed else 0.0
    if peak > 1.0:
        mixed = [s / peak for s in mixed]

    return mixed


def samples_to_sound(samples, sample_rate=SAMPLE_RATE):
    """Convert a list of float samples in [-1, 1] to a pygame.mixer.Sound.

    The samples are converted to 16-bit signed integers and packed into an
    array.array('h') buffer, which pygame.mixer.Sound accepts directly.

    Args:
        samples: List of float samples in the range [-1.0, 1.0].
        sample_rate: Sample rate (informational; mixer must already be init'd
                     at this rate).

    Returns:
        A pygame.mixer.Sound object, or None if mixer is unavailable.
    """
    try:
        int_samples = array.array('h', [
            max(-_INT16_MAX, min(_INT16_MAX, int(s * _INT16_MAX)))
            for s in samples
        ])
        sound = pygame.mixer.Sound(buffer=int_samples)
        return sound
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Low-pass filter helper (simple first-order IIR)
# ---------------------------------------------------------------------------

def low_pass_filter(samples, cutoff_freq, sample_rate=SAMPLE_RATE):
    """Apply a simple first-order IIR low-pass filter.

    Args:
        samples: List of float samples.
        cutoff_freq: Cutoff frequency in Hz.
        sample_rate: Sample rate in Hz.

    Returns:
        Filtered list of float samples.
    """
    if not samples:
        return []
    rc = 1.0 / (2.0 * math.pi * cutoff_freq)
    dt = 1.0 / sample_rate
    alpha = dt / (rc + dt)
    filtered = [samples[0]]
    for i in range(1, len(samples)):
        filtered.append(filtered[-1] + alpha * (samples[i] - filtered[-1]))
    return filtered


# ---------------------------------------------------------------------------
# Sound effect generators
# ---------------------------------------------------------------------------

def _make_light_hit(sample_rate=SAMPLE_RATE):
    """Quick, snappy punch sound (~100 ms).

    A short noise burst mixed with a high-mid sine adds both the percussive
    crack and a tonal body characteristic of a light strike.
    """
    duration = 0.10
    noise = generate_noise(duration, volume=0.6, sample_rate=sample_rate)
    tone  = generate_sine(800, duration, volume=0.3, sample_rate=sample_rate)
    mixed = mix_sounds(noise, tone)
    # Sharp attack, fast exponential decay
    enveloped = apply_envelope(mixed, attack=0.02, decay=0.20, sustain=0.0, release=0.78)
    return apply_exponential_decay(enveloped, decay_rate=8.0)


def _make_heavy_hit(sample_rate=SAMPLE_RATE):
    """Meaty thwack (~200 ms).

    Lower frequency sine (thud body) plus noise (attack crack) with a longer
    sustain tail gives weight to the impact.
    """
    duration = 0.20
    noise = generate_noise(duration, volume=0.5, sample_rate=sample_rate)
    low   = generate_sine(120, duration, volume=0.6, sample_rate=sample_rate)
    mid   = generate_sine(300, duration, volume=0.25, sample_rate=sample_rate)
    mixed = mix_sounds(noise, low, mid)
    enveloped = apply_envelope(mixed, attack=0.01, decay=0.15, sustain=0.3, release=0.54)
    return apply_exponential_decay(enveloped, decay_rate=5.0)


def _make_special_hit(sample_rate=SAMPLE_RATE):
    """Dramatic impact with reverb-like tail (~400 ms).

    Three layered sine frequencies plus a noise burst create a rich, weighty
    sound. A slow release mimics early reflections.
    """
    duration = 0.40
    noise  = generate_noise(duration, volume=0.4, sample_rate=sample_rate)
    low    = generate_sine(80,  duration, volume=0.5, sample_rate=sample_rate)
    mid    = generate_sine(200, duration, volume=0.3, sample_rate=sample_rate)
    high   = generate_sine(600, duration, volume=0.2, sample_rate=sample_rate)
    mixed  = mix_sounds(noise, low, mid, high)
    enveloped = apply_envelope(mixed, attack=0.01, decay=0.10, sustain=0.4, release=0.49)
    return apply_exponential_decay(enveloped, decay_rate=3.5)


def _make_block_sound(sample_rate=SAMPLE_RATE):
    """Metallic clang (~150 ms).

    Two closely-spaced high-frequency sines produce beating / shimmer; rapid
    decay suggests hard material contact.
    """
    duration = 0.15
    sine1 = generate_sine(1200, duration, volume=0.5, sample_rate=sample_rate)
    sine2 = generate_sine(1350, duration, volume=0.3, sample_rate=sample_rate)
    noise = generate_noise(duration, volume=0.15, sample_rate=sample_rate)
    mixed = mix_sounds(sine1, sine2, noise)
    enveloped = apply_envelope(mixed, attack=0.005, decay=0.10, sustain=0.1, release=0.50)
    return apply_exponential_decay(enveloped, decay_rate=9.0)


def _make_whoosh(sample_rate=SAMPLE_RATE):
    """Swing/miss sound - filtered noise sweep from high to low (~150 ms).

    The cutoff frequency of the low-pass filter is swept downward over time,
    producing the characteristic Doppler-like quality of a near-miss.
    """
    duration = 0.15
    num_samples = int(sample_rate * duration)
    noise = generate_noise(duration, volume=0.5, sample_rate=sample_rate)

    # Sweep cutoff from 4000 Hz down to 400 Hz sample-by-sample
    filtered = []
    rc_start = 1.0 / (2.0 * math.pi * 4000)
    rc_end   = 1.0 / (2.0 * math.pi * 400)
    dt = 1.0 / sample_rate
    prev = noise[0]
    for i in range(num_samples):
        progress = i / max(num_samples - 1, 1)
        rc    = rc_start + progress * (rc_end - rc_start)
        alpha = dt / (rc + dt)
        val   = prev + alpha * (noise[i] - prev)
        filtered.append(val)
        prev = val

    enveloped = apply_envelope(filtered, attack=0.05, decay=0.20, sustain=0.3, release=0.45)
    return apply_exponential_decay(enveloped, decay_rate=4.0)


def _make_ko_sound(sample_rate=SAMPLE_RATE):
    """Knockout impact - deep bass hit plus high crack (~500 ms).

    The crack is a very short noise burst while the bass thud provides the
    seismic feel of a final blow.
    """
    duration = 0.50
    num_samples = int(sample_rate * duration)

    # Deep bass sine that drops in pitch (pitch bend down)
    bass = []
    for i in range(num_samples):
        progress = i / max(num_samples - 1, 1)
        freq = 60.0 + (1.0 - progress) * 80.0  # 140 Hz -> 60 Hz
        val  = 0.7 * math.sin(2.0 * math.pi * freq * i / sample_rate)
        bass.append(val)

    crack_dur = 0.04
    crack = generate_noise(crack_dur, volume=0.8, sample_rate=sample_rate)
    # Pad crack to full duration
    crack += [0.0] * (num_samples - len(crack))

    rumble = generate_noise(duration, volume=0.2, sample_rate=sample_rate)
    rumble = low_pass_filter(rumble, cutoff_freq=200, sample_rate=sample_rate)

    mixed = mix_sounds(bass, crack, rumble)
    enveloped = apply_envelope(mixed, attack=0.005, decay=0.15, sustain=0.3, release=0.545)
    return apply_exponential_decay(enveloped, decay_rate=3.0)


def _make_menu_select(sample_rate=SAMPLE_RATE):
    """Clean sine blip for menu navigation (~80 ms)."""
    duration = 0.08
    tone = generate_sine(880, duration, volume=0.4, sample_rate=sample_rate)
    return apply_envelope(tone, attack=0.05, decay=0.10, sustain=0.0, release=0.85)


def _make_menu_confirm(sample_rate=SAMPLE_RATE):
    """Two-tone ascending confirmation sound (~150 ms)."""
    half = 0.075
    tone1 = generate_sine(660, half, volume=0.4, sample_rate=sample_rate)
    tone2 = generate_sine(880, half, volume=0.4, sample_rate=sample_rate)
    tone1 = apply_envelope(tone1, attack=0.05, decay=0.10, sustain=0.6, release=0.25)
    tone2 = apply_envelope(tone2, attack=0.05, decay=0.10, sustain=0.6, release=0.25)
    return tone1 + tone2


def _make_round_start(sample_rate=SAMPLE_RATE):
    """Rising tone sweep for 'Fight!' indicator (~300 ms)."""
    duration = 0.30
    num_samples = int(sample_rate * duration)
    samples = []
    for i in range(num_samples):
        progress = i / max(num_samples - 1, 1)
        freq = 300.0 + progress * 600.0  # 300 -> 900 Hz
        samples.append(0.5 * math.sin(2.0 * math.pi * freq * i / sample_rate))
    return apply_envelope(samples, attack=0.05, decay=0.10, sustain=0.7, release=0.15)


def _make_victory_fanfare(sample_rate=SAMPLE_RATE):
    """Short victory jingle - ascending arpeggio in C major (~1500 ms).

    The arpeggio ascends through C4-E4-G4-C5 then ends with a held note,
    giving a triumphant flavour appropriate to winning a round.
    """
    bpm = 180
    beat = 60.0 / bpm

    # (frequency, beats) pairs
    notes = [
        (C4, 0.5), (E4, 0.5), (G4, 0.5), (C5, 0.5),
        (E5, 0.5), (G5, 0.5), (C5, 1.0), (G4, 1.0),
    ]

    result = []
    for freq, beats in notes:
        dur = beats * beat
        tone = generate_square(freq, dur, volume=0.35, sample_rate=sample_rate)
        tone = apply_envelope(tone, attack=0.05, decay=0.10, sustain=0.7, release=0.15)
        result.extend(tone)

    return result


def _make_defeat_sound(sample_rate=SAMPLE_RATE):
    """Descending sad tones (~1000 ms).

    Descends through A4-F4-D4-A3 in a minor-flavoured pattern with a slow
    piano-like envelope on each note.
    """
    bpm = 100
    beat = 60.0 / bpm

    notes = [
        (A4,  0.5), (F4,  0.5), (D4,  0.5), (A3,  1.5),
    ]

    result = []
    for freq, beats in notes:
        dur = beats * beat
        tone = generate_triangle(freq, dur, volume=0.35, sample_rate=sample_rate)
        tone = apply_envelope(tone, attack=0.03, decay=0.20, sustain=0.5, release=0.27)
        result.extend(tone)

    return result


def _make_syrup_splash(sample_rate=SAMPLE_RATE):
    """Wet splat sound with low-pass character (~200 ms).

    Noise filtered through an aggressive low-pass sounds like a viscous fluid
    impact. A fast attack onset reinforces the percussive splat quality.
    """
    duration = 0.20
    noise = generate_noise(duration, volume=0.7, sample_rate=sample_rate)
    filtered = low_pass_filter(noise, cutoff_freq=600, sample_rate=sample_rate)
    enveloped = apply_envelope(filtered, attack=0.01, decay=0.15, sustain=0.2, release=0.64)
    return apply_exponential_decay(enveloped, decay_rate=4.5)


def _make_fire_blast(sample_rate=SAMPLE_RATE):
    """Whooshing flame - noise with resonant frequency sweep (~400 ms).

    Sweeping the low-pass cutoff upward mid-sound mimics the ignition and
    flare of a flame burst.
    """
    duration = 0.40
    num_samples = int(sample_rate * duration)
    noise = generate_noise(duration, volume=0.6, sample_rate=sample_rate)

    # Sweep cutoff 200 Hz -> 2000 Hz -> 800 Hz (rises then falls)
    filtered = []
    prev = noise[0]
    dt = 1.0 / sample_rate
    for i in range(num_samples):
        progress = i / max(num_samples - 1, 1)
        # Bell-curve sweep
        if progress < 0.5:
            cutoff = 200.0 + progress * 2.0 * 1800.0
        else:
            cutoff = 2000.0 - (progress - 0.5) * 2.0 * 1200.0
        rc    = 1.0 / (2.0 * math.pi * max(cutoff, 50.0))
        alpha = dt / (rc + dt)
        val   = prev + alpha * (noise[i] - prev)
        filtered.append(val)
        prev = val

    # Add a resonant buzz underneath
    buzz = generate_triangle(180, duration, volume=0.2, sample_rate=sample_rate)
    mixed = mix_sounds(filtered, buzz)
    return apply_envelope(mixed, attack=0.03, decay=0.20, sustain=0.4, release=0.37)


def _make_freeze_sound(sample_rate=SAMPLE_RATE):
    """Ice crystallizing - high tinkling tones with shimmer (~300 ms).

    Multiple high-frequency sines with slight detuning produce the glassy,
    crystalline quality of ice forming rapidly.
    """
    duration = 0.30
    freqs  = [2093.0, 2349.0, 2637.0, 3136.0, 2793.0]  # C7, D7, E7, G7, F7
    tones  = [generate_sine(f, duration, volume=0.15, sample_rate=sample_rate) for f in freqs]
    shimmer = generate_noise(duration, volume=0.1, sample_rate=sample_rate)
    # High-pass the shimmer by subtracting a low-pass version
    low = low_pass_filter(shimmer, cutoff_freq=3000, sample_rate=sample_rate)
    hp_shimmer = [shimmer[i] - low[i] for i in range(len(shimmer))]

    mixed = mix_sounds(*tones, hp_shimmer)
    return apply_envelope(mixed, attack=0.01, decay=0.20, sustain=0.3, release=0.49)


def _make_ground_pound(sample_rate=SAMPLE_RATE):
    """Heavy bass slam with rumble (~500 ms).

    A very low sine burst combined with a broadband noise rumble gives the
    feeling of a heavy character landing on solid ground.
    """
    duration = 0.50
    num_samples = int(sample_rate * duration)

    # Pitch-bending bass: starts at 100 Hz, drops to 40 Hz
    bass = []
    for i in range(num_samples):
        progress = i / max(num_samples - 1, 1)
        freq = 100.0 * math.exp(-progress * 0.9)  # exponential drop
        bass.append(0.7 * math.sin(2.0 * math.pi * freq * i / sample_rate))

    rumble = generate_noise(duration, volume=0.3, sample_rate=sample_rate)
    rumble = low_pass_filter(rumble, cutoff_freq=150, sample_rate=sample_rate)

    mixed = mix_sounds(bass, rumble)
    enveloped = apply_envelope(mixed, attack=0.005, decay=0.10, sustain=0.4, release=0.495)
    return apply_exponential_decay(enveloped, decay_rate=3.0)


def _make_rage_activate(sample_rate=SAMPLE_RATE):
    """Power-up roar - rising intensity noise plus bass (~600 ms).

    The noise volume sweeps upward while a bass drone rises in pitch,
    conveying the build-up of adrenaline and power.
    """
    duration = 0.60
    num_samples = int(sample_rate * duration)

    # Rising noise intensity
    noise_base = generate_noise(duration, volume=1.0, sample_rate=sample_rate)
    noise = []
    for i, s in enumerate(noise_base):
        progress = i / max(num_samples - 1, 1)
        env = progress ** 0.5  # square root curve - fast initial rise
        noise.append(s * 0.5 * env)

    # Rising bass sine from 60 Hz to 160 Hz
    bass = []
    for i in range(num_samples):
        progress = i / max(num_samples - 1, 1)
        freq = 60.0 + progress * 100.0
        bass.append(0.4 * math.sin(2.0 * math.pi * freq * i / sample_rate))

    # Low-pass the noise
    noise = low_pass_filter(noise, cutoff_freq=800, sample_rate=sample_rate)

    mixed = mix_sounds(noise, bass)
    return apply_envelope(mixed, attack=0.10, decay=0.05, sustain=0.8, release=0.05)


# ---------------------------------------------------------------------------
# Music generation
# ---------------------------------------------------------------------------

def _beats_to_seconds(beats, bpm):
    """Convert a beat count to seconds at the given BPM."""
    return beats * 60.0 / bpm


def _render_sequence(notes, bpm, generator_fn, sample_rate=SAMPLE_RATE):
    """Render a list of (frequency, beats) note tuples to a sample list.

    Args:
        notes: List of (freq, beats) tuples. freq=0 or REST produces silence.
        bpm: Beats per minute.
        generator_fn: Callable(freq, duration, sample_rate) -> [floats]
        sample_rate: Sample rate.

    Returns:
        Flat list of float samples.
    """
    result = []
    for freq, beats in notes:
        duration = _beats_to_seconds(beats, bpm)
        if freq <= 0.0:
            result.extend([0.0] * int(sample_rate * duration))
        else:
            samples = generator_fn(freq, duration, sample_rate)
            # Apply a short per-note release to avoid clicks between notes
            samples = apply_envelope(samples, attack=0.02, decay=0.05,
                                     sustain=0.75, release=0.18)
            result.extend(samples)
    return result


def _render_percussion(num_samples, bpm, pattern, sample_rate=SAMPLE_RATE):
    """Render a simple percussion pattern to a sample list.

    Args:
        num_samples: Total output length in samples.
        bpm: Beats per minute.
        pattern: List of (beat_offset, 'kick'|'snare'|'hat') describing hits.
        sample_rate: Sample rate.

    Returns:
        List of float samples of length num_samples.
    """
    output = [0.0] * num_samples
    beat_samples = int(sample_rate * 60.0 / bpm)

    kick_dur  = 0.08
    snare_dur = 0.06
    hat_dur   = 0.03

    for beat_offset, hit_type in pattern:
        start = int(beat_offset * beat_samples)
        if start >= num_samples:
            continue

        if hit_type == 'kick':
            # Low thud
            n = int(sample_rate * kick_dur)
            for i in range(n):
                if start + i >= num_samples:
                    break
                progress = i / max(n - 1, 1)
                freq = 80.0 * math.exp(-progress * 4.0)
                env  = math.exp(-progress * 8.0)
                output[start + i] += 0.6 * env * math.sin(
                    2.0 * math.pi * freq * i / sample_rate)

        elif hit_type == 'snare':
            # Noise burst
            n = int(sample_rate * snare_dur)
            rng = random.Random(hit_type + str(beat_offset))
            for i in range(n):
                if start + i >= num_samples:
                    break
                env = math.exp(-i / (sample_rate * snare_dur) * 6.0)
                output[start + i] += 0.4 * env * (rng.random() * 2.0 - 1.0)

        elif hit_type == 'hat':
            # High noise tick
            n = int(sample_rate * hat_dur)
            rng = random.Random(hit_type + str(beat_offset))
            for i in range(n):
                if start + i >= num_samples:
                    break
                env = math.exp(-i / (sample_rate * hat_dur) * 10.0)
                output[start + i] += 0.2 * env * (rng.random() * 2.0 - 1.0)

    return output


def _normalize(samples, target_peak=0.85):
    """Normalize samples so the peak is at target_peak."""
    peak = max(abs(s) for s in samples) if samples else 0.0
    if peak == 0.0:
        return samples
    scale = target_peak / peak
    return [s * scale for s in samples]


def _generate_fight_music(sample_rate=SAMPLE_RATE):
    """Generate the main battle theme in C minor at 140 BPM.

    Structure: 8-bar loop with melody, bass, and percussion.
    Melody uses the C natural minor scale for an energetic, driving feel.
    """
    bpm = 140
    # Total length: 16 beats (4/4 time, 4 bars)
    total_beats = 16
    total_duration = _beats_to_seconds(total_beats, bpm)
    total_samples = int(sample_rate * total_duration)

    # --- Melody (square wave, C minor pentatonic pattern) ---
    melody_notes = [
        # Bar 1
        (C4, 0.5), (Eb4, 0.5), (F4, 0.5), (G4, 0.5),
        # Bar 2
        (Ab4, 0.5), (G4, 0.5), (F4, 0.5), (Eb4, 0.5),
        # Bar 3
        (C4, 0.5), (G4, 0.5), (Ab4, 0.5), (G4, 0.5),
        # Bar 4
        (F4, 0.5), (Eb4, 0.5), (C4, 1.0),
        # Bar 5 - variation, higher register
        (C5, 0.5), (Bb4, 0.5), (Ab4, 0.5), (G4, 0.5),
        # Bar 6
        (F4, 0.5), (G4, 0.5), (Ab4, 0.5), (G4, 0.5),
        # Bar 7
        (Eb4, 0.5), (F4, 0.5), (G4, 0.5), (Ab4, 0.5),
        # Bar 8 - resolve back to C
        (G4, 0.5), (F4, 0.5), (Eb4, 0.5), (C4, 0.5),
    ]

    def sq_gen(freq, duration, sr):
        return generate_square(freq, duration, volume=0.28, sample_rate=sr)

    melody = _render_sequence(melody_notes, bpm, sq_gen, sample_rate)

    # --- Counter-melody (triangle wave, harmony) ---
    counter_notes = [
        (G3, 1.0), (Ab3, 1.0), (G3, 1.0), (F3, 1.0),
        (Eb3, 1.0), (F3, 1.0), (G3, 1.0), (C3, 1.0),
        (G3, 1.0), (Ab3, 1.0), (G3, 1.0), (F3, 1.0),
        (Eb3, 1.0), (F3, 1.0), (G3, 0.5), (Ab3, 0.5),
    ]

    def tri_gen(freq, duration, sr):
        return generate_triangle(freq, duration, volume=0.18, sample_rate=sr)

    counter = _render_sequence(counter_notes, bpm, tri_gen, sample_rate)

    # --- Bass line (square wave, low register) ---
    bass_notes = [
        (C3, 0.5), (REST, 0.25), (C3, 0.25), (G3, 0.5), (REST, 0.5),
        (Ab3, 0.5), (REST, 0.25), (Ab3, 0.25), (G3, 0.5), (REST, 0.5),
        (C3, 0.5), (REST, 0.25), (C3, 0.25), (F3, 0.5), (REST, 0.5),
        (G3, 0.5), (REST, 0.25), (G3, 0.25), (C3, 0.5), (REST, 0.5),
        (C3, 0.5), (REST, 0.25), (C3, 0.25), (Eb3, 0.5), (REST, 0.5),
        (F3, 0.5), (REST, 0.25), (F3, 0.25), (G3, 0.5), (REST, 0.5),
        (Ab3, 0.5), (REST, 0.25), (G3, 0.25), (F3, 0.5), (REST, 0.5),
        (G3, 0.5), (REST, 0.25), (G3, 0.25), (C3, 0.5), (REST, 0.5),
    ]

    def bass_gen(freq, duration, sr):
        return generate_square(freq, duration, volume=0.22, sample_rate=sr)

    bass = _render_sequence(bass_notes, bpm, bass_gen, sample_rate)

    # --- Percussion (kick, snare, hi-hat pattern) ---
    # 16-beat pattern (4/4 with 16th-note resolution)
    perc_pattern = []
    for bar in range(4):
        offset = bar * 4.0
        # Kick on beat 1, beat 3 (slightly syncopated in bar 4)
        perc_pattern += [
            (offset + 0.0,   'kick'),
            (offset + 0.5,   'hat'),
            (offset + 1.0,   'snare'),
            (offset + 1.5,   'hat'),
            (offset + 2.0,   'kick'),
            (offset + 2.5,   'hat'),
            (offset + 3.0,   'snare'),
            (offset + 3.5,   'hat'),
        ]
    # Second half of loop (bars 5-8)
    for bar in range(4):
        offset = 8.0 + bar * 4.0
        perc_pattern += [
            (offset + 0.0,   'kick'),
            (offset + 0.25,  'hat'),
            (offset + 0.5,   'hat'),
            (offset + 0.75,  'hat'),
            (offset + 1.0,   'snare'),
            (offset + 1.5,   'hat'),
            (offset + 2.0,   'kick'),
            (offset + 2.25,  'kick'),
            (offset + 2.5,   'hat'),
            (offset + 3.0,   'snare'),
            (offset + 3.5,   'hat'),
        ]

    percussion = _render_percussion(total_samples, bpm, perc_pattern, sample_rate)

    # Pad/trim all tracks to total_samples
    def fit(s):
        if len(s) < total_samples:
            return s + [0.0] * (total_samples - len(s))
        return s[:total_samples]

    melody    = fit(melody)
    counter   = fit(counter)
    bass      = fit(bass)
    percussion = fit(percussion)

    mixed = mix_sounds(melody, counter, bass, percussion)
    return _normalize(mixed, target_peak=0.75)


def _generate_boss_music(sample_rate=SAMPLE_RATE):
    """Generate the boss battle theme in E minor at 155 BPM.

    Darker, more intense than the fight theme. Lower register, dissonant
    intervals, driving triplet-feel bass line.
    """
    bpm = 155

    # Note constants for E minor
    E3n  = 164.81
    Fs3  = 185.00
    G3n  = 196.00
    A3n  = 220.00
    B3n  = 246.94
    C4n  = 261.63
    D4n  = 293.66
    E4n  = 329.63
    Fs4  = 369.99
    G4n  = 392.00
    A4n  = 440.00
    B4n  = 493.88

    total_beats   = 16
    total_duration = _beats_to_seconds(total_beats, bpm)
    total_samples  = int(sample_rate * total_duration)

    # --- Melody (square, dark E minor) ---
    melody_notes = [
        (E4n, 0.5), (D4n, 0.5), (C4n, 0.5), (B3n, 0.5),
        (A3n, 0.5), (B3n, 0.5), (C4n, 0.5), (D4n, 0.5),
        (E4n, 0.5), (Fs4, 0.5), (G4n, 0.5), (A4n, 0.5),
        (B4n, 0.5), (A4n, 0.5), (G4n, 0.5), (Fs4, 0.5),
        (E4n, 0.5), (G4n, 0.5), (B3n, 0.5), (C4n, 0.5),
        (D4n, 0.5), (C4n, 0.5), (B3n, 0.5), (A3n, 0.5),
        (G3n, 0.5), (A3n, 0.5), (B3n, 0.5), (C4n, 0.5),
        (D4n, 0.5), (B3n, 0.5), (E3n, 1.0),
    ]

    def sq_gen(freq, duration, sr):
        return generate_square(freq, duration, volume=0.26, sample_rate=sr)

    melody = _render_sequence(melody_notes, bpm, sq_gen, sample_rate)

    # --- Ominous sustained bass ---
    bass_notes = [
        (E3n, 1.0), (E3n, 1.0), (A3n, 1.0), (B3n, 1.0),
        (G3n, 1.0), (G3n, 1.0), (D4n, 1.0), (E3n, 1.0),
        (C4n, 1.0), (C4n, 1.0), (G3n, 1.0), (A3n, 1.0),
        (B3n, 1.0), (A3n, 1.0), (G3n, 0.5), (Fs3, 0.5),
    ]

    def tri_bass(freq, duration, sr):
        return generate_triangle(freq, duration, volume=0.24, sample_rate=sr)

    bass = _render_sequence(bass_notes, bpm, tri_bass, sample_rate)

    # --- Driving inner voice (triangle, mid-register) ---
    inner_notes = [
        (B3n, 0.25), (A3n, 0.25), (G3n, 0.25), (Fs3, 0.25),
        (E3n, 0.25), (Fs3, 0.25), (G3n, 0.25), (A3n, 0.25),
        (B3n, 0.25), (A3n, 0.25), (B3n, 0.25), (C4n, 0.25),
        (D4n, 0.25), (C4n, 0.25), (B3n, 0.25), (A3n, 0.25),
    ] * 4  # repeat 4 times to fill 16 beats

    def tri_gen(freq, duration, sr):
        return generate_triangle(freq, duration, volume=0.14, sample_rate=sr)

    inner = _render_sequence(inner_notes, bpm, tri_gen, sample_rate)

    # --- Heavy percussion ---
    perc_pattern = []
    for bar in range(8):
        offset = bar * 2.0  # 2 beats per bar at double-time feel
        perc_pattern += [
            (offset + 0.0,   'kick'),
            (offset + 0.25,  'hat'),
            (offset + 0.5,   'snare'),
            (offset + 0.75,  'hat'),
            (offset + 1.0,   'kick'),
            (offset + 1.25,  'hat'),
            (offset + 1.5,   'snare'),
            (offset + 1.75,  'kick'),  # extra kick for intensity
        ]

    percussion = _render_percussion(total_samples, bpm, perc_pattern, sample_rate)

    def fit(s):
        if len(s) < total_samples:
            return s + [0.0] * (total_samples - len(s))
        return s[:total_samples]

    melody    = fit(melody)
    bass      = fit(bass)
    inner     = fit(inner)
    percussion = fit(percussion)

    mixed = mix_sounds(melody, bass, inner, percussion)
    return _normalize(mixed, target_peak=0.80)


def _generate_menu_music(sample_rate=SAMPLE_RATE):
    """Generate the title/menu theme in C major at 120 BPM.

    Light, catchy, major-key feel. Square wave melody with a walking bass
    line and gentle hi-hat rhythm.
    """
    bpm = 120

    total_beats    = 16
    total_duration = _beats_to_seconds(total_beats, bpm)
    total_samples  = int(sample_rate * total_duration)

    # --- Cheerful C major melody ---
    melody_notes = [
        (C4, 0.5), (E4, 0.5), (G4, 0.5), (E4, 0.5),
        (F4, 0.5), (A4, 0.5), (G4, 1.0),
        (E4, 0.5), (G4, 0.5), (A4, 0.5), (G4, 0.5),
        (F4, 0.5), (E4, 0.5), (D4, 1.0),
        (C4, 0.5), (D4, 0.5), (E4, 0.5), (F4, 0.5),
        (G4, 0.5), (A4, 0.5), (B4, 0.5), (C5, 0.5),
        (B4, 0.5), (A4, 0.5), (G4, 0.5), (F4, 0.5),
        (E4, 0.5), (D4, 0.5), (C4, 1.0),
    ]

    def sq_gen(freq, duration, sr):
        return generate_square(freq, duration, volume=0.25, sample_rate=sr)

    melody = _render_sequence(melody_notes, bpm, sq_gen, sample_rate)

    # --- Walking bass line ---
    bass_notes = [
        (C3, 1.0), (G3, 1.0), (A3, 1.0), (F3, 1.0),
        (C3, 1.0), (G3, 1.0), (A3, 1.0), (E3, 1.0),
        (F3, 1.0), (C3, 1.0), (G3, 1.0), (D3, 1.0),
        (E3, 1.0), (A3, 1.0), (G3, 1.0), (C3, 1.0),
    ]

    def bass_gen(freq, duration, sr):
        return generate_triangle(freq, duration, volume=0.20, sample_rate=sr)

    bass = _render_sequence(bass_notes, bpm, bass_gen, sample_rate)

    # --- Harmony (triangle, thirds above melody) ---
    harm_notes = [
        (E4, 0.5), (G4, 0.5), (B4, 0.5), (G4, 0.5),
        (A4, 0.5), (C5, 0.5), (B4, 1.0),
        (G4, 0.5), (B4, 0.5), (C5, 0.5), (B4, 0.5),
        (A4, 0.5), (G4, 0.5), (F4, 1.0),
        (E4, 0.5), (F4, 0.5), (G4, 0.5), (A4, 0.5),
        (B4, 0.5), (C5, 0.5), (D5, 0.5), (E5, 0.5),
        (D5, 0.5), (C5, 0.5), (B4, 0.5), (A4, 0.5),
        (G4, 0.5), (F4, 0.5), (E4, 1.0),
    ]

    def harm_gen(freq, duration, sr):
        return generate_triangle(freq, duration, volume=0.14, sample_rate=sr)

    harmony = _render_sequence(harm_notes, bpm, harm_gen, sample_rate)

    # --- Light percussion ---
    perc_pattern = []
    for bar in range(8):
        offset = bar * 2.0
        perc_pattern += [
            (offset + 0.0,  'kick'),
            (offset + 0.5,  'hat'),
            (offset + 1.0,  'snare'),
            (offset + 1.5,  'hat'),
        ]

    percussion = _render_percussion(total_samples, bpm, perc_pattern, sample_rate)

    def fit(s):
        if len(s) < total_samples:
            return s + [0.0] * (total_samples - len(s))
        return s[:total_samples]

    melody    = fit(melody)
    bass      = fit(bass)
    harmony   = fit(harmony)
    percussion = fit(percussion)

    mixed = mix_sounds(melody, bass, harmony, percussion)
    return _normalize(mixed, target_peak=0.70)


# ---------------------------------------------------------------------------
# SoundManager class
# ---------------------------------------------------------------------------

class SoundManager:
    """Central audio controller for Cooking Combat.

    Handles initialization, procedural generation, playback, and volume
    control for all sound effects and music tracks.

    If pygame.mixer fails to initialize, all public methods become no-ops so
    the game continues to function in a silent-mode fallback.
    """

    def __init__(self):
        self._available = False
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._music: dict[str, pygame.mixer.Sound]  = {}
        self._current_music_channel: pygame.mixer.Channel | None = None
        self._volume = 0.8

        try:
            pygame.mixer.pre_init(SAMPLE_RATE, -16, 1, 512)
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self._available = True
        except Exception as exc:
            print(f"[SoundManager] pygame.mixer init failed: {exc}. "
                  "Running in silent mode.")
            return

        self._generate_all_sounds()
        self._generate_all_music()

    # ------------------------------------------------------------------
    # Internal generation
    # ------------------------------------------------------------------

    def _make_sound(self, samples):
        """Convert float sample list to a pygame.mixer.Sound at master volume."""
        sound = samples_to_sound(samples, SAMPLE_RATE)
        if sound is not None:
            sound.set_volume(self._volume)
        return sound

    def _generate_all_sounds(self):
        """Generate every sound effect and store it by name."""
        generators = {
            'light_hit':     _make_light_hit,
            'heavy_hit':     _make_heavy_hit,
            'special_hit':   _make_special_hit,
            'block_sound':   _make_block_sound,
            'whoosh':        _make_whoosh,
            'ko_sound':      _make_ko_sound,
            'menu_select':   _make_menu_select,
            'menu_confirm':  _make_menu_confirm,
            'round_start':   _make_round_start,
            'victory_fanfare': _make_victory_fanfare,
            'defeat_sound':  _make_defeat_sound,
            'syrup_splash':  _make_syrup_splash,
            'fire_blast':    _make_fire_blast,
            'freeze_sound':  _make_freeze_sound,
            'ground_pound':  _make_ground_pound,
            'rage_activate': _make_rage_activate,
        }
        for name, fn in generators.items():
            try:
                samples = fn(SAMPLE_RATE)
                sound   = self._make_sound(samples)
                if sound is not None:
                    self._sounds[name] = sound
            except Exception as exc:
                print(f"[SoundManager] Failed to generate '{name}': {exc}")

    def _generate_all_music(self):
        """Generate all music tracks and store them as Sound objects."""
        track_generators = {
            'fight': _generate_fight_music,
            'boss':  _generate_boss_music,
            'menu':  _generate_menu_music,
        }
        for name, fn in track_generators.items():
            try:
                samples = fn(SAMPLE_RATE)
                sound   = samples_to_sound(samples, SAMPLE_RATE)
                if sound is not None:
                    # Music plays at a lower volume than SFX
                    sound.set_volume(self._volume * 0.55)
                    self._music[name] = sound
            except Exception as exc:
                print(f"[SoundManager] Failed to generate music '{name}': {exc}")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def play_sound(self, sound_name: str):
        """Play a sound effect by name.

        Silently ignores unknown names or mixer unavailability.

        Args:
            sound_name: One of the registered sound effect names, e.g.
                        'light_hit', 'menu_select', 'fire_blast', etc.
        """
        if not self._available:
            return
        sound = self._sounds.get(sound_name)
        if sound is None:
            return
        try:
            sound.play()
        except Exception as exc:
            print(f"[SoundManager] play_sound('{sound_name}') error: {exc}")

    def play_music(self, track_name: str):
        """Start looping a music track.

        Stops any currently playing music before starting the new track.

        Args:
            track_name: One of 'fight', 'boss', or 'menu'.
        """
        if not self._available:
            return
        self.stop_music()
        sound = self._music.get(track_name)
        if sound is None:
            print(f"[SoundManager] Unknown music track: '{track_name}'")
            return
        try:
            channel = sound.play(loops=-1)  # -1 = loop forever
            self._current_music_channel = channel
        except Exception as exc:
            print(f"[SoundManager] play_music('{track_name}') error: {exc}")

    def stop_music(self, fade_ms: int = 500):
        """Fade out and stop the currently playing music track.

        Args:
            fade_ms: Fade-out duration in milliseconds (default 500 ms).
        """
        if not self._available:
            return
        if self._current_music_channel is not None:
            try:
                self._current_music_channel.fadeout(fade_ms)
            except Exception:
                pass
            self._current_music_channel = None
        # Also stop any music sounds that might be playing on other channels
        for sound in self._music.values():
            try:
                sound.stop()
            except Exception:
                pass

    def set_volume(self, volume: float):
        """Set the master volume for all sounds and music.

        Args:
            volume: A float in the range [0.0, 1.0]. Values outside this
                    range are clamped.
        """
        if not self._available:
            return
        self._volume = max(0.0, min(1.0, float(volume)))
        for sound in self._sounds.values():
            try:
                sound.set_volume(self._volume)
            except Exception:
                pass
        for sound in self._music.values():
            try:
                sound.set_volume(self._volume * 0.55)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Convenience properties (direct Sound access for custom usage)
    # ------------------------------------------------------------------

    @property
    def sounds(self) -> dict:
        """Read-only view of the generated sound effect dictionary."""
        return self._sounds

    @property
    def music_tracks(self) -> dict:
        """Read-only view of the generated music track dictionary."""
        return self._music

    @property
    def is_available(self) -> bool:
        """True if pygame.mixer initialized successfully."""
        return self._available
