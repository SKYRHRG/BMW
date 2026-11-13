// ===== MV3 background (service worker) - UPDATED DEBUG VERSION =====

const SEED_URL = chrome.runtime.getURL("seed.json");

// RAM auth map (host:port -> {u,p})
const authMap = Object.create(null);
const pendingReq = Object.create(null);

function normalizeScheme(s) {
  const v = String(s || "http").toLowerCase();
  if (v.startsWith("socks5")) return "socks5";
  if (v.startsWith("socks4")) return "socks4";
  if (v === "https") return "https";
  return "http"; // default
}

function isProxyChallenge(details) {
  if (!details) return false;
  if (details.isProxy === true) return true;
  if (details.challenger && details.challenger.host) return true;
  if ((details.statusLine || "").includes("407")) return true;
  return false;
}

function clearAuth() {
  for (const k of Object.keys(authMap)) delete authMap[k];
  for (const r of Object.keys(pendingReq)) delete pendingReq[r];
}

function setAuth(host, port, user, pass) {
  clearAuth();
  if (host && port && user) {
    authMap[`${host}:${port}`] = { u: user, p: pass || "" };
    console.log(`[DEBUG bg.js] Credentials set in authMap for ${host}:${port}`);
  } else {
    console.log(`[DEBUG bg.js] setAuth called with incomplete data. authMap cleared.`);
  }
}

function clearProxy() {
  chrome.proxy.settings.clear({ scope: "regular" }, () => {
    console.log("[bg] Proxy cleared");
  });
  clearAuth();
}

function applyProxy({ scheme, host, port, user, pass, bypassList }) {
  if (!host || !port) {
    console.warn("[bg] Missing host/port → clearing proxy.");
    clearProxy();
    return;
  }
  const config = {
    mode: "fixed_servers",
    rules: {
      singleProxy: { scheme: normalizeScheme(scheme), host: String(host), port: Number(port) },
      bypassList: Array.isArray(bypassList) && bypassList.length ? bypassList : ["<local>"]
    }
  };
  console.log("[DEBUG bg.js] Preparing to apply proxy config:", config);
  setAuth(String(host), String(port), String(user || ""), String(pass || ""));
  chrome.proxy.settings.set({ value: config, scope: "regular" }, () => {
    console.log("[bg] Proxy applied:", config);
  });
}

async function readSeed() {
  console.log("[DEBUG bg.js] Reading seed.json...");
  try {
    const res = await fetch(SEED_URL, { cache: "no-store" });
    if (!res.ok) throw new Error(`fetch ${SEED_URL} ${res.status}`);
    const data = await res.json();
    console.log("[DEBUG bg.js] Successfully read and parsed seed.json.");
    return data || {};
  } catch (e) {
    console.warn("[bg] readSeed error:", e);
    return {};
  }
}

// ===================================================================
// =================== बदला हुआ फंक्शन यहाँ है =======================
// ===================================================================
async function applyFromSeed() {
  const seed = await readSeed();
  
  console.log("[DEBUG bg.js] applyFromSeed को seed.json से यह डेटा मिला:", seed);

  // --- बदलाव 1: 'activeProxy' पढ़ें, 'activeSlot' नहीं ---
  const active = Number(seed.activeProxy || 1);

  // --- बदलाव 2: 'proxies' (एरे) से पहला प्रॉक्सी निकालें, 'proxy' (ऑब्जेक्ट) नहीं ---
  let px = {};
  if (Array.isArray(seed.proxies) && seed.proxies.length > 0) {
    px = seed.proxies[0]; // एरे से पहला आइटम लेते हैं
  }

  const payload = {
    scheme: px.scheme || "http",
    host: (px.ip || "").trim(),
    port: Number(px.port || 0),
    user: (px.user || "").trim(),
    pass: (px.pass || "").trim(),
    bypassList: Array.isArray(seed.bypassList) ? seed.bypassList : ["<local>"]
  };
  
  console.log("[DEBUG bg.js] नए लॉजिक से Parsed payload:", payload);

  if (active <= 1 || !payload.host || !payload.port) {
    console.log("[DEBUG bg.js] Decision: Slot is 1 or proxy data is incomplete. Clearing proxy.");
    clearProxy();
    return;
  }
  
  console.log("[DEBUG bg.js] Decision: Applying proxy.");
  applyProxy(payload);
}
// ===================================================================
// =================== फंक्शन में बदलाव खत्म ==========================
// ===================================================================


// Auth challenge handler (for proxy 407)
chrome.webRequest.onAuthRequired.addListener(
  (details, callbackFn) => {
    console.log("[DEBUG bg.js] onAuthRequired event triggered. Details:", details);
    const ch = details.challenger || {};
    if (!isProxyChallenge(details)) {
      callbackFn({});
      return;
    }
    if (pendingReq[details.requestId]) {
      callbackFn({ cancel: true });
      return;
    }
    const key = `${ch.host || ""}:${ch.port || ""}`;
    const entry = authMap[key];
    console.log(`[DEBUG bg.js] Proxy challenge for key: "${key}"`);
    if (entry && entry.u) {
      console.log(`[DEBUG bg.js] Credentials found for key "${key}". Providing username: ${entry.u}`);
      pendingReq[details.requestId] = 1;
      callbackFn({ authCredentials: { username: entry.u, password: entry.p || "" } });
    } else {
      console.error(`[DEBUG bg.js] ERROR: No credentials found in authMap for key "${key}"`);
      callbackFn({});
    }
  },
  { urls: ["<all_urls>"] },
  ["asyncBlocking"]
);

// Verbose proxy errors
chrome.proxy.onProxyError.addListener((e) => {
  try { console.warn("[bg] onProxyError:", e, " details:", JSON.stringify(e)); }
  catch { console.warn("[bg] onProxyError:", e); }
});

// Apply timing
chrome.runtime.onInstalled.addListener(applyFromSeed);
chrome.runtime.onStartup.addListener(applyFromSeed);
applyFromSeed();

// Optional polling
let _poll = 0;
function startLightPolling(ms = 2500, times = 4) {
  if (_poll) return;
  let left = Math.max(1, times);
  _poll = setInterval(async () => {
    left -= 1;
    await applyFromSeed();
    if (left <= 0) {
      clearInterval(_poll); _poll = 0;
    }
  }, ms);
}
startLightPolling();