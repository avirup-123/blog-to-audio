const MODEL_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium";
const MODEL_FILES = {
  onnx: `${MODEL_BASE}/en_US-lessac-medium.onnx`,
  config: `${MODEL_BASE}/en_US-lessac-medium.onnx.json`,
};

let ortSession = null;
let modelConfig = null;
let phonemeIdMap = null;

async function loadConfig(onProgress) {
  if (modelConfig) return;

  const configBuf = await ModelCache.fetchAndCache(
    MODEL_FILES.config, "piper-config",
    (loaded, total) => onProgress?.("config", loaded, total)
  );
  modelConfig = JSON.parse(new TextDecoder().decode(configBuf));
  phonemeIdMap = modelConfig.phoneme_id_map;
}

async function loadModel(onProgress) {
  if (ortSession) return;

  await loadConfig(onProgress);

  const modelBuf = await ModelCache.fetchAndCache(
    MODEL_FILES.onnx, "piper-model",
    (loaded, total) => onProgress?.("model", loaded, total)
  );

  ort.env.wasm.numThreads = 1;
  ort.env.wasm.simd = true;
  ort.env.wasm.wasmPaths = chrome.runtime.getURL("lib/");

  ortSession = await ort.InferenceSession.create(modelBuf, {
    executionProviders: ["wasm"],
    graphOptimizationLevel: "all",
  });
}

// --- Phonemization ---
// Piper models using espeak phoneme_type expect espeak IPA phonemes.
// We use a lightweight English phonemizer that maps text to the phoneme IDs
// the model was trained on. This covers the phoneme set used by en_US-lessac.

const CHAR_TO_PHONEMES = {
  a: "æ", b: "b", c: "k", d: "d", e: "ɛ", f: "f", g: "ɡ",
  h: "h", i: "ɪ", j: "dʒ", k: "k", l: "l", m: "m", n: "n",
  o: "ɑ", p: "p", q: "k", r: "ɹ", s: "s", t: "t", u: "ʌ",
  v: "v", w: "w", x: "ks", y: "j", z: "z",
};

// Common English words → approximate IPA (espeak-compatible subset)
const WORD_PHONEMES = {
  the: "ðə", a: "ə", an: "æn", and: "ænd", or: "ɔːɹ", is: "ɪz",
  are: "ɑːɹ", was: "wɑz", were: "wɜːɹ", be: "biː", been: "bɪn",
  have: "hæv", has: "hæz", had: "hæd", do: "duː", does: "dʌz",
  did: "dɪd", will: "wɪl", would: "wʊd", could: "kʊd", should: "ʃʊd",
  can: "kæn", may: "meɪ", might: "maɪt", must: "mʌst",
  not: "nɑt", no: "noʊ", yes: "jɛs",
  in: "ɪn", on: "ɑn", at: "æt", to: "tuː", for: "fɔːɹ",
  of: "ʌv", with: "wɪð", from: "fɹʌm", by: "baɪ",
  this: "ðɪs", that: "ðæt", it: "ɪt", he: "hiː", she: "ʃiː",
  we: "wiː", they: "ðeɪ", you: "juː", i: "aɪ",
  what: "wʌt", how: "haʊ", when: "wɛn", where: "wɛɹ", why: "waɪ",
  who: "huː", which: "wɪtʃ",
};

