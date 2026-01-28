const tg = window.Telegram.WebApp;

tg.ready();

tg.expand();

const state = {
  initData: tg.initData || "",
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
      "X-Init-Data": state.initData,
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error("Request failed");
  return res.json();
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

async function refresh() {
  if (!state.initData) {
    document.getElementById("date").textContent = "Open inside Telegram";
    return;
  }
  const data = await apiGet("/api/status");
  fillStatus(data);
}

async function saveGoals() {
  const gh = Number(document.getElementById("goal-github").value || 0);
  const lc = Number(document.getElementById("goal-leetcode").value || 0);
  await apiPost("/api/settings", { goals: { github_commits: gh, leetcode_solved: lc } });
  await refresh();
}

async function saveReminders() {
  const r1 = document.getElementById("reminder-1").value;
  const r2 = document.getElementById("reminder-2").value;
  const reminders = [r1, r2].filter(Boolean);
  await apiPost("/api/settings", { reminders });
  await refresh();
}

async function saveRepos() {
  const text = document.getElementById("repos").value;
  const repos = text.split(",").map((r) => r.trim()).filter(Boolean);
  await apiPost("/api/settings", { repos });
  await refresh();
}

function openBotLink(command) {
  if (!botUsername) return;
  const url = `https://t.me/${botUsername}?start=${command}`;
  tg.openTelegramLink(url);
}

document.getElementById("refresh").addEventListener("click", refresh);
document.getElementById("save-goals").addEventListener("click", saveGoals);
document.getElementById("save-reminders").addEventListener("click", saveReminders);
document.getElementById("save-repos").addEventListener("click", saveRepos);
document.getElementById("open-settings").addEventListener("click", () => openBotLink("settings"));
document.getElementById("open-status").addEventListener("click", () => openBotLink("status"));

setSegmentDefaults();
refresh();
