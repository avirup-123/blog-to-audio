import argparse
import asyncio
import os
import re
import sys

import edge_tts
from google import genai
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# --------------- Configurable Variables ---------------
TTS_VOICE = "en-US-JennyNeural"
WORD_COUNT_THRESHOLD = 3000
CONDENSED_TARGET_WORDS = 2500
OUTPUT_DIR = "output"
# ------------------------------------------------------

load_dotenv()

SYMBOL_MAP = {
    "&": " and ",
    "%": " percent ",
    "→": " to ",
    ">": " greater than ",
    "<": " less than ",
}

ABBREVIATION_MAP = {
    "e.g.": "for example",
    "i.e.": "that is",
    "etc.": "and so on",
    "vs.": "versus",
    "approx.": "approximately",
}


def fetch_article(url: str) -> str:
    print(f"Fetching URL: {url}")
    resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    for tag in soup.find_all(
        ["nav", "header", "footer", "aside", "form", "script", "style", "noscript"]
    ):
        tag.decompose()

    selectors_to_remove = [
        ".author-bio", ".author-info", ".byline",
        ".related-posts", ".related-articles",
        ".cta", ".call-to-action",
        ".social-share", ".share-buttons",
        ".comments", "#comments", ".comment-section",
        ".cookie-banner", ".cookie-notice",
        ".breadcrumb", ".breadcrumbs",
        ".sidebar",
    ]
    for selector in selectors_to_remove:
        for el in soup.select(selector):
            el.decompose()

    article = (
        soup.find("article")
        or soup.find("div", class_=re.compile(r"(article|post|entry|content)-?(body|content|text)", re.I))
        or soup.find("div", {"role": "main"})
        or soup.find("main")
    )

    if article:
        return article.get_text(separator="\n")
    return soup.body.get_text(separator="\n") if soup.body else soup.get_text(separator="\n")


def get_manual_input() -> str:
    print("Paste your blog content below.")
    print("When done, press Enter, then type END on a new line, and press Enter again.\n")
    lines = []
    for line in sys.stdin:
        if line.strip() == "END":
            break
        lines.append(line)
    return "".join(lines)


def clean_text(raw: str) -> str:
    text = BeautifulSoup(raw, "html.parser").get_text(separator="\n")

    # Truncate at FAQ section
    faq_pattern = re.compile(r"(?:FAQ|FAQs|Frequently\s+Asked\s+Questions)", re.IGNORECASE)
    faq_match = faq_pattern.search(text)
    if faq_match:
        text = text[:faq_match.start()].rstrip()

    text = re.sub(r"[*_`#]", "", text)
    text = re.sub(r"---+", "", text)

    for symbol, word in SYMBOL_MAP.items():
        text = text.replace(symbol, word)

    for abbr, expansion in ABBREVIATION_MAP.items():
        text = text.replace(abbr, expansion)

    def replace_list_block(match: re.Match) -> str:
        block = match.group(0)
        items = re.findall(r"(?:^|\n)\s*(?:[-•*]|\d+[.)]) *(.*)", block)
        if not items:
            return block
        ordinals = ["First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth", "Ninth", "Tenth"]
        parts = []
        for i, item in enumerate(items):
            prefix = ordinals[i] if i < len(ordinals) else f"Next"
            if i == len(items) - 1 and len(items) > 1:
                prefix = "Finally"
            parts.append(f"{prefix}, {item.strip()}.")
        return " ".join(parts)

    text = re.sub(
        r"((?:^|\n)\s*(?:[-•*]|\d+[.)]) +.+(?:\n\s*(?:[-•*]|\d+[.)]) +.+)*)",
        replace_list_block,
        text,
    )

    lines = text.split("\n")
    processed = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            processed.append("")
            continue
        if len(stripped.split()) <= 12 and stripped == stripped.rstrip(".!?") and not any(c in stripped for c in ".,;:"):
            if stripped[0].isupper() and processed and processed[-1] == "":
                stripped = f"Now, let's talk about {stripped}."
        processed.append(stripped)

    text = "\n".join(processed)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"  +", " ", text)
    return text.strip()


def word_count(text: str) -> int:
    return len(text.split())


def condense_with_gemini(text: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found in .env file.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    prompt = (
        f"Condense the following article to approximately {CONDENSED_TARGET_WORDS} words.\n\n"
        "Rules:\n"
        "- Preserve every key point, all details, data points, statistics, steps, and important information\n"
        "- Remove only filler phrases, redundant sentences, decorative transitions, and repetitive content\n"
        "- Do not remove any section entirely unless it contains zero informational value\n"
        "- Maintain the logical flow and structure of the original article\n"
        "- Return only the condensed article text, no commentary or explanation\n\n"
        f"Article:\n{text}"
    )

    print("Sending to Gemini for condensation...")
    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    return response.text


def slug_from_url(url: str) -> str:
    path = url.rstrip("/").split("/")[-1]
    path = path.split("?")[0].split("#")[0]
    return sanitize_slug(path)


def sanitize_slug(slug: str) -> str:
    slug = slug.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


async def generate_audio(text: str, output_path: str) -> None:
    print(f"Generating audio with voice: {TTS_VOICE}")
    communicate = edge_tts.Communicate(text, TTS_VOICE)
    await communicate.save(output_path)


def estimate_duration(wc: int) -> str:
    seconds = int(wc / 150 * 60)
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}m {secs}s"


def main():
    parser = argparse.ArgumentParser(description="Convert blog posts to audio MP3 files.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", help="URL of the blog post to convert")
    group.add_argument("--manual", action="store_true", help="Paste blog content manually")
    args = parser.parse_args()

    # --- Input ---
    if args.url:
        input_source = f"URL: {args.url}"
        try:
            raw_text = fetch_article(args.url)
        except Exception as e:
            print(f"ERROR fetching URL: {e}")
            print("Try running with --manual to paste the content instead.")
            sys.exit(1)
        slug = slug_from_url(args.url)
    else:
        input_source = "Pasted text"
        raw_text = get_manual_input()
        if not raw_text.strip():
            print("ERROR: No content was provided.")
            sys.exit(1)
        slug_input = input("Enter a filename slug for this audio file (e.g. my-blog-post-title): ")
        slug = sanitize_slug(slug_input)
        if not slug:
            print("ERROR: Invalid slug.")
            sys.exit(1)

    # --- Clean ---
    print("Cleaning text for audio...")
    cleaned = clean_text(raw_text)
    wc = word_count(cleaned)
    print(f"Word count after cleaning: {wc}")

    # --- Condense if needed ---
    condensed = False
    final_text = cleaned
    if wc > WORD_COUNT_THRESHOLD:
        try:
            final_text = condense_with_gemini(cleaned)
            condensed = True
        except Exception as e:
            print(f"ERROR during Gemini condensation: {e}")
            sys.exit(1)

    final_wc = word_count(final_text)

    # --- Generate audio ---
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, f"{slug}.mp3")
    asyncio.run(generate_audio(final_text, output_path))

    # --- Summary ---
    print("\n--- Summary ---")
    print(f"Input source:        {input_source}")
    print(f"Word count (cleaned): {wc}")
    print(f"Condensation applied: {'Yes' if condensed else 'No'}")
    if condensed:
        print(f"Word count (condensed): {final_wc}")
    print(f"Estimated duration:  {estimate_duration(final_wc)}")
    print(f"Output file:         {output_path}")
    print("Done.")


if __name__ == "__main__":
    main()