function textToPhonemeIds(text) {
  if (!phonemeIdMap) throw new Error("Model config not loaded");

  const PAD = phonemeIdMap["_"]?.[0] ?? 0;
  const BOS = phonemeIdMap["^"]?.[0] ?? 1;
  const EOS = phonemeIdMap["$"]?.[0] ?? 2;
  const SPACE = phonemeIdMap[" "]?.[0] ?? 3;

  const sentences = text.replace(/\n+/g, " ").split(/(?<=[.!?])\s+/);
  const allIds = [];

  for (const sentence of sentences) {
    if (!sentence.trim()) continue;

    const ids = [BOS];
    const words = sentence.trim().toLowerCase().replace(/[^\w\s'-]/g, "").split(/\s+/);

    for (let wi = 0; wi < words.length; wi++) {
      if (wi > 0) {
        ids.push(PAD);
        ids.push(SPACE);
        ids.push(PAD);
      }

      const word = words[wi];
      const phonemes = WORD_PHONEMES[word] || wordToPhonemes(word);

      for (const ch of phonemes) {
        const mapped = phonemeIdMap[ch];
        if (mapped && mapped.length > 0) {
          ids.push(PAD);
          ids.push(mapped[0]);
        }
      }
    }

    ids.push(PAD);
    ids.push(EOS);
    allIds.push(ids);
  }

  return allIds;
}

function wordToPhonemes(word) {
  let result = "";
  for (const ch of word) {
    result += CHAR_TO_PHONEMES[ch] || ch;
  }
  return result;
}

// --- Inference ---

async function synthesizeSentence(phonemeIds) {
  if (!ortSession) throw new Error("Model not loaded");

  const inputTensor = new ort.Tensor("int64",
    BigInt64Array.from(phonemeIds.map(BigInt)),
    [1, phonemeIds.length]
  );

  const lengthTensor = new ort.Tensor("int64",
    BigInt64Array.from([BigInt(phonemeIds.length)]),
    [1]
  );

  const scalesTensor = new ort.Tensor("float32",
    Float32Array.from([0.667, 1.0, 0.8]),
    [3]
  );

  const feeds = {
    input: inputTensor,
    input_lengths: lengthTensor,
    scales: scalesTensor,
  };

  const results = await ortSession.run(feeds);
  const outputKey = Object.keys(results)[0];
  return results[outputKey].data;
}

// --- Full pipeline ---

async function generateAudio(text, onProgress) {
  onProgress?.("loading");
  await loadModel((what, loaded, total) => {
    const pct = total ? Math.round(loaded / total * 100) : 0;
    onProgress?.("downloading", `${what}: ${pct}%`);
  });

  onProgress?.("phonemizing");
  const sentenceIds = textToPhonemeIds(text);

  onProgress?.("synthesizing");
  const sampleRate = modelConfig.audio?.sample_rate || 22050;
  const allSamples = [];
  const silenceSamples = new Float32Array(Math.floor(sampleRate * 0.3));

  for (let i = 0; i < sentenceIds.length; i++) {
    onProgress?.("synthesizing", `Sentence ${i + 1}/${sentenceIds.length}`);
    try {
      const samples = await synthesizeSentence(sentenceIds[i]);
      allSamples.push(samples);
      if (i < sentenceIds.length - 1) {
        allSamples.push(silenceSamples);
      }
    } catch (e) {
      console.warn(`Sentence ${i + 1} failed:`, e);
    }
  }

  const totalLen = allSamples.reduce((s, a) => s + a.length, 0);
  const merged = new Float32Array(totalLen);
  let offset = 0;
  for (const chunk of allSamples) {
    merged.set(chunk, offset);
    offset += chunk.length;
  }

  onProgress?.("encoding");
  return encodeMP3(merged, sampleRate);
}

// --- MP3 encoding ---

function encodeMP3(float32Samples, sampleRate) {
  const samples = new Int16Array(float32Samples.length);
  for (let i = 0; i < float32Samples.length; i++) {
    const s = Math.max(-1, Math.min(1, float32Samples[i]));
    samples[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
  }

  const mp3enc = new lamejs.Mp3Encoder(1, sampleRate, 128);
  const chunks = [];
  const blockSize = 1152;

  for (let i = 0; i < samples.length; i += blockSize) {
    const block = samples.subarray(i, Math.min(i + blockSize, samples.length));
    const mp3buf = mp3enc.encodeBuffer(block);
    if (mp3buf.length > 0) chunks.push(mp3buf);
  }

  const end = mp3enc.flush();
  if (end.length > 0) chunks.push(end);

  const totalLen = chunks.reduce((s, c) => s + c.length, 0);
  const mp3Data = new Uint8Array(totalLen);
  let off = 0;
  for (const chunk of chunks) {
    mp3Data.set(chunk, off);
    off += chunk.length;
  }

  return mp3Data;
}

if (typeof globalThis !== "undefined") {
  globalThis.PiperTTS = { loadModel, generateAudio };
}
