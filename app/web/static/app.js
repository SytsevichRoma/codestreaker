const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;

if (tg) {
  tg.ready();
  tg.expand();
}

const state = {
  initData: "",
  goals: { github_commits: 2, leetcode_solved: 2 },
  avatar: "🐶",
};

const botUsername = window.__BOT_USERNAME__ || "";

let loadingCount = 0;

function setButtonsDisabled(disabled) {
  document.querySelectorAll("button").forEach((btn) => {
    btn.disabled = disabled;
  });
}

function showLoading() {
  loadingCount += 1;
  if (loadingCount === 1) {
    document.body.classList.add("is-loading");
    const overlay = document.getElementById("loading-overlay");
    if (overlay) overlay.classList.add("is-visible");
    setButtonsDisabled(true);
  }
}

function hideLoading() {
  loadingCount = Math.max(loadingCount - 1, 0);
  if (loadingCount === 0) {
    document.body.classList.remove("is-loading");
    const overlay = document.getElementById("loading-overlay");
    if (overlay) overlay.classList.remove("is-visible");
    setButtonsDisabled(false);
  }
}

async function apiGet(url) {
  showLoading();
  try {
    const res = await fetch(`${url}?initData=${encodeURIComponent(state.initData)}`);
    if (!res.ok) throw new Error("Request failed");
    return res.json();
  } finally {
    hideLoading();
  }
}

async function apiPost(url, body) {
  showLoading();
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Telegram-Init-Data": state.initData,
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error("Request failed");
    return res.json();
  } finally {
    hideLoading();
  }
}

function showError(message) {
  const banner = document.getElementById("error-banner");
  if (!banner) return;
  banner.textContent = message;
  banner.style.display = "block";
}

function clearError() {
  const banner = document.getElementById("error-banner");
  if (!banner) return;
  banner.style.display = "none";
}

function fillStatus(data) {
  document.getElementById("date").textContent = `${data.date} (${data.timezone})`;
  document.getElementById("github").textContent = data.github_commits;
  document.getElementById("leetcode").textContent = data.leetcode_solved;
  document.getElementById("github-goal").textContent = `/${data.goals.github_commits}`;
  document.getElementById("leetcode-goal").textContent = `/${data.goals.leetcode_solved}`;
  document.getElementById("current-streak").textContent = data.streak.current_streak;
  document.getElementById("best-streak").textContent = data.streak.best_streak;

  state.goals = data.goals;
  document.getElementById("goal-github").value = data.goals.github_commits;
  document.getElementById("goal-leetcode").value = data.goals.leetcode_solved;
  document.getElementById("reminder-1").value = data.reminders[0] || "";
  document.getElementById("reminder-2").value = data.reminders[1] || "";
  document.getElementById("repos").value = data.repos.join(", ");
  if (data.avatar) {
    state.avatar = data.avatar;
  }
  renderAvatarBadge();
}

function setSegmentDefaults() {
  document.querySelectorAll(".seg-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      document.querySelectorAll(".seg-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const mode = btn.dataset.goal;
      let goals = { github_commits: 2, leetcode_solved: 2 };
      if (mode === "low") goals = { github_commits: 1, leetcode_solved: 1 };
      if (mode === "high") goals = { github_commits: 5, leetcode_solved: 4 };
      document.getElementById("goal-github").value = goals.github_commits;
      document.getElementById("goal-leetcode").value = goals.leetcode_solved;
    });
  });
}

async function loadStatus() {
  state.initData = tg ? tg.initData || "" : "";
  if (!state.initData) {
    console.warn("Missing Telegram initData; open inside Telegram.");
    showError("WebApp init data missing. Open this dashboard from Telegram.");
    document.getElementById("date").textContent = "Open inside Telegram";
    return;
  }
  clearError();
  try {
    const data = await apiGet("/api/status");
    fillStatus(data);
  } catch (err) {
    console.error("Failed to load status:", err);
    showError("Failed to load status. Please try again.");
  }
}

async function saveGoals() {
  const gh = Number(document.getElementById("goal-github").value || 0);
  const lc = Number(document.getElementById("goal-leetcode").value || 0);
  await apiPost("/api/settings", { goals: { github_commits: gh, leetcode_solved: lc } });
  await loadStatus();
}

async function saveReminders() {
  const r1 = document.getElementById("reminder-1").value;
  const r2 = document.getElementById("reminder-2").value;
  const reminders = [r1, r2].filter(Boolean);
  await apiPost("/api/settings", { reminders });
  await loadStatus();
}

