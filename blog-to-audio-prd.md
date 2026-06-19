# Product Requirements Document
## Blog-to-Audio Agent

---

## 1. Project Overview

A local CLI tool that accepts a blog post as input, processes it into clean audio-ready text, converts it to a natural-sounding MP3 file using a free neural TTS engine, and saves the output for manual upload to a Drupal website.

The tool is built and run inside Claude Code using Python.

---

## 2. Goals

- Convert existing and newly published blog posts into MP3 audio files
- Audio must sound natural and human, not robotic
- Keep all tooling free or near-zero cost
- Keep the workflow simple enough to run manually per article

---

## 3. Tech Stack

| Layer | Tool | Version / Notes |
|---|---|---|
| Language | Python | 3.10 or higher |
| URL scraping | requests + BeautifulSoup4 | Latest stable |
| Content processing | Google Gemini API | Gemini 2.0 Flash via Google AI Studio free tier |
| Text-to-Speech | edge-tts | Latest stable — uses Microsoft Neural voices, free, no API key |
| Output format | MP3 | 24kHz, standard web audio |

### API Keys Required
- **Gemini API key** from Google AI Studio (`aistudio.google.com`) — free tier, no billing setup needed

---

## 4. Input

The tool supports two input methods. Both are treated as primary options and must work independently.

**Method 1 — URL**
The user provides a blog post URL. The tool fetches and extracts the article content automatically.

**Method 2 — Manual text input**
The user pastes the blog content directly into the terminal when prompted. The tool must launch an interactive multi-line input mode where the user can paste the full text and then signal when they are done. This is useful for drafts, staging content, or cases where URL scraping does not work correctly.

No file upload support is required at this stage.

**CLI usage pattern:**
```
# URL input
python blog_to_audio.py --url "https://example.com/blog/post-slug"

# Manual text input — launches interactive paste mode in the terminal
python blog_to_audio.py --manual
```

When `--manual` is used, the tool prints the following prompt and waits for input:

```
Paste your blog content below.
When done, press Enter, then type END on a new line, and press Enter again.
```

The user pastes the full blog text, then types `END` on a new line to signal completion. The tool then proceeds with the pasted content exactly as it would with URL-extracted content.

---

## 5. Functional Requirements

### FR1 — URL Content Extraction

Applies only when `--url` is used.

- Fetch the full page HTML using `requests`
- Parse with `BeautifulSoup4`
- Extract only the article body content
- Strip all of the following before processing: navigation menus, page header, page footer, sidebar, author bio section, related posts section, CTA blocks, social share buttons, comment sections, cookie banners, and breadcrumbs

The Drupal article body is consistently structured. Target the main content container.

### FR1b — Manual Text Input Handling

Applies only when `--manual` is used.

- Launch interactive multi-line input mode in the terminal
- Display the paste prompt as specified in Section 4
- Collect all lines until the user types `END` on a new line
- Use the collected text as-is and pass it directly to FR2 for cleaning
- No scraping or HTML parsing is performed

### FR2 — Content Cleaning for Audio

After extraction, the text must be cleaned and reformatted so it sounds natural when spoken. The following transformations must be applied:

- Remove any remaining HTML tags
- Convert symbols to words: `&` → "and", `%` → "percent", `→` → "to", `>` → "greater than", `<` → "less than"
- Expand common abbreviations where possible: `e.g.` → "for example", `i.e.` → "that is", `etc.` → "and so on", `vs.` → "versus", `approx.` → "approximately"
- Convert bullet point lists and numbered lists into naturally spoken sequences using transitional phrases: "First...", "Second...", "Third...", "Finally..."
- Convert section headings from title-style text into verbal transition phrases that introduce the section naturally, suitable for spoken audio
- Preserve paragraph breaks as natural pause points
- Remove markdown formatting characters (`**`, `_`, `#`, `---`, backticks)
- Normalize multiple spaces and line breaks

### FR3 — Word Count Assessment

After cleaning, count the words in the processed text and apply the following logic:

