const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;

if (tg) {
  tg.ready();
  tg.expand();
}

const state = {
  initData: "",
  goals: { github_commits: 2, leetcode_solved: 2 },
  avatar: "🐶",
  celebrated: { github_commits: false, leetcode_solved: false },
  historyByDate: {},
  historyTz: "Europe/Kyiv",
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

async function apiGet(path, params = {}) {
  showLoading();
  try {
    const res = await fetch(buildUrl(path, { ...params, initData: state.initData }));
    if (!res.ok) throw new Error("Request failed");
    return res.json();
  } finally {
    hideLoading();
  }
}

async function apiPost(path, body, params = {}) {
  showLoading();
  try {
    const res = await fetch(buildUrl(path, { ...params, initData: state.initData }), {
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

function buildUrl(path, params = {}) {
  const url = new URL(path, window.location.origin);
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    url.searchParams.set(key, String(value));
  });
  return url.toString();
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

function setHeatmapMessage(message) {
  const el = document.getElementById("heatmap-message");
  if (!el) return;
  if (!message) {
    el.style.display = "none";
    el.textContent = "";
    return;
  }
  el.textContent = message;
  el.style.display = "block";
}

function setRing(el, current, goal) {
  if (!el) return;
  const circle = el.querySelector(".ring-progress");
  const label = el.querySelector(".ring-label");
  const safeGoal = Math.max(Number(goal) || 0, 0);
  const value = Math.max(Number(current) || 0, 0);
  const progress = safeGoal > 0 ? Math.min(value / safeGoal, 1) : 0;
  if (circle) {
    const radius = Number(circle.getAttribute("r")) || 0;
    const circumference = 2 * Math.PI * radius;
    circle.style.strokeDasharray = `${circumference}`;
    circle.style.strokeDashoffset = `${circumference * (1 - progress)}`;
  }
  if (label) {
    label.textContent = `${value}/${safeGoal}`;
  }
}

function launchConfetti(targetEl, palette) {
  if (!targetEl) return;
  const burst = document.createElement("div");
  burst.className = "confetti-burst";
  const colors = palette && palette.length ? palette : ["#3b82f6", "#5ad0a0", "#94a3b8"];
  const count = 14;
  for (let i = 0; i < count; i += 1) {
    const piece = document.createElement("div");
    piece.className = "confetti-piece";
    const angle = Math.random() * Math.PI * 2;
    const distance = 16 + Math.random() * 14;
    const x = Math.cos(angle) * distance;
    const y = Math.sin(angle) * distance;
    const rotate = (Math.random() * 240 - 120).toFixed(0);
    const size = 4 + Math.random() * 3;
    piece.style.width = `${size}px`;
    piece.style.height = `${size}px`;
    piece.style.background = colors[i % colors.length];
    piece.style.setProperty("--x", `${x.toFixed(1)}px`);
    piece.style.setProperty("--y", `${y.toFixed(1)}px`);
    piece.style.setProperty("--r", `${rotate}deg`);
    piece.style.animationDelay = `${(Math.random() * 120).toFixed(0)}ms`;
    burst.appendChild(piece);
  }
  targetEl.appendChild(burst);
  window.setTimeout(() => {
    burst.remove();
  }, 1000);
}

function maybeCelebrate(metricKey, current, goal, ringEl) {
  if (!ringEl || goal <= 0) return;
  if (current >= goal && !state.celebrated[metricKey]) {
    state.celebrated[metricKey] = true;
    const palette =
      metricKey === "github_commits"
        ? ["#3b82f6", "#7aa7ff", "#c2d7ff"]
        : ["#5ad0a0", "#8ee8c6", "#c7f4df"];
    launchConfetti(ringEl, palette);
  }
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

  const githubRing = document.querySelector("[data-ring='github']");
  const leetcodeRing = document.querySelector("[data-ring='leetcode']");
  setRing(githubRing, data.github_commits, data.goals.github_commits);
  setRing(leetcodeRing, data.leetcode_solved, data.goals.leetcode_solved);
  maybeCelebrate("github_commits", data.github_commits, data.goals.github_commits, githubRing);
  maybeCelebrate("leetcode_solved", data.leetcode_solved, data.goals.leetcode_solved, leetcodeRing);
}

function hexToRgb(hex) {
  const value = hex.replace("#", "");
  if (value.length !== 6) return null;
  const r = parseInt(value.slice(0, 2), 16);
  const g = parseInt(value.slice(2, 4), 16);
  const b = parseInt(value.slice(4, 6), 16);
  return { r, g, b };
}

function heatColor(hex, value, goal) {
  if (!value || value <= 0) {
    return "rgba(122, 132, 153, 0.12)";
  }
  const rgb = hexToRgb(hex);
  if (!rgb) return hex;
  const ratio = goal > 0 ? Math.min(value / goal, 1) : 1;
  const alpha = 0.25 + ratio * 0.6;
  return `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${alpha.toFixed(2)})`;
}

function weekdayShort(dateStr, tz) {
  const date = new Date(`${dateStr}T12:00:00Z`);
  return new Intl.DateTimeFormat("en-US", { weekday: "short", timeZone: tz }).format(date);
}

function buildTooltip(dayLabel, value, singular, plural) {
  const count = Number(value) || 0;
  const unit = count === 1 ? singular : plural;
  return `${dayLabel}: ${count} ${unit}`;
}

function weekdayIndex(dateStr, tz) {
  const date = new Date(`${dateStr}T12:00:00Z`);
  const label = new Intl.DateTimeFormat("en-US", { weekday: "short", timeZone: tz }).format(date);
  const map = { Mon: 0, Tue: 1, Wed: 2, Thu: 3, Fri: 4, Sat: 5, Sun: 6 };
  return map[label] ?? 0;
}

function heatLevel(value) {
  const count = Number(value) || 0;
  if (count <= 0) return 0;
  if (count === 1) return 1;
  if (count === 2) return 2;
  if (count === 3) return 3;
  return 4;
}

function renderHeatmap(data) {
  const githubGrid = document.querySelector("[data-heatmap='github']");
  const leetcodeGrid = document.querySelector("[data-heatmap='leetcode']");
  if (!githubGrid || !leetcodeGrid) return;
  const tzLabel = document.getElementById("weekly-tz");
  if (tzLabel) tzLabel.textContent = data.tz || "Europe/Kyiv";
  setHeatmapMessage("");

  state.historyByDate = {};
  state.historyTz = data.tz || "Europe/Kyiv";
  data.days.forEach((day) => {
    state.historyByDate[day.date] = day;
  });

  const slots = new Array(7).fill(null);
  data.days.forEach((day) => {
    const index = weekdayIndex(day.date, data.tz);
    slots[index] = day;
  });

  const renderRow = (grid, metricKey, unitLabel, rowClass) => {
    grid.innerHTML = "";
    slots.forEach((entry) => {
      const value = entry ? entry[metricKey] : 0;
      const dateLabel = entry ? entry.date : "—";
      const level = heatLevel(value);
      const cell = document.createElement("button");
      cell.type = "button";
      cell.className = `heatmap-cell hm-cell hm-${level} ${rowClass} ios-tap`;
      if (entry) {
        cell.dataset.date = entry.date;
      }
      cell.setAttribute("aria-label", buildTooltip(dateLabel, value, unitLabel.singular, unitLabel.plural));
      const tooltip = document.createElement("span");
      tooltip.className = "heatmap-tooltip";
      tooltip.textContent = buildTooltip(dateLabel, value, unitLabel.singular, unitLabel.plural);
      cell.appendChild(tooltip);
      cell.addEventListener("click", () => {
        if (entry) openInsight(entry.date);
        cell.classList.add("show-tooltip");
        window.setTimeout(() => cell.classList.remove("show-tooltip"), 1400);
      });
      grid.appendChild(cell);
    });
  };

  renderRow(githubGrid, "github", { singular: "commit", plural: "commits" }, "hm-row-github");
  renderRow(leetcodeGrid, "leetcode", { singular: "solved", plural: "solved" }, "hm-row-leetcode");
  initIosTap();
  updateWeekScore(data.days);
}

function updateWeekScore(days) {
  const weekScore = document.getElementById("week-score");
  const weekFill = document.getElementById("week-score-fill");
  if (!weekScore || !weekFill) return;
  const total = Array.isArray(days) ? days.length : 0;
  const completed = Array.isArray(days)
    ? days.filter((day) => day.github >= state.goals.github_commits && day.leetcode >= state.goals.leetcode_solved).length
    : 0;
  const ratio = total > 0 ? completed / total : 0;
  weekScore.textContent = `${completed}/${total || 7} days completed`;
  weekFill.style.width = `${Math.round(ratio * 100)}%`;
}

function formatInsightTitle(dateStr) {
  if (!dateStr) return "Day";
  const date = new Date(`${dateStr}T12:00:00Z`);
  const weekday = new Intl.DateTimeFormat("en-US", { weekday: "short", timeZone: state.historyTz }).format(date);
  return `${weekday}, ${dateStr}`;
}

function openInsight(dateStr) {
  const entry = state.historyByDate[dateStr] || { github: 0, leetcode: 0 };
  const title = document.getElementById("insight-title");
  const gh = document.getElementById("insight-github");
  const lc = document.getElementById("insight-leetcode");
  const ghRemain = document.getElementById("insight-github-remaining");
  const lcRemain = document.getElementById("insight-leetcode-remaining");
  const suggestion = document.getElementById("insight-suggestion");
  const card = document.getElementById("insight-card");
  const backdrop = document.getElementById("insight-backdrop");
  if (!card || !backdrop || !title || !gh || !lc || !ghRemain || !lcRemain || !suggestion) return;

  const ghGoal = state.goals.github_commits || 0;
  const lcGoal = state.goals.leetcode_solved || 0;
  const ghLeft = Math.max(ghGoal - entry.github, 0);
  const lcLeft = Math.max(lcGoal - entry.leetcode, 0);
  const completed = entry.github >= ghGoal && entry.leetcode >= lcGoal;

  title.textContent = formatInsightTitle(dateStr);
  gh.textContent = `${entry.github} / ${ghGoal}`;
  lc.textContent = `${entry.leetcode} / ${lcGoal}`;
  ghRemain.textContent = ghLeft > 0 ? `${ghLeft} left` : "goal met";
  lcRemain.textContent = lcLeft > 0 ? `${lcLeft} left` : "goal met";
  suggestion.textContent = completed
    ? "Nice — goals completed ✅"
    : "Quick win: do 1 easy LC + small commit";

  triggerHapticLight();
  card.classList.add("is-visible");
  backdrop.classList.add("is-visible");
}

function closeInsight() {
  const card = document.getElementById("insight-card");
  const backdrop = document.getElementById("insight-backdrop");
  if (!card || !backdrop) return;
  card.classList.remove("is-visible");
  backdrop.classList.remove("is-visible");
}

async function loadHistory() {
  if (!state.initData) {
    setHeatmapMessage("Open inside Telegram to see this week.");
    return;
  }
  try {
    const data = await apiGet("/api/history", { days: 7 });
    renderHeatmap(data);
  } catch (err) {
    console.error("Failed to load history:", err);
    setHeatmapMessage("History unavailable right now.");
  }
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

async function loadStatus(force = false) {
  state.initData = tg ? tg.initData || "" : "";
  if (!state.initData) {
    console.warn("Missing Telegram initData; open inside Telegram.");
    showError("WebApp init data missing. Open this dashboard from Telegram.");
    document.getElementById("date").textContent = "Open inside Telegram";
    setHeatmapMessage("Open inside Telegram to see this week.");
    return;
  }
  clearError();
  try {
    const data = await apiGet("/api/status", { force: force ? 1 : undefined });
    fillStatus(data);
    await loadHistory();
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
  document.getElementById("btnRefresh").addEventListener("click", () => loadStatus(true));
  document.getElementById("save-goals").addEventListener("click", saveGoals);
  document.getElementById("save-reminders").addEventListener("click", saveReminders);
  document.getElementById("save-repos").addEventListener("click", saveRepos);
  document.getElementById("open-settings").addEventListener("click", () => openBotLink("settings"));
  document.getElementById("open-status").addEventListener("click", () => openBotLink("status"));
  document.getElementById("btnAvatar").addEventListener("click", openAvatarSheet);
  document.getElementById("avatar-backdrop").addEventListener("click", closeAvatarSheet);
  document.getElementById("insight-backdrop").addEventListener("click", closeInsight);
  document.getElementById("insight-close").addEventListener("click", closeInsight);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeAvatarSheet();
      closeInsight();
    }
  });

  initIosTap();
  setSegmentDefaults();
  loadStatus();
});
