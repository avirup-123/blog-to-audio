import asyncio
import os
import re
import sys

import edge_tts
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, send_from_directory
from google import genai
import requests as http_requests

load_dotenv()

# --------------- Configurable Variables ---------------
TTS_VOICE = "en-US-JennyNeural"
WORD_COUNT_THRESHOLD = 3000
CONDENSED_TARGET_WORDS = 2500
OUTPUT_DIR = "output"
# ------------------------------------------------------

app = Flask(__name__)

SYMBOL_MAP = {
    "&": " and ",
    "%": " percent ",
    "→": " to ",
}

ABBREVIATION_MAP = {
    "e.g.": "for example",
    "i.e.": "that is",
    "etc.": "and so on",
    "vs.": "versus",
    "approx.": "approximately",
}


def fetch_article(url: str) -> str:
    resp = http_requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
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
            prefix = ordinals[i] if i < len(ordinals) else "Next"
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
        raise ValueError("GEMINI_API_KEY not set in .env")

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
    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    return response.text


def sanitize_slug(slug: str) -> str:
    slug = slug.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def slug_from_url(url: str) -> str:
    path = url.rstrip("/").split("/")[-1]
    path = path.split("?")[0].split("#")[0]
    return sanitize_slug(path)


def estimate_duration(wc: int) -> str:
    seconds = int(wc / 150 * 60)
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}m {secs}s"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/convert", methods=["POST"])
def convert():
    data = request.get_json()
    input_type = data.get("input_type")
    url = data.get("url", "").strip()
    text = data.get("text", "").strip()
    slug = data.get("slug", "").strip()

    try:
        if input_type == "url":
            if not url:
                return jsonify({"error": "URL is required"}), 400
            raw_text = fetch_article(url)
            file_slug = slug_from_url(url)
        elif input_type == "manual":
            if not text:
                return jsonify({"error": "Text content is required"}), 400
            if not slug:
                return jsonify({"error": "Filename slug is required"}), 400
            raw_text = text
            file_slug = sanitize_slug(slug)
            if not file_slug:
                return jsonify({"error": "Invalid slug"}), 400
        else:
            return jsonify({"error": "Invalid input type"}), 400

        cleaned = clean_text(raw_text)
        wc = word_count(cleaned)

        condensed = False
        final_text = cleaned
        if wc > WORD_COUNT_THRESHOLD:
            final_text = condense_with_gemini(cleaned)
            condensed = True

        final_wc = word_count(final_text)

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(OUTPUT_DIR, f"{file_slug}.mp3")
        asyncio.run(edge_tts.Communicate(final_text, TTS_VOICE).save(output_path))

        return jsonify({
            "success": True,
            "input_source": f"URL: {url}" if input_type == "url" else "Pasted text",
            "word_count_cleaned": wc,
            "condensation_applied": condensed,
            "word_count_final": final_wc if condensed else wc,
            "estimated_duration": estimate_duration(final_wc),
            "filename": f"{file_slug}.mp3",
            "download_url": f"/download/{file_slug}.mp3",
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
