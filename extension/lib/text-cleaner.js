const SYMBOL_MAP = {
  "&": " and ",
  "%": " percent ",
  "→": " to ",
};

const ABBREVIATION_MAP = {
  "e.g.": "for example",
  "i.e.": "that is",
  "etc.": "and so on",
  "vs.": "versus",
  "approx.": "approximately",
};

const ORDINALS = [
  "First", "Second", "Third", "Fourth", "Fifth",
  "Sixth", "Seventh", "Eighth", "Ninth", "Tenth"
];

function cleanText(raw) {
  let text = raw.replace(/<[^>]*>/g, "");

  // Truncate at FAQ section
  const faqMatch = text.match(/(?:FAQ|FAQs|Frequently\s+Asked\s+Questions)/i);
  if (faqMatch) {
    text = text.substring(0, faqMatch.index).trimEnd();
  }

  // Remove markdown formatting
  text = text.replace(/[*_`#]/g, "");
  text = text.replace(/-{3,}/g, "");

  // Symbol replacement
  for (const [sym, word] of Object.entries(SYMBOL_MAP)) {
    text = text.split(sym).join(word);
  }

  // Abbreviation expansion
  for (const [abbr, expansion] of Object.entries(ABBREVIATION_MAP)) {
    text = text.split(abbr).join(expansion);
  }

  // Convert lists to spoken sequences
  text = text.replace(
    /((?:^|\n)\s*(?:[-•*]|\d+[.)]) +.+(?:\n\s*(?:[-•*]|\d+[.)]) +.+)*)/g,
    (block) => {
      const items = [...block.matchAll(/(?:^|\n)\s*(?:[-•*]|\d+[.)]) *(.*)/g)]
        .map(m => m[1].trim())
        .filter(Boolean);
      if (!items.length) return block;
      return items.map((item, i) => {
        let prefix = ORDINALS[i] || "Next";
        if (i === items.length - 1 && items.length > 1) prefix = "Finally";
        return `${prefix}, ${item}.`;
      }).join(" ");
    }
  );

  // Convert headings to verbal transitions
  const lines = text.split("\n");
  const processed = [];
  for (const line of lines) {
    const stripped = line.trim();
    if (!stripped) { processed.push(""); continue; }

    const words = stripped.split(/\s+/);
    if (
      words.length <= 12 &&
      stripped === stripped.replace(/[.!?]+$/, "") &&
      !/[.,;:]/.test(stripped) &&
      /^[A-Z]/.test(stripped) &&
      processed.length > 0 &&
      processed[processed.length - 1] === ""
    ) {
      processed.push(`Now, let's talk about ${stripped}.`);
    } else {
      processed.push(stripped);
    }
  }

  text = processed.join("\n");
  text = text.replace(/\n{3,}/g, "\n\n");
  text = text.replace(/ {2,}/g, " ");
  return text.trim();
}

function wordCount(text) {
  return text.split(/\s+/).filter(Boolean).length;
}

function sanitizeSlug(slug) {
  return slug.toLowerCase().trim()
    .replace(/[^a-z0-9\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
}

function slugFromUrl(url) {
  try {
    const path = new URL(url).pathname;
    const last = path.replace(/\/$/, "").split("/").pop() || "audio";
    return sanitizeSlug(last);
  } catch {
    return "audio";
  }
}

if (typeof globalThis !== "undefined") {
  globalThis.TextCleaner = { cleanText, wordCount, sanitizeSlug, slugFromUrl };
}
