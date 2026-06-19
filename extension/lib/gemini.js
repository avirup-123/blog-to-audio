const GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE";
const GEMINI_MODEL = "gemini-2.0-flash";
const GEMINI_ENDPOINT = `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key=${GEMINI_API_KEY}`;
const CONDENSED_TARGET_WORDS = 2500;

async function condenseWithGemini(text) {
  const prompt =
    `Condense the following article to approximately ${CONDENSED_TARGET_WORDS} words.\n\n` +
    "Rules:\n" +
    "- Preserve every key point, all details, data points, statistics, steps, and important information\n" +
    "- Remove only filler phrases, redundant sentences, decorative transitions, and repetitive content\n" +
    "- Do not remove any section entirely unless it contains zero informational value\n" +
    "- Maintain the logical flow and structure of the original article\n" +
    "- Return only the condensed article text, no commentary or explanation\n\n" +
    `Article:\n${text}`;

  const resp = await fetch(GEMINI_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      contents: [{ parts: [{ text: prompt }] }]
    })
  });

  if (!resp.ok) {
    const err = await resp.text();
    throw new Error(`Gemini API error (${resp.status}): ${err}`);
  }

  const data = await resp.json();
  return data.candidates?.[0]?.content?.parts?.[0]?.text || "";
}

if (typeof globalThis !== "undefined") {
  globalThis.Gemini = { condenseWithGemini };
}
