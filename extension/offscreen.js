const WORD_COUNT_THRESHOLD = 3000;

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "process") {
    handleProcess(msg.data).then(
      result => sendResponse({ ok: true, result }),
      err => sendResponse({ ok: false, error: err.message })
    );
    return true;
  }
});

async function handleProcess({ rawText, url, slug }) {
  postStatus("cleaning", "Cleaning text for audio...");
  const cleaned = TextCleaner.cleanText(rawText);
  const wc = TextCleaner.wordCount(cleaned);

  let finalText = cleaned;
  let condensed = false;

  if (wc > WORD_COUNT_THRESHOLD) {
    postStatus("condensing", "Condensing with Gemini...");
    finalText = await Gemini.condenseWithGemini(cleaned);
    condensed = true;
  }

  const finalWc = TextCleaner.wordCount(finalText);
  const fileSlug = slug || TextCleaner.slugFromUrl(url || "audio");

  postStatus("synthesizing", "Generating audio with Piper TTS...");
  const mp3Data = await PiperTTS.generateAudio(finalText, (stage, detail) => {
    postStatus(stage, detail || stage);
  });

  const base64 = arrayBufferToBase64(mp3Data.buffer);

  return {
    mp3Base64: base64,
    filename: `${fileSlug}.mp3`,
    inputSource: url ? `URL: ${url}` : "Pasted text",
    wordCountCleaned: wc,
    wordCountFinal: finalWc,
    condensed,
    estimatedDuration: estimateDuration(finalWc),
  };
}

function postStatus(stage, detail) {
  chrome.runtime.sendMessage({ type: "status", stage, detail });
}

function estimateDuration(wc) {
  const seconds = Math.round(wc / 150 * 60);
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${s}s`;
}

function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}
