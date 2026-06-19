const DB_NAME = "blog-to-audio-cache";
const DB_VERSION = 1;
const STORE_NAME = "models";

function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      req.result.createObjectStore(STORE_NAME);
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function getCached(key) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly");
    const req = tx.objectStore(STORE_NAME).get(key);
    req.onsuccess = () => resolve(req.result ?? null);
    req.onerror = () => reject(req.error);
  });
}

async function setCached(key, value) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    tx.objectStore(STORE_NAME).put(value, key);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

async function fetchAndCache(url, key, onProgress) {
  const cached = await getCached(key);
  if (cached) return cached;

  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`Download failed: ${url} (${resp.status})`);

  const total = parseInt(resp.headers.get("content-length") || "0", 10);
  const reader = resp.body.getReader();
  const chunks = [];
  let loaded = 0;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
    loaded += value.length;
    if (onProgress && total) onProgress(loaded, total);
  }

  const blob = new Blob(chunks);
  const buffer = await blob.arrayBuffer();
  await setCached(key, buffer);
  return buffer;
}

if (typeof globalThis !== "undefined") {
  globalThis.ModelCache = { getCached, setCached, fetchAndCache };
}
