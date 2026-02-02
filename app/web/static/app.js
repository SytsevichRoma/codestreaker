const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;

if (tg) {
  tg.ready();
  tg.expand();
}

const state = {
  initData: "",
  goals: { github_commits: 2, leetcode_solved: 2 },
};

const botUsername = window.__BOT_USERNAME__ || "";

async function apiGet(url) {
  const res = await fetch(`${url}?initData=${encodeURIComponent(state.initData)}`);
  if (!res.ok) throw new Error("Request failed");
  return res.json();
}

async function apiPost(url, body) {
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

function initIosTap() {
  const tapTargets = document.querySelectorAll(".ios-tap");
  tapTargets.forEach((el) => {
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
  document.getElementById("refresh").addEventListener("click", loadStatus);
  document.getElementById("save-goals").addEventListener("click", saveGoals);
  document.getElementById("save-reminders").addEventListener("click", saveReminders);
  document.getElementById("save-repos").addEventListener("click", saveRepos);
  document.getElementById("open-settings").addEventListener("click", () => openBotLink("settings"));
  document.getElementById("open-status").addEventListener("click", () => openBotLink("status"));

  initIosTap();
  setSegmentDefaults();
  loadStatus();
});
