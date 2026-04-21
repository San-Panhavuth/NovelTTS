# Audiobook Website — Project Brief for Claude Code

## Project Summary

A web application focused on **Chinese and Korean light novels / web novels**. Users browse a default library of popular translated novels, or upload their own PDF/EPUB, and generate multi-voice audiobooks with distinct TTS voices per character, narration, and inner thoughts.

---

## Core Features

- **Default Novel Library**: curated list of popular CN/KR light novels shown on the homepage, sourced from free public APIs and translation sites
- **Book Import**: browse/search the default library or upload your own PDF/EPUB
- **Dialog Attribution**: automatically detect and tag each line as `NARRATION`, `DIALOGUE`, or `INNER_THOUGHT` with speaker identity using an LLM
- **Character Registry**: auto-build a list of detected characters per book
- **Voice Assignment**: user assigns a TTS voice to each character (changeable anytime)
- **Multi-Voice Audio Generation**: generate TTS audio per segment, stitch into chapter files
- **Audio Player**: stream and play generated chapters with waveform visualization

---

## Tech Stack (Current Thinking)

### Frontend
- Next.js 14 (App Router)
- Tailwind CSS + shadcn/ui
- Wavesurfer.js (audio player)
- React Query (API state)

### Backend
- FastAPI (Python)
- BullMQ + Redis (async job queue for TTS processing)
- PostgreSQL + Prisma (data)
- FFmpeg (audio stitching)

### AI / Processing
- **LLM for dialog tagging**: Gemini 1.5 Flash (free tier) or Ollama + Mistral (local/free)
- **TTS engine**: Kokoro TTS (free/self-hosted) → upgrade to ElevenLabs for production
- **File parsing**: PyMuPDF (PDF), ebooklib (EPUB)

### Storage & Hosting
- Supabase (PostgreSQL + file storage)
- Cloudflare R2 (audio file storage)
- Vercel (frontend)
- Render (backend)

---

## Light Novel APIs (Default Library Source)

> ⚠️ **Important reality**: There is no clean, official free REST API specifically for Chinese/Korean light novels with full chapter text. Modern translated novels are copyrighted. The practical options are:
> (a) use sites that allow scraping for personal/non-commercial use,
> (b) use metadata-only APIs and link out to source,
> (c) self-host a curated catalog of pre-scraped novels.

