# Product Requirements: NovelTTS

## Vision
Make any English-translated web novel listenable as a multi-voice audiobook, with each character speaking in a distinct voice that matches their personality — generated in under 10 minutes per chapter on a CUDA GPU.

## Target User
Web novel readers (CN / KR / JP translations) who:
- Want to consume novels hands-free during commutes, workouts, or chores
- Find single-voice TTS monotonous and immersion-breaking
- Are comfortable uploading their own EPUB files

## MVP Scope (Phases 1–4)
1. EPUB upload + chapter parsing
2. LLM-based dialog attribution (narration / dialogue / inner thought + speaker)
3. LLM-based character profile + voice recommendation (no wiki scraping)
4. Manual voice assignment per character (with greyed-out disqualified voices)
5. Multi-voice TTS generation + chapter stitching
6. Plain HTML5 `<audio>` player (Wavesurfer in Phase 5)

## Out of Scope (for MVP)
- PDF / TXT support (EPUB only)
- Default scraped catalog (upload-only)
- Wiki / Fandom character research
- Background music or ambient layers
- Mobile app
- Collaborative voice configs
- Billing / monetization

## Key User Flows
1. **Sign up & upload**: Google OAuth → drag EPUB into upload zone → chapter list appears
2. **Process chapter**: pick chapter → "Process" → backend chunks + attributes → segment list appears
3. **Assign voices**: open Character Voice Dashboard → review AI profiles → pick from top-3 recommendations or override
4. **Generate audio**: click "Generate" → progress bar (WebSocket) → MP3 plays inline
5. **Listen**: play, pause, seek, change speed; resume position saved per book

## Success Criteria
- Upload → first listenable chapter in **< 15 min on CUDA GPU**
- Dialog attribution **≥ 85% accuracy** on a curated 5-chapter fixture set
- Voice recommendation top-3 contains the user's eventual choice **≥ 70%** of the time
- Zero re-generation needed when voice assignment is unchanged (cache hit on `(voice_id, text_hash)`)

## Stack Decisions (locked)
| Decision | Choice | Why |
|---|---|---|
| Frontend | Next.js 14 + Tailwind + shadcn | Standard, fast iteration |
| Backend | FastAPI | Best Python AI / scraping ecosystem |
| LLM | Gemini 2.5 Flash | Free tier, fast, good JSON adherence |
| TTS | Kokoro (CUDA) + Edge TTS | Free, ~310 voices total, GPU-fast |
| Auth | Supabase Auth | DB + Auth in one vendor |
| Storage | Cloudflare R2 | Cheap egress for audio streaming |
| File format | EPUB only | Cleanest parsing path |
| Languages | English only | Simplifies voice tagging |
| Char research | LLM from text | Wikis don't exist for arbitrary uploads |

## Open Questions
- Confidence threshold for flagging ambiguous speaker attributions for manual review?
- Pronunciation: SSML `<phoneme>` only, or also a user-correctable dictionary UI in MVP?
- Per-user rate limiting to protect Gemini / Edge TTS free tiers?
- How many concurrent generation jobs per user before back-pressure?
