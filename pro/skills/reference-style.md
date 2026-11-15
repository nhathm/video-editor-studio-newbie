# Reference style: learn a design language, apply it to the user's own videos

The user shows a sample video ("make mine in this style", a Facebook reel / YouTube / Shorts / TikTok link or a
file). Learn **how it looks and sounds**: fonts, colours, text treatments, motion, transitions, pace, framing and
light, music mood, sound effects. Then apply that to the user's own footage and words.

Never copy the sample: not its footage, music, voice, words, scene order or layout, and never judge how it was
made. A reference is a mood board, not a template.

## 1. Measure and lay out sheets

```bash
nve new <user files…> --name "<name>"     # or `nve new --name "<name>"` when only the sample exists yet
nve ref <project> <link|file>              # -> analysis/ref_r1.json + reference/r1/sheets/*.jpg
```

- Download: public videos only, never the user's accounts or cookies. If it fails (YouTube often blocks
  servers; private or age-limited videos), ask the user in one line to send the file.
- `ref_r1.json`: `pace` (cuts per minute, shot lengths, cut / jump / fade / flash), `hook_shot_s`, `aspect`,
  `shots`, and `audio`: voice present; `music` with `bpm` (+ half / double alternatives), `beat_strength`,
  `section_changes`, `no_beat`, and `character` (`brightness`, `drums`, `energy`, `mood_hint`); `cuts_on_beat`
  vs `beat_chance` and `beat_synced_edit`. nve cannot name the song or its genre: describe the feel.

## 2. Read the design language from the sheets

`overview.jpg` (whole video), `shots_N.jpg` (one frame per shot, 360 px), `strip_N.jpg` (8 fps over 1.5 s: entrances).

For each text role (title / caption / label): font look (geometric, humanist, condensed, serif, script),
weight, case, size as % of frame height, colour and keyword colour, outline, shadow, glow, box or pill,
position, words on screen at once, karaoke or not. Then the palette, motion (how text and graphics enter and
leave, how fast, camera moves), transitions and how often, framing / light / grade, and the sound (music mood,
energy, how loud under the voice, how many SFX and on what).

Then pick out 1–3 **signature moves**: devices that make the style recognisable (a wall of past videos
zooming in, a red stat screen, a keyword behind the person). Write when each one fits, so it is used only where
the user's own content gives a reason, never pasted in because the sample had it.

## 3. Write `analysis/style_dna.json` (schema `nve.style_dna/2`), check, save

- `style`: the tokens above. `signature_moves`: name, what, when it fits, the nve block that does it or `missing`.
- `apply`: what nve writes into a storyboard: `output` (e.g. speed), `style` (fonts from the pack: Montserrat,
  Be Vietnam Pro, Anton, Inter, Lexend, Nunito, Baloo 2, Playfair Display, Lora, Dancing Script, Pacifico;
  condensed heavy → Anton; palette; caption block and props; look; skin; green-screen background), `music`
  (`mood`, `volume`, `pick_from`: 1–3 tracks from `nve assets list bgm` whose mood tags match the `mood_hint`
  and energy), `stamp` defaults, `limits` (stamps / SFX per minute, as a density guide).
- `missing`: what nve cannot do yet; tell the user.

```bash
nve ref <project> --check          # validates the schema
nve style save <project> [name]    # -> <workspace>/custom/styles/<name>/style.json
nve ref <project> --clean          # ALWAYS right after saving: deletes the sample video and sheets
```

Tell the user in 2–3 plain lines what the style is (e.g. "chữ to kiểu Anton vàng/trắng, caption 2–3 chữ, nền
tối ấm, nhạc nhẹ ấm, cắt nhanh ở phần mở đầu") and what nve cannot do yet.

## 4. Apply a saved style to any video

```bash
nve plan draft <project>
nve style apply <project> <name>    # fonts, palette, caption, look, speed, music; the user's taste still wins
```

The result lists `signature_moves`, `stamp` defaults and `limits`: plan the overlays with the user's own words in
that style, and use a signature move only where their content calls for it. `nve style list` shows saved
styles ("dựng theo style Hana" → apply that one). At G1 say which style was applied.
