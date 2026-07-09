# Text to Audio Online

Convert any blog post, article, or text into a natural-sounding MP3 audio file — instantly.

Paste a URL or raw text, pick a voice and language, and download the audio in seconds. Powered by Google Gemini 2.0 Flash for intelligent content extraction and Microsoft Edge TTS for 60+ natural voices across 19 languages.

[![Website](https://img.shields.io/badge/Website-text--to--audio--online.vercel.app-4f46e5?style=flat-square&logo=vercel)](https://text-to-audio-online.vercel.app)
[![Chrome Web Store](https://img.shields.io/badge/Chrome_Extension-Install_Free-4285F4?style=flat-square&logo=googlechrome&logoColor=white)](https://chromewebstore.google.com/detail/text-to-audio-online/dmomnogiakppmhhfdefoigmopahihmhn)
[![Privacy Policy](https://img.shields.io/badge/Privacy_Policy-View-gray?style=flat-square)](https://text-to-audio-online.vercel.app/privacy)

---

## Features

- **URL to Audio** — paste a blog URL; the tool fetches the content, cleans it, and converts it to speech
- **Text to Audio** — paste raw text directly for conversion
- **AI-Powered Summarization** — articles over 3,000 words are automatically condensed using Gemini 2.0 Flash while preserving key points
- **60+ Natural Voices** — powered by Microsoft Edge TTS with region-specific accents
- **19 Languages** — English, Spanish, French, German, Portuguese, Italian, Dutch, Russian, Japanese, Korean, Chinese, Arabic, Hindi, Turkish, Polish, Swedish, Indonesian, Vietnamese, and Thai
- **Google Sign-In** — secure authentication via Supabase Auth
- **10 Free Conversions Per Day** — daily quota resets at midnight UTC
- **Instant MP3 Download** — no waiting, no email; download plays in-browser and saves as MP3

---

## Chrome Extension

The Chrome extension brings the same conversion capability directly into your browser toolbar.

**Install:** [Text to Audio Online](https://chromewebstore.google.com/detail/text-to-audio-online/dmomnogiakppmhhfdefoigmopahihmhn)

### Extension Features

- One-click conversion of the current tab's URL
- Paste text directly (up to 5,000 characters)
- 3 English voice options: Jenny (US Female), Guy (US Male), Sonia (UK Female)
- Animated progress ring with color transition (indigo → green)
- Google Sign-In — opens the website for OAuth, session is pushed back to the extension automatically
- Same 10 conversions/day free tier

### How to Use the Extension

1. Click the extension icon in your browser toolbar
2. Sign in with Google (one-time setup)
3. The current page URL is auto-filled — or switch to the "Text" tab to paste content
4. Pick a voice from the dropdown
5. Click **Convert** and wait for the progress ring to complete
6. Play the audio inline or download the MP3

---

## How It Works

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐     ┌──────────┐
│  User Input │────▶│  Content Fetch   │────▶│   Gemini    │────▶│ Edge TTS │
│  (URL/Text) │     │  & Extraction    │     │ Summarize   │     │  to MP3  │
└─────────────┘     └──────────────────┘     └─────────────┘     └──────────┘
                                                                       │
                                                                       ▼
                                                               ┌──────────────┐
                                                               │ MP3 Download │
                                                               └──────────────┘
```

1. **Input** — user provides a blog URL or pastes text
2. **Fetch & Clean** — for URLs, the backend fetches the page HTML and uses BeautifulSoup to extract the article body
3. **Summarize** (if needed) — articles exceeding 3,000 words are condensed to ~2,500 words using Google Gemini 2.0 Flash, preserving the core message
4. **Text-to-Speech** — the text is converted to audio using Microsoft Edge TTS with the selected voice
5. **Deliver** — the MP3 is base64-encoded and returned to the client for instant playback and download

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python / Flask (single-file serverless function) |
| Hosting | Vercel (serverless) |
| AI Summarization | Google Gemini 2.0 Flash |
| Text-to-Speech | Microsoft Edge TTS (`edge-tts`) |
| Authentication | Supabase Auth (Google OAuth) |
| Database | Supabase (PostgreSQL) — conversion logs & quota tracking |
| Extension | Chrome Manifest V3 (vanilla JS, no build step) |

---

## Project Structure

```
blog-to-audio/
├── api/
│   └── index.py              # Backend: all routes, HTML, CSS, JS in one file
├── blog-to-audio-extension/   # Chrome Web Store extension
│   ├── manifest.json
│   ├── background.js          # Receives auth session from website
│   ├── popup.html             # Extension UI
│   └── popup.js               # Conversion logic, progress animation
├── blog-to-audio-edge/        # Microsoft Edge Add-ons version
├── blog-to-audio-opera/       # Opera Add-ons version
├── blog-to-audio-firefox/     # Firefox Add-ons version
│   ├── content.js             # Auth bridge (replaces externally_connectable)
│   └── background.js          # Uses browser.* API namespace
├── vercel.json                # Vercel routing config
├── requirements.txt           # Python dependencies
└── .env.example               # Required environment variables
```

---

## Supported Languages & Voices

| Language | Voices |
|----------|--------|
| English | Jenny, Aria, Guy, Christopher, Andrew, Emma, Brian (US), Sonia, Ryan (UK), Natasha (AU), Neerja (IN) |
| Español | Elvira, Álvaro (Spain), Dalia, Jorge (Mexico), Elena (Argentina) |
| Français | Denise, Henri (France), Sylvie, Antoine (Canada) |
| Deutsch | Katja, Conrad, Amala, Ingrid (Austria) |
| Português | Francisca, Antonio (Brazil), Raquel, Duarte (Portugal) |
| Italiano | Elsa, Isabella, Diego, Giuseppe |
| Nederlands | Colette, Fenna, Maarten |
| Русский | Svetlana, Dmitry |
| 日本語 | Nanami, Keita |
| 한국어 | SunHi, InJoon |
| 中文 | Xiaoxiao, Yunyang |
| العربية | Zariyah, Hamed |
| हिन्दी | Swara, Madhur |
| Türkçe | Emel, Ahmet |
| Polski | Agnieszka, Marek |
| Svenska | Sofie, Mattias |
| Bahasa Indonesia | Gadis, Ardi |
| Tiếng Việt | HoaiMy, NamMinh |
| ไทย | Premwadee, Niwat |

---

## Local Development

### Prerequisites

- Python 3.9+
- A [Google AI Studio](https://aistudio.google.com/) API key (for Gemini)
- A [Supabase](https://supabase.com/) project (for auth and quota tracking)

### Setup

```bash
# Clone the repository
git clone https://github.com/avirup-123/blog-to-audio.git
cd blog-to-audio

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your keys:
#   GEMINI_API_KEY=your_key
#   SUPABASE_URL=your_supabase_url
#   SUPABASE_SERVICE_KEY=your_supabase_service_key
#   SUPABASE_ANON_KEY=your_supabase_anon_key

# Run locally
python app.py
```

The app will be available at `http://localhost:5000`.

### Deploy to Vercel

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod
```

Add the same environment variables in your Vercel project settings.

---

## Browser Extension Variants

The extension is available (or pending review) for multiple browsers:

| Browser | Store | Auth Bridge |
|---------|-------|-------------|
| Chrome | [Chrome Web Store](https://chromewebstore.google.com/detail/text-to-audio-online/dmomnogiakppmhhfdefoigmopahihmhn) | `externally_connectable` + `chrome.runtime.sendMessage` |
| Edge | Microsoft Edge Add-ons (pending) | Same as Chrome |
| Opera | Opera Add-ons (pending) | Same as Chrome |
| Firefox | Firefox Add-ons (pending) | `content_scripts` + `window.postMessage` |

Firefox uses a different auth bridge because it doesn't support `externally_connectable`. A content script on the website domain listens for `window.postMessage` events and relays the auth session to the background script via `browser.runtime.sendMessage`.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Main website (serves HTML with embedded CSS/JS) |
| POST | `/convert` | Convert URL or text to MP3 (requires Bearer token) |
| GET | `/privacy` | Privacy policy page |
| GET | `/voices` | Returns available voices for a given language |

### POST /convert

```json
{
  "input_type": "url",
  "url": "https://example.com/blog/post",
  "voice": "en-US-JennyNeural",
  "lang": "en"
}
```

Response:

```json
{
  "audio_base64": "...",
  "filename": "blog-post.mp3",
  "word_count": 1200,
  "duration": "4:32",
  "condensed": false
}
```

---

## Privacy

This tool collects only what's necessary to function:

- **Google account email** — for authentication and quota tracking
- **Conversion logs** — URL or text snippet, timestamp, voice used (for quota enforcement)
- **No data is sold or shared** with third parties

Full privacy policy: [text-to-audio-online.vercel.app/privacy](https://text-to-audio-online.vercel.app/privacy)

---

## License

MIT
