# Part A — Recommendation memo

*Commit `fd3e481e89b59415a68867936ab60e0d233b0818-dirty` · generated `2026-09-07T05:05:40+00:00`.*

## Corrected headline numbers

Tokenizer `gpt2`, ratio to `eng`, macro:

| lang | per words | per graphemes | per codepoints | per utf8_bytes | per sentences ||---|---|---|---|---|---|| hin | 6.3219 | 11.3049 | 7.3867 | 2.8760 | 7.4214 || kan | 18.5018 | 19.6232 | 12.8429 | 4.7320 | 13.5877 || tam | 20.2911 | 20.3598 | 13.1582 | 4.8168 | 15.5366 || tel | 16.7358 | 22.2314 | 12.7723 | 4.7905 | 12.9708 || ben | 10.7982 | 15.4032 | 9.6276 | 3.6004 | 9.6054 || mar | 9.0288 | 12.7749 | 7.7061 | 2.8914 | 7.8638 |
## Routing recommendation

**Change the tokenizer; do not route Indic traffic to a separate model, and do
not budget a fixed multiple for serving cost.** Measured on the evaluation
corpus, per parallel sentence and relative to English: Hindi is
7.4214× under the tokenizer the v0 report used, and
1.1575× under an Indic-aware one. Tamil moves
15.5366× → 1.0588×; Bengali reaches
1.0012×. The premium is a property of the vocabulary and largely
disappears when the vocabulary changes, so provisioning against it would be
buying capacity to compensate for a tokenizer choice.

## Biggest caveat

The corpus is professionally translated news and encyclopaedic prose. It
contains no assistant chat register, no code-switching and no Latin-script
Indic — all of which are common in real traffic and none of which is
represented here. Because every sentence is a translation of a shared English
source, Indic phrasing is pulled toward English structure, which if anything
understates true divergence. These numbers are sound for the text they were
measured on and are not a forecast of production token cost.

## The one metric to monitor in production

**Median tokens per served request, segmented by language, expressed as a ratio
to English.** If that production ratio drifts away from the per-sentence ratios
above, the corpus has stopped representing traffic and every conclusion here
expires. It is the single number that catches this analysis being wrong,
because it fails in exactly the way the caveat predicts: real Indic traffic
being shorter, code-switched or Latin-script would move it without anything in
the tokenizer changing.
