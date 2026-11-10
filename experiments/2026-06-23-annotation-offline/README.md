# Phone-friendly (offline) annotation files

Self-contained copies of the annotation HTML that render math **with no
internet**. The original CDN-based files (in
`experiments/2026-06-19-dispatch-annotation/disp10/` and
`experiments/2026-06-18-pilot-annotation/`) go **blank on a phone** that is
offline, on flaky data, or whose mail/files preview blocks external resources —
because they fetch KaTeX + marked from a CDN. These versions inline KaTeX +
marked + the fonts (base64), so they work on any device with no network.

The originals are left in place; these are additional files.

## Contents

- `disp10/annotation_T01.html … annotation_T10.html` — the 10 teacher files (send these).
- `pilot/annotation_T01.html`, `annotation_T02.html` — pilot, for completeness.

Each file is ~840 KB (the inlined math libraries + fonts). They are **gitignored**
(regenerable, and large); regenerate with:

```
uv run python "experiments/2026-06-19-dispatch-annotation/build_dispatch_html.py" --offline
uv run python "experiments/2026-06-18-pilot-annotation/build_pilot_html.py" --offline
```

(omit `--offline` to write the original CDN versions to their original folders).

## How it works

`src/eval/relevance/annotation_html.py` with `offline=True` inlines the vendored
assets in `src/eval/relevance/_annotation_assets/` (KaTeX 0.16.9 + marked 12.0.2;
fonts embedded as `data:` URIs). Rendering also degrades gracefully: if for any
reason the libraries are unavailable, the questions still appear as plain text
(raw `$…$`) instead of a blank page.

## Sending to teachers

Same as before — one file per teacher (T01 → teacher 1, …), `T0x → name` map kept
private. Verified: no `script src` / `link href` to any URL, so nothing is
fetched at open time. Still best opened in a real browser (not an email preview).