- **3,000 words or fewer** → proceed to TTS with the full cleaned text, no condensation
- **More than 3,000 words** → send to Gemini API for intelligent condensation before TTS

The 3,000-word threshold is based on approximately 20 minutes of audio at natural reading pace, which is the upper limit for a blog page embed.

### FR4 — Intelligent Condensation via Gemini API

This step only runs when the word count exceeds 3,000 words.

Send the cleaned text to Gemini 2.0 Flash with the following instruction:

- Preserve every key point, all details, data points, statistics, steps, and important information
- Remove only filler phrases, redundant sentences, decorative transitions, and repetitive content
- Do not remove any section entirely unless it contains zero informational value
- Maintain the logical flow and structure of the original article
- Target output is approximately 2,500 words
- Return only the condensed article text, no commentary or explanation

### FR5 — Audio Generation

Pass the final processed text (either full or condensed) to `edge-tts` for speech synthesis.

Default voice: `en-US-JennyNeural`

Output format: MP3 at 24kHz

The voice selection should be configurable via a variable at the top of the script so it can be changed without modifying logic.

### FR6 — Output File Naming

The output MP3 file must be named after the blog post slug.

- If input is a URL, extract the slug from the URL path automatically
- If input is manual text, prompt the user to type a slug after they finish pasting and before generation begins: `Enter a filename slug for this audio file (e.g. my-blog-post-title):`
- Sanitize the slug: lowercase, replace spaces with hyphens, remove special characters

File naming format: `{blog-slug}.mp3`

Example: `how-to-get-a-trade-license-in-dubai.mp3`

All output files are saved to an `/output` folder in the project directory. Create the folder automatically if it does not exist.

### FR7 — Console Logging

After each successful run, print the following to the console:

- Input source (URL or pasted text)
- Word count of the cleaned text
- Whether condensation was applied (yes/no)
- Word count after condensation (if applicable)
- Estimated audio duration in minutes and seconds
- Output file path

---

## 6. Non-Functional Requirements

- **Cost:** Gemini API usage on the free tier handles up to 1,500 requests per day. At 2–3 articles per month the tool will never approach this limit. edge-tts is free with no limits. Total running cost should be zero.
- **Audio quality:** 24kHz MP3, which is the standard for voice content delivered over the web and matches edge-tts default output.
- **Speed:** A 1,500-word article should complete end to end in under 60 seconds on a standard machine.
- **Portability:** The tool runs entirely locally inside Claude Code. No server, no deployment, no external services beyond the two API calls.
- **Error handling:** If the URL fetch fails, print a clear error and prompt the user to paste the content instead. If the Gemini API call fails, print the error and stop before attempting TTS.

---

## 7. Out of Scope

The following are explicitly out of scope for this build and should not be implemented:

- Any frontend UI or web interface
- Drupal integration or automatic file upload
- Audio player embedding or HTML generation
- Automated triggers on Drupal publish events
- Batch processing of multiple URLs in one run
- Any audio format other than MP3
- Voice cloning or custom voice training
- Scheduled or background job execution

---

## 8. Project File Structure

```
blog-to-audio/
├── blog_to_audio.py       # Main CLI script
├── requirements.txt       # Python dependencies
├── .env                   # API keys (GEMINI_API_KEY)
├── .env.example           # Template for .env
├── /output                # Generated MP3 files (auto-created)
└── README.md              # Setup and usage instructions
```

---

## 9. Dependencies (requirements.txt)

```
requests
beautifulsoup4
google-generativeai
edge-tts
python-dotenv
```

---

## 10. Environment Variables (.env)

```
GEMINI_API_KEY=your_google_ai_studio_api_key_here
```

---

## 11. Configurable Variables (top of script)

The following should be defined as constants at the top of `blog_to_audio.py` so they can be changed without touching the logic:

```python
TTS_VOICE = "en-US-JennyNeural"
WORD_COUNT_THRESHOLD = 3000
CONDENSED_TARGET_WORDS = 2500
OUTPUT_DIR = "output"
```
