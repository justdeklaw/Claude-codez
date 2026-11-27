# Ranking Channel – Production Workflow

Each video lives in `projects/<video-slug>/`:

```
projects/top-10-example/
  script.md        # title, hook, items #10 → #1, facts + sources
  shotlist.csv     # rank, item, search terms, clip URL, license, in/out times
  footage/         # downloaded raw clips (not committed – too large)
  voiceover/       # narration audio (one file per rank)
  graphics/        # rank cards, lower thirds, thumbnail
  output/          # final render (not committed)
```

## Pipeline

1. **Topic & research** – pick topic, gather facts with sources, choose ranking order.
2. **Script** – hook (first 15 s), intro, #N → #1 segments (~45–90 s each), outro/CTA.
3. **Shot list** – search terms per item; find clips on royalty-free libraries
   (Pexels, Pixabay, Wikimedia Commons, Internet Archive). Record license per clip.
4. **Download** – fetch clips via the library APIs into `footage/`.
5. **Voiceover** – your own recording, or AI text-to-speech.
6. **Edit (automated)** – ffmpeg/Python assembles: rank title cards → clips trimmed
   to narration length → captions → background music (ducked under voice) → 1080p export.
7. **Thumbnail & metadata** – thumbnail image, title, description with credits, tags, chapters.
8. **Review & upload** – you watch the render, request changes, then upload.

## Copyright rules
- Only royalty-free / Creative Commons / your own footage. Credit where required.
- No re-uploading clips from other YouTube videos, films or TV unless clearly fair use.
