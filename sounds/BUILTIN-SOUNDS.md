# Built-in reminder sounds

Three stages only. The third stage repeats at the configured interval until a blink.

- Polite (audition 65) and Sharp (audition 79): akx notification sounds, CC0 option; see akx-LICENSE.md. Stages use 0/3/7 semitone pitch offsets, 1/.78/.60 tempo, and .30/.38/.46 peak amplitude. Each cue is one transformed original, not repeated beeps.
- Ding (internal asset key: original): exact original Dryless alert0.wav, alert1.wav, alert2.wav. Preserved without pitch or duration changes.
- Blip: exact previously auditioned three-stage files derived from BreakTimer app/renderer/public/sounds/blip_start.wav, commit b8156788e54e5f3f81cb6d232239bfcfb975bfd7; GPL-3.0, see breaktimer-LICENSE.md. Stages 0/3/7 semitones, durations approximately .714/.915/1.187 seconds.
- Microbreak: Workrave ui/data/sounds/subtle/micro-break-started.wav, commit 0ce618303e09c0d006ddcda8e29240786661805a; GPL-3.0, see workrave-COPYING and workrave-LICENSES.md. Exact source audio, fixed independently of the blink sound selection.

Audio is bundled locally. Selecting a family previews its first stage once. Play all 3 plays stages one through three with an .8-second gap. Microbreak audio preempts previews and blink audio; all playback shares one channel.