### Option 1: NovelUpdates (Metadata + Community Data) ⭐
- **URL**: `https://www.novelupdates.com`
- **What it is**: The largest English-language database of translated CN/KR/JP web novels — tens of thousands of series with ratings, genres, chapter counts, and translation group links
- **API**: No official public API. Use the unofficial scraper wrapper [`novelupdates.py`](https://github.com/jckli/novelupdates.py) or scrape their search/series pages directly
- **What you can get**: title, cover image, genres, tags, rating, status (ongoing/completed), language (CN/KR/JP), synopsis, chapter release links
- **Full text**: ❌ NovelUpdates is metadata only — it links out to actual translator sites for chapter text
- **Best use**: Power the homepage browser (search, filter by genre/language/rating), then link users to source or scrape chapter text from the linked translator site
- **Example series page**: `https://www.novelupdates.com/series/solo-leveling/`

### Option 2: lightnovel-crawler (Python Library) ⭐ Recommended for MVP
- **Repo**: `https://github.com/lncrawl/lightnovel-crawler`
- **What it is**: Open-source Python library that supports **300+ novel sites** including popular CN/KR sources. Acts as a unified scraping layer with source plugins
- **Supported sources include**: NovelFull, LightNovelWorld, WuxiaWorld, BoxNovel, MTLNovel, ReadLightNovel, and many more
- **Install**: `pip install lightnovel-crawler`
- **Usage**:
  ```python
  from lncrawl.core.app import App
  app = App()
  app.user_input = "https://www.novelfull.com/solo-leveling.html"
  app.initialize()
  app.search_novel()
  chapters = app.crawler.chapters   # list of chapter metadata
  text = app.crawler.download_chapter(chapters[0])  # full chapter text
  ```
- **Best use**: Use as the backend scraping engine. Pre-scrape and cache a curated catalog — do NOT do runtime scraping on user requests
- **Limitation**: dependent on site HTML structure; may break when source sites update

### Option 3: NovelFull / LightNovelWorld (Direct Scraping Fallback)
- **Sites**: `https://www.novelfull.com`, `https://www.lightnovelworld.com`
- **How to access**: `httpx` + `BeautifulSoup` (NovelFull is easier), `Playwright` for JS-heavy sites
- **LightNovelWorld**: uses Cloudflare — requires cookie rotation or Playwright with delays
- **Scraping notes**: always add 2–5 second delays between requests; respect `robots.txt`
- **Legal note**: only use for non-commercial/personal MVP; do not redistribute full text at scale

### Recommended Strategy

```
Homepage library browser   →  NovelUpdates metadata (title, cover, genre, rating)
Full chapter text          →  lightnovel-crawler scraping, stored in your own DB
Stable production catalog  →  Pre-scraped & cached (50-100 top novels) — no runtime scraping
User-uploaded books        →  PDF/EPUB upload flow (PyMuPDF / ebooklib)
```

### Suggested Default Library (Pre-scrape these first)

| Title | Origin | Genre | Status |
|-------|--------|-------|--------|
| Solo Leveling | Korean | Action / Fantasy | Completed |
| Omniscient Reader's Viewpoint | Korean | Action / Fantasy | Completed |
| The Beginning After the End | Korean | Fantasy / Isekai | Ongoing |
| Legendary Moonlight Sculptor | Korean | Fantasy / RPG | Completed |
| Lord of Mysteries | Chinese | Mystery / Steampunk | Completed |
| A Will Eternal | Chinese | Xianxia / Cultivation | Completed |
| I Shall Seal the Heavens | Chinese | Xianxia | Completed |
| The Legendary Mechanic | Chinese | Sci-Fi / RPG | Completed |
| Release That Witch | Chinese | Isekai / Kingdom Building | Completed |
| Reverend Insanity | Chinese | Xianxia / Dark | Completed |

### Data Model for Books

```typescript
Book {
  id,
  title,
  author,
  source: "scraped" | "upload",
  originLanguage: "CN" | "KR" | "JP",
  sourceUrl,           // original novel page URL
  coverUrl,
  synopsis,
  genres,              // ["Action", "Fantasy", "Xianxia", ...]
  status: "ongoing" | "completed",
  totalChapters,
  rating,
  scrapedAt,
  createdAt
}
```

---

## Character Intelligence System

### Overview

Before assigning any voice, the system automatically researches each character using wiki/fandom sources to build a **Character Profile**. This profile drives smart voice recommendations and prevents mismatches like a wise elderly sage being assigned a young child's high-pitched voice.

### Step 1 — Auto Character Research (Wiki/Fandom Scraping)

When a book is added to the system, a background job scrapes character information from community wikis:

**Sources to scrape (in order of priority)**:
```
1. Fandom wiki          →  https://{novel-name}.fandom.com/wiki/{character}
2. Novel-specific wikis →  Search "{novel title} wiki {character name}"
3. NovelUpdates chars   →  https://www.novelupdates.com/series/{slug}/ (character section)
4. Novel text itself    →  LLM extracts traits directly from first 5 chapters as fallback
```

**Scraping approach**:
- Use `httpx` + `BeautifulSoup` for static fandom pages
- Use `Playwright` for JS-rendered wikis
- Use Google Custom Search API (free tier: 100 queries/day) or DuckDuckGo scraping to find the right wiki URL for each character

**What to extract from the wiki**:
```python
CharacterProfile {
  name,
  aliases,           # ["Sung Jin-Woo", "Shadow Monarch"]
  age,               # "mid-20s", "ancient", "teenager"
  gender,            # "male" | "female" | "unknown"
  personality,       # ["cold", "stoic", "calculating", "loyal"]
  speechStyle,       # ["formal", "curt", "rarely speaks", "arrogant"]
  physicalTraits,    # ["tall", "dark eyes", "imposing presence"]
  role,              # "protagonist" | "antagonist" | "mentor" | "comic relief" | ...
  powerLevel,        # "weakest hunter" → "strongest being" (useful for tone shift)
  voiceNotes,        # free-text: "Deep, quiet, commanding. Never shouts."
  wikiSource,        # URL scraped from
  confidence,        # "high" | "medium" | "low" (how complete the wiki data was)
}
```

### Step 2 — LLM Voice Trait Mapping

After building the `CharacterProfile`, pass it to an LLM to produce a structured `VoiceRequirement`:

```python
SYSTEM_PROMPT = """
You are a voice casting director for an audiobook.
Given a character's profile, output ONLY JSON with these fields:

{
  "pitch": "very_low | low | medium | high | very_high",
  "age_group": "child | teen | young_adult | adult | middle_aged | elderly",
  "tone": "warm | cold | neutral | cheerful | menacing | gentle | authoritative",
  "pacing": "slow | measured | normal | quick | erratic",
  "energy": "low | calm | moderate | intense | explosive",
  "accent_notes": "string or null",
  "avoid": ["list of traits that would be WRONG for this character"],
  "rationale": "one sentence explaining the casting choice"
}

Examples of avoid:
- For a wise elderly elder: avoid ["high_pitch", "child", "very_high", "cheerful", "quick"]
- For a bubbly teenage girl: avoid ["very_low", "elderly", "menacing", "slow"]
"""
```

### Step 3 — Voice Scoring & Smart Recommendation

Each available TTS voice has pre-tagged metadata:

```typescript
Voice {
  id, provider, name, previewUrl,
  tags: {
    pitch: "low" | "medium" | "high",
    ageGroup: "child" | "teen" | "adult" | "elderly",
    tone: "warm" | "cold" | "neutral" | "authoritative" | ...,
    gender: "male" | "female" | "neutral",
    energy: "calm" | "moderate" | "intense"
  }
}
```

Voice scoring algorithm:
```python
def score_voice(voice: Voice, requirement: VoiceRequirement) -> float:
    score = 0
    # Hard disqualifiers — instant reject
    for bad_trait in requirement.avoid:
        if bad_trait in voice.tags.values():
            return -1  # DISQUALIFIED

    # Positive matches — add points
    if voice.tags.pitch == requirement.pitch: score += 3
    if voice.tags.age_group == requirement.age_group: score += 4  # weighted highest
    if voice.tags.tone == requirement.tone: score += 2
    if voice.tags.energy == requirement.energy: score += 2
    return score
```

The top 3 scored voices become the **Recommended Voices** shown to the user. The system never auto-assigns without user confirmation.

### Step 4 — Character Voice Dashboard (Per Novel)

Each novel gets a dedicated **Character Voice Dashboard** where users manage all voice assignments:

```
┌─────────────────────────────────────────────────────────┐
│  Solo Leveling — Character Voice Management             │
├──────────────────┬────────────────────────────────────  │
│  Sung Jin-Woo    │  🤖 AI Profile: Adult male, cold,    │
│  [Protagonist]   │  stoic, commanding, low energy       │
│                  │  ────────────────────────────────    │
│                  │  ⭐ Recommended:                     │
│                  │    1. [Deep Male - Calm]    ▶ preview │
│                  │    2. [Baritone - Cold]     ▶ preview │
│                  │    3. [Tenor - Measured]    ▶ preview │
│                  │  ────────────────────────────────    │
│                  │  🎙 Current: Deep Male - Calm ✓      │
│                  │  [Change Voice ▼] [Custom Preview]   │
├──────────────────┼────────────────────────────────────  │
│  Thomas Andre    │  🤖 AI Profile: Elderly male,        │
│  [Antagonist]    │  arrogant, booming, authoritative    │
│                  │  ⭐ Recommended: [Baritone - Cold]   │
│                  │  ⚠️  Avoid: high pitch, child, teen  │
└──────────────────┴────────────────────────────────────  │
```

**Dashboard features**:
- Character card shows: name, role, AI-generated personality summary, age group badge
- "⚠️ Avoid" warning chip showing disqualified voice traits
- Top 3 AI-recommended voices with one-click preview (plays a character-relevant sample sentence)
- "Override" mode: user can still browse ALL voices, but disqualified ones are greyed out with a warning tooltip ("This voice may not suit the character's age/personality")
- Voice conflict detector: warn if two main characters share the same voice
- "Re-research" button: re-scrape wiki and regenerate profile if data seems wrong

### Pronunciation Guide

Beyond voice selection, the system also builds a **Pronunciation Dictionary** per novel:

```python
PronunciationEntry {
  term,              # "Qi", "Cultivation", "Sung Jin-Woo", "Murim"
  type,              # "character_name" | "power_system" | "place" | "title"
  phonetic,          # IPA or simplified: "chee", "sung-jin-woo"
  notes,             # "Korean name, family name first"
  source,            # "wiki" | "community_consensus" | "llm_inferred"
}
```

Sources for pronunciation:
- Fandom wikis often have pronunciation guides in character infoboxes
- LLM infers from language of origin (Korean names, Chinese cultivation terms, etc.)
- SSML `<phoneme>` tags injected into TTS input to override default pronunciation

```xml
<!-- Example SSML for ElevenLabs/Azure -->
<speak>
  <phoneme alphabet="ipa" ph="sʌŋ dʒɪn uː">Sung Jin-Woo</phoneme>
  gathered his <phoneme alphabet="ipa" ph="tʃiː">Qi</phoneme> and struck.
</speak>
```

### Updated Data Models

```typescript
CharacterProfile {
  id, bookId, characterId,
  age,                  // "elderly" | "middle_aged" | "adult" | "teen" | "child"
  gender,               // "male" | "female" | "unknown"
  personality,          // string[] — ["cold", "stoic", "commanding"]
  speechStyle,          // string[] — ["curt", "formal", "rarely_speaks"]
  role,                 // "protagonist" | "antagonist" | "mentor" | "comic_relief" | "side"
  voiceNotes,           // free text from wiki
  wikiSource,           // URL
  confidence,           // "high" | "medium" | "low"
  scrapedAt
}

VoiceRequirement {
  id, characterId,
  pitch,                // "very_low" | "low" | "medium" | "high" | "very_high"
  ageGroup,             // "child" | "teen" | "young_adult" | "adult" | "middle_aged" | "elderly"
  tone,                 // "warm" | "cold" | "neutral" | "authoritative" | "cheerful" | "menacing"
  pacing,               // "slow" | "measured" | "normal" | "quick"
  energy,               // "low" | "calm" | "moderate" | "intense"
  avoid,                // string[] — hard disqualifiers
  rationale             // LLM explanation
}

Voice {
  id, provider, name, previewUrl,
  pitchTag, ageGroupTag, toneTag, genderTag, energyTag  // pre-tagged by admin
}

PronunciationEntry {
  id, bookId, term, type, phonetic, notes, source
}
```

---

## Processing Pipeline

```
Browse default library (pre-scraped catalog)  OR  Upload PDF/EPUB
        ↓                                               ↓
Fetch chapter text from DB cache               Extract text (PyMuPDF / ebooklib)
        └───────────────────┬───────────────────────────┘
                            ↓
           Chunk into ~500-word segments (at paragraph boundaries)
                            ↓
           LLM Attribution → JSON array of { text, type, character }
                            ↓
           Build Character Registry (list of all unique characters)
                            ↓
    ┌───────── Background: Character Research Pipeline ──────────┐
    │  Scrape Fandom/Wiki for each character                     │
    │         ↓                                                  │
    │  Build CharacterProfile (age, gender, personality, role)   │
    │         ↓                                                  │
    │  LLM → VoiceRequirement (pitch, tone, avoid list)          │
    │         ↓                                                  │
    │  Score all voices → Top 3 Recommendations per character    │
    │         ↓                                                  │
    │  Build PronunciationDictionary (names, power terms)        │
    └────────────────────────────────────────────────────────────┘
                            ↓
        User opens Character Voice Dashboard
        (reviews AI profiles, previews recommended voices, confirms/overrides)
                            ↓
           TTS Generation per segment (parallel BullMQ jobs)
           (inject SSML phoneme tags for pronunciation)
                            ↓
           FFmpeg stitch segments → chapter audio files
                            ↓
           Store on R2 → stream to frontend player
```

---

## Data Models (Draft)

```typescript
Book {
  id, title, author, source ("scraped" | "upload"), originLanguage, status, createdAt
}

Chapter {
  id, bookId, index, title, rawText, status
}

Segment {
  id, chapterId, index, text, type ("NARRATION" | "DIALOGUE" | "INNER_THOUGHT"),
  character, audioUrl, status
}

Character {
  id, bookId, name, traits, voiceId
}

Voice {
  id, provider ("kokoro" | "elevenlabs" | "google"), voiceId, name, previewUrl
}

AudioJob {
  id, segmentId, status ("queued" | "processing" | "done" | "failed"), retries, createdAt
}
```

---

## Key Concerns / Open Questions

1. **Dialog attribution accuracy** — LLM prompt needs heavy tuning; how do we handle ambiguous speakers?
2. **Wiki coverage gaps** — not every character in every novel has a fandom wiki page; LLM fallback from novel text must be robust
3. **Voice tag quality** — recommendation system is only as good as how well we pre-tag the Kokoro voices; needs careful manual tagging upfront
4. **Scraping stability** — source sites and fandom wikis change HTML; need monitors to detect breakage
5. **Copyright** — only use scraped content for non-commercial MVP; get proper licenses before monetizing
6. **TTS speed** — Kokoro on CPU is slow (~10-20 min/chapter); acceptable for MVP?
7. **Audio caching** — if user changes a voice mid-way, only regenerate affected segments
8. **Pronunciation accuracy** — SSML phoneme tags help but LLM-inferred phonetics may still be wrong; allow user correction
9. **User auth** — simple email/password with Supabase Auth, or OAuth (Google)?
10. **Billing model** — credits per chapter? subscription? free with ads?

---

## Ideas to Refine

- [ ] Should voice assignment happen before or after attribution? (currently: after)
- [ ] Allow users to manually edit/correct misattributed segments before generation
- [ ] Add emotion/tone control per segment type (e.g. dramatic pause for inner thoughts)
- [ ] Genre-aware voice suggestions (e.g. deep/powerful voice for cultivation novels)
- [ ] Collaborative features — share a book's voice configuration with others
- [ ] Mobile app version (React Native?)
- [ ] Background music / ambient sound layer per chapter

---

## Cost Estimate (Per Book, ~100k chars)

| Option | LLM Cost | TTS Cost | Total |
|--------|----------|----------|-------|
| Fully Free | $0 (Gemini Flash) | $0 (Kokoro) | $0 |
| Hybrid | $0 (Gemini Flash) | ~$30 (ElevenLabs) | ~$30 |
| Premium | ~$0.10 (Claude Haiku) | ~$30 (ElevenLabs) | ~$30.10 |

---

## Development Plan

### Phase 0 — Setup & Foundations *(Week 1)*
**Goal**: working dev environment, project skeleton, nothing user-facing yet

- [ ] Initialize monorepo: `frontend/` (Next.js), `backend/` (FastAPI)
- [ ] Set up PostgreSQL via Supabase (local dev + cloud instance)
- [ ] Set up Redis via local Docker or Upstash free tier
- [ ] Configure Cloudflare R2 bucket for audio storage
- [ ] Initialize Prisma schema with all base models (Book, Chapter, Segment, Character, Voice, AudioJob)
- [ ] Run first DB migration
- [ ] Set up environment variables and `.env.example`
- [ ] Configure linting and formatting (ESLint + Prettier for frontend, Ruff + Black for backend)
- [ ] Set up GitHub Actions CI: lint + type-check on every PR

**✅ Done when**: `docker-compose up` starts the full local stack with no errors

---

### Phase 1 — Book Catalog & Ingestion *(Week 2–3)*
**Goal**: users can browse the default CN/KR novel library and view book details

- [ ] Integrate `lightnovel-crawler` as a background scraping service
- [ ] Pre-scrape 10 novels from the suggested default library (metadata + all chapters)
- [ ] Store scraped books and chapters in PostgreSQL
- [ ] Build REST endpoints:
  - `GET /books` — paginated list (filter by genre, language, status, search)
  - `GET /books/{id}` — book detail + chapter list
  - `GET /books/{id}/chapters/{index}` — chapter raw text
- [ ] Build frontend: Homepage library grid (cover, title, author, genre tags, rating)
- [ ] Build frontend: Book detail page (synopsis, chapter list, start button)
- [ ] Add placeholder cover image fallback

**✅ Done when**: homepage shows 10 novels, clicking one shows its chapter list

---

### Phase 2 — Text Processing & Dialog Attribution *(Week 4–5)*
**Goal**: given chapter raw text, produce tagged segments with speaker labels

- [ ] Build text chunker: split chapter into ~500-word segments at paragraph boundaries
- [ ] Integrate Gemini 1.5 Flash (free tier) for LLM dialog attribution
- [ ] Design and iterate attribution prompt (output: `[{ text, type, character }]`)
- [ ] Build attribution pipeline: chunk → LLM → parse JSON → store Segments in DB
- [ ] Build character registry: extract unique character names across the whole book
- [ ] Add confidence scoring — flag ambiguous attributions for manual review
- [ ] Build REST endpoints:
  - `POST /books/{id}/chapters/{index}/process` — trigger attribution pipeline
  - `GET /books/{id}/characters` — list detected characters
  - `GET /books/{id}/chapters/{index}/segments` — list attributed segments
- [ ] Build frontend: Segment review UI — show tagged lines, allow user to correct type/character
- [ ] Test attribution accuracy on 3+ different novel styles (cultivation, romance, action)

**✅ Done when**: any chapter produces a correctable, tagged segment list

---

### Phase 3 — Character Intelligence & Voice System *(Week 6–7)*
**Goal**: system automatically researches characters and recommends personality-matched voices; users manage everything from a dashboard

**Character Research Pipeline**:
- [ ] Build wiki scraper: given character name + novel title, find and scrape the Fandom wiki page
- [ ] Use DuckDuckGo or Google Custom Search (free tier) to locate the correct wiki URL per character
- [ ] Parse wiki infoboxes and description sections to extract: age, gender, personality, role, speech style, physical traits
- [ ] Build fallback: if wiki not found, LLM extracts character traits directly from first 5 chapters of novel text
- [ ] Build `CharacterProfile` model and storage
- [ ] LLM prompt: given `CharacterProfile`, output `VoiceRequirement` JSON (pitch, age_group, tone, pacing, energy, avoid list, rationale)
- [ ] Store `VoiceRequirement` per character in DB

**Voice Tagging & Scoring**:
- [ ] Pre-tag all available Kokoro voices with metadata: pitch, ageGroup, tone, gender, energy
- [ ] Build voice scoring function: score each voice against a `VoiceRequirement`, hard-reject voices in the `avoid` list
- [ ] Return top 3 recommended voices per character (ranked by score)
- [ ] Generate preview audio samples for all Kokoro voices, upload to R2

**Pronunciation Dictionary**:
- [ ] Scrape pronunciation notes from wiki character infoboxes
- [ ] LLM infers phonetics for Korean/Chinese names and cultivation terms (Qi, Dantian, murim, etc.)
- [ ] Store `PronunciationEntry` records per book
- [ ] Build SSML injector: wrap known terms in `<phoneme>` tags before sending to TTS

**Character Voice Dashboard (Frontend)**:
- [ ] Build per-novel `/dashboard/[bookId]/voices` page
- [ ] Character card layout: name, role badge, age group badge, AI-generated personality summary
- [ ] Show "⚠️ Avoid" chips for disqualified voice traits
- [ ] Show top 3 recommended voices with one-click preview player (plays a sample line)
- [ ] "Change Voice" dropdown: full voice browser with disqualified voices greyed out + tooltip warning
- [ ] Voice conflict warning: badge/alert if two main characters share the same voice
- [ ] "Re-research" button: re-trigger wiki scrape + LLM profile for a character
- [ ] Manual override: user can edit the AI-generated personality notes if wiki data is wrong

**REST Endpoints**:
- [ ] `GET /books/{id}/characters` — list with profiles + voice requirements + recommendations
- [ ] `POST /books/{id}/characters/{charId}/research` — trigger wiki research job
- [ ] `GET /voices?characterId={id}` — scored + ranked voices for a character
- [ ] `POST /books/{id}/characters/{charId}/voice` — confirm voice assignment
- [ ] `GET /books/{id}/pronunciation` — pronunciation dictionary

**✅ Done when**: dashboard shows all characters with AI profiles, recommended voices, and user can confirm/change assignments with appropriate warnings

---

### Phase 4 — TTS Audio Generation *(Week 8–9)*
**Goal**: generate full chapter audio from attributed segments using assigned voices

- [ ] Set up BullMQ job queue (Redis-backed) with a dedicated TTS worker process
- [ ] Build TTS worker: dequeue segment job → call Kokoro TTS → save audio chunk to R2
- [ ] Build audio stitcher: FFmpeg concatenates all segment chunks → final chapter `.mp3`
- [ ] Upload final chapter audio to R2, store URL in DB
- [ ] Build REST endpoints:
  - `POST /books/{id}/chapters/{index}/generate` — enqueue generation jobs
  - `GET /jobs/{jobId}/status` — poll progress
- [ ] Implement WebSocket endpoint for real-time generation progress updates to frontend
- [ ] Implement audio caching: skip re-generation for unchanged voice + text segments
- [ ] Add retry logic: max 3 retries for failed TTS segments, then mark as error
- [ ] Build frontend: "Generate Audio" button + real-time progress bar via WebSocket

**✅ Done when**: clicking Generate Audio produces a playable `.mp3` for a chapter

---

### Phase 5 — Audio Player & Playback UX *(Week 10)*
**Goal**: polished, enjoyable listening experience

- [ ] Integrate Wavesurfer.js waveform player
- [ ] Build player controls: play/pause, seek, playback speed (0.75x–2x)
- [ ] Add chapter navigation: previous/next chapter buttons
- [ ] Sync current segment text highlight with audio playback position
- [ ] Save and restore playback position per user per book (resume where left off)
- [ ] Build reading-mode view: text on left, player controls fixed at bottom

**✅ Done when**: user can listen to a full chapter with text sync and resume support

---

### Phase 6 — User Auth & PDF/EPUB Upload *(Week 11)*
**Goal**: user accounts and ability to bring your own books

- [ ] Set up Supabase Auth (email/password + Google OAuth)
- [ ] Add `userId` foreign key to Book and voice assignment models
- [ ] Protect all write endpoints with JWT auth middleware (FastAPI dependency)
- [ ] Build PDF upload endpoint: receive file → PyMuPDF extraction → store chapters in DB
- [ ] Build EPUB upload endpoint: ebooklib extraction → chapter detection → store in DB
- [ ] Handle malformed EPUB HTML: strip tags, decode entities, normalize whitespace
- [ ] Enforce file size limit (50MB max) and MIME type validation
- [ ] Build frontend: Upload page with drag-and-drop zone for PDF/EPUB
- [ ] Build frontend: Auth pages (sign up, log in, forgot password)

**✅ Done when**: logged-in users can upload their own novel and process it end-to-end

---

### Phase 7 — Polish, Reliability & Testing *(Week 12–13)*
**Goal**: production-grade stability, error handling, and test coverage

- [ ] Add global error boundary and user-friendly toast notifications in frontend
- [ ] Add loading skeletons for all async data states
- [ ] Add DB query indexes on: `bookId`, `chapterId`, `status`, `userId`
- [ ] Implement rate limiting on all scraping-related endpoints
- [ ] Add scraper health monitor: detect when source site HTML structure has changed
- [ ] Add basic admin panel: view books, job queue status, error logs
- [ ] Write unit tests for: text chunker, LLM response JSON parser, audio stitcher, voice scoring function
- [ ] Write unit tests for: CharacterProfile extractor, VoiceRequirement mapper, SSML phoneme injector
- [ ] Write integration tests for: wiki scraping pipeline, character research job queue, TTS generation
- [ ] Load test: simulate 10 concurrent chapter generation jobs and verify queue stability
- [ ] Fix any performance bottlenecks discovered during load testing

**✅ Done when**: full test suite passes; 10 concurrent jobs complete without errors

---

### Phase 8 — Deployment & Launch *(Week 14–15)*
**Goal**: live on the internet, monitored, and seeded with full content

- [ ] Deploy frontend to Vercel (connect GitHub repo, configure env vars)
- [ ] Deploy backend to Render (Dockerfile, configure env vars)
- [ ] Run DB migrations on production Supabase instance
- [ ] Configure production Redis on Upstash
- [ ] Set Cloudflare R2 CORS policy to allow requests from frontend domain
- [ ] Set up error monitoring (Sentry free tier)
- [ ] Set up uptime monitoring (Better Uptime or UptimeRobot free tier)
- [ ] Pre-scrape and seed production DB with full 50–100 novel default catalog
- [ ] Smoke test all critical user flows on production environment
- [ ] Configure custom domain + SSL

**✅ Done when**: app is live, monitored, and accessible to real users 🚀

---

## MVP Scope (Phases 1–4 only — validate core loop first)

1. Pre-scrape 5 novels into DB (no runtime scraping needed)
2. Display them on homepage — user picks one
3. Run LLM attribution on one chapter
4. Show character list + basic voice assignment UI
5. Generate audio for that chapter with Kokoro TTS
6. Play audio with a plain HTML5 `<audio>` element (no Wavesurfer yet)

**Core loop proven = proceed to Phase 5+**

---

## Notes for Claude Code

- Work strictly phase by phase — do not skip ahead or build Phase 5 features during Phase 2
- Abstract book source behind a `BookProvider` interface: `ScrapedProvider`, `UploadProvider`
- Abstract TTS behind a `TTSProvider` interface: `KokoroProvider`, `ElevenLabsProvider`
- Abstract character research behind a `WikiProvider` interface: `FandomProvider`, `LLMFallbackProvider`
- Prefer Python (FastAPI) for backend — better ecosystem for AI/scraping/TTS
- Never do runtime scraping in the critical user request path — always serve from DB cache
- All LLM prompts must request JSON-only output; always wrap JSON parsing in try/catch with a fallback
- The voice scoring `avoid` list is a HARD disqualifier — never recommend a disqualified voice even if it scores well on other dimensions
- Log everything in the TTS job pipeline — async audio debugging is impossible without logs
- Character research jobs run in the background after book ingestion — never block the user waiting for wiki scraping
- Use free-tier services during development; document the upgrade path for each service
- Prioritize dialog attribution accuracy and character intelligence over UI polish in early phases
- Pre-tag ALL voices with metadata before launch — the recommendation system is useless without it
