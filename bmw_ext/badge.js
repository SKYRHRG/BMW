// badge.js — हर पेज पर corner में Slot label दिखाने के लिए

const BADGE_ID = "__bmw_slot_badge__";

function ensureBadge(label) {
  let el = document.getElementById(BADGE_ID);

  if (!label) {
    if (el) el.remove();
    return;
  }

  if (!el) {
    el = document.createElement("div");
    el.id = BADGE_ID;
    el.style.position = "fixed";
    el.style.top = "8px";
    el.style.right = "8px";
    el.style.zIndex = "2147483647";
    el.style.padding = "4px 8px";
    el.style.background = "rgba(0,0,0,0.6)";
    el.style.color = "#fff";
    el.style.borderRadius = "6px";
    el.style.font = "12px/1.2 system-ui, Arial, sans-serif";
    el.style.pointerEvents = "none";
    document.documentElement.appendChild(el);
  }
  el.textContent = label;
}

async function initBadge() {
  const { bmw_slot_label } = await chrome.storage.local.get("bmw_slot_label");
  ensureBadge(bmw_slot_label || null);
}

chrome.storage.onChanged.addListener((changes, area) => {
  if (area === "local" && changes.bmw_slot_label) {
    ensureBadge(changes.bmw_slot_label.newValue || null);
  }
});

initBadge();