async function saveRepos() {
  const text = document.getElementById("repos").value;
  const repos = text.split(",").map((r) => r.trim()).filter(Boolean);
  await apiPost("/api/settings", { repos });
  await loadStatus();
}

function openBotLink(command) {
  if (!botUsername) return;
  const url = `https://t.me/${botUsername}?start=${command}`;
  if (tg) tg.openTelegramLink(url);
}

function triggerHapticLight() {
  if (!tg || !tg.HapticFeedback || typeof tg.HapticFeedback.impactOccurred !== "function") return;
  try {
    tg.HapticFeedback.impactOccurred("light");
  } catch (err) {
    console.warn("Haptic feedback unavailable:", err);
  }
}

const AVATARS = ["🐶", "🐱", "🦊", "🐻", "🐼", "🐸", "🐵", "🐯", "🐨", "🦁"];

function renderAvatarBadge() {
  const badge = document.getElementById("avatar-badge");
  if (badge) badge.textContent = state.avatar || "🐶";
}

function renderAvatarGrid() {
  const grid = document.getElementById("avatar-grid");
  if (!grid) return;
  grid.innerHTML = "";
  AVATARS.forEach((emoji) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "avatar-option ios-tap ios-card";
    btn.dataset.avatar = emoji;
    btn.textContent = emoji;
    if (emoji === state.avatar) btn.classList.add("selected");
    btn.addEventListener("click", async () => {
      if (state.avatar === emoji) {
        closeAvatarSheet();
        return;
      }
      state.avatar = emoji;
      renderAvatarBadge();
      renderAvatarGrid();
      triggerHapticLight();
      try {
        await apiPost("/api/settings", { avatar: emoji });
      } catch (err) {
        console.error("Failed to save avatar:", err);
        showError("Failed to save avatar. Please try again.");
      }
      closeAvatarSheet();
    });
    grid.appendChild(btn);
  });
  initIosTap();
}

function openAvatarSheet() {
  const sheet = document.getElementById("avatar-sheet");
  const backdrop = document.getElementById("avatar-backdrop");
  if (!sheet || !backdrop) return;
  renderAvatarGrid();
  sheet.classList.add("is-visible");
  backdrop.classList.add("is-visible");
}

function closeAvatarSheet() {
  const sheet = document.getElementById("avatar-sheet");
  const backdrop = document.getElementById("avatar-backdrop");
  if (!sheet || !backdrop) return;
  sheet.classList.remove("is-visible");
  backdrop.classList.remove("is-visible");
}

function initIosTap() {
  const tapTargets = document.querySelectorAll(".ios-tap");
  tapTargets.forEach((el) => {
    if (el.dataset.iosTapBound === "true") return;
    el.dataset.iosTapBound = "true";
    const addPressed = () => el.classList.add("is-pressed");
    const removePressed = () => el.classList.remove("is-pressed");

    el.addEventListener("pointerdown", (event) => {
      if (event.button !== undefined && event.button !== 0) return;
      addPressed();
      if (el.classList.contains("ios-button") || el.tagName === "BUTTON") {
        triggerHapticLight();
      }
    });
    el.addEventListener("pointerup", removePressed);
    el.addEventListener("pointerleave", removePressed);
    el.addEventListener("pointercancel", removePressed);
    el.addEventListener("blur", removePressed);
    el.addEventListener("keydown", (event) => {
      if (event.key === " " || event.key === "Enter") addPressed();
    });
    el.addEventListener("keyup", (event) => {
      if (event.key === " " || event.key === "Enter") removePressed();
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  renderAvatarBadge();
  document.getElementById("btnRefresh").addEventListener("click", loadStatus);
  document.getElementById("save-goals").addEventListener("click", saveGoals);
  document.getElementById("save-reminders").addEventListener("click", saveReminders);
  document.getElementById("save-repos").addEventListener("click", saveRepos);
  document.getElementById("open-settings").addEventListener("click", () => openBotLink("settings"));
  document.getElementById("open-status").addEventListener("click", () => openBotLink("status"));
  document.getElementById("btnAvatar").addEventListener("click", openAvatarSheet);
  document.getElementById("avatar-backdrop").addEventListener("click", closeAvatarSheet);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeAvatarSheet();
  });

  initIosTap();
  setSegmentDefaults();
  loadStatus();
});
