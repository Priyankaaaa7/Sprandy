const API = "";

// ---------- Helpers ----------
async function api(path, options = {}) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.status === 204 ? null : res.json();
}

function todayISO() {
  return new Date().toISOString().split("T")[0];
}

function yesterdayISO() {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return d.toISOString().split("T")[0];
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ---------- Tasks ----------
function renderTaskItem(t) {
  const completed = t.status === "completed";
  const div = document.createElement("div");
  div.className = "task-item";
  div.innerHTML = `
    <div>
      <span class="task-title ${completed ? "completed" : ""}">${escapeHtml(t.title)}</span>
      <span class="badge ${t.priority}">${t.priority}</span>
      ${t.postponed_count > 0 ? `<span class="badge postponed">postponed x${t.postponed_count}</span>` : ""}
      <div class="task-meta">${t.due_date ? "Due: " + t.due_date : "No due date"}</div>
    </div>
    <div class="task-actions">
      ${!completed ? `<button class="complete-btn" data-id="${t.id}">Done</button>` : ""}
      ${!completed ? `<button class="postpone-btn" data-id="${t.id}">Postpone</button>` : ""}
      <button class="delete-btn" data-id="${t.id}">Delete</button>
    </div>
  `;
  return div;
}

function wireTaskButtons(container) {
  container.querySelectorAll(".complete-btn").forEach((btn) =>
    btn.addEventListener("click", async () => {
      await api(`/tasks/${btn.dataset.id}/complete`, { method: "POST" });
      refreshAll();
    })
  );
  container.querySelectorAll(".delete-btn").forEach((btn) =>
    btn.addEventListener("click", async () => {
      await api(`/tasks/${btn.dataset.id}`, { method: "DELETE" });
      refreshAll();
    })
  );
  container.querySelectorAll(".postpone-btn").forEach((btn) =>
    btn.addEventListener("click", async () => {
      const newDate = prompt("New due date (YYYY-MM-DD):", todayISO());
      if (!newDate) return;
      const reason = prompt("Reason (optional):", "");
      await api(`/tasks/${btn.dataset.id}/postpone`, {
        method: "POST",
        body: JSON.stringify({ new_due_date: newDate, reason }),
      });
      refreshAll();
    })
  );
}

async function loadTasks() {
  const tasks = await api("/tasks");
  const today = todayISO();

  // Today's tasks: due today, overdue, or no due date and not completed
  const todays = tasks.filter(
    (t) => t.status !== "completed" && (!t.due_date || t.due_date <= today)
  );

  const todayList = document.getElementById("today-task-list");
  todayList.innerHTML = "";
  if (todays.length === 0) {
    todayList.innerHTML = "<p class='task-meta'>Nothing due today. Suspicious, but enjoy it.</p>";
  } else {
    todays.forEach((t) => todayList.appendChild(renderTaskItem(t)));
    wireTaskButtons(todayList);
  }

  const allList = document.getElementById("all-task-list");
  allList.innerHTML = "";
  if (tasks.length === 0) {
    allList.innerHTML = "<p class='task-meta'>No tasks yet.</p>";
  } else {
    tasks.forEach((t) => allList.appendChild(renderTaskItem(t)));
    wireTaskButtons(allList);
  }
}

document.getElementById("task-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const title = document.getElementById("task-title").value;
  const due = document.getElementById("task-due").value || null;
  const priority = document.getElementById("task-priority").value;
  await api("/tasks", {
    method: "POST",
    body: JSON.stringify({ title, due_date: due, priority }),
  });
  document.getElementById("task-title").value = "";
  document.getElementById("task-due").value = "";
  refreshAll();
});

// ---------- Accountability (v0.12 endpoint) ----------
async function loadAccountability() {
  const data = await api("/accountability");
  const el = document.getElementById("accountability-content");
  el.innerHTML = "";

  if (!data.flags || data.flags.length === 0) {
    el.innerHTML = "<p class='all-clear'>No chronic postponement detected. Don't get comfortable.</p>";
    return;
  }

  data.flags.forEach((f) => {
    const div = document.createElement("div");
    div.className = "flag";
    div.textContent = f.message;
    el.appendChild(div);
  });
}

// ---------- Journal ----------
async function loadJournal() {
  try {
    const entry = await api(`/journal/${todayISO()}`);
    document.getElementById("journal-content").value = entry.content;
    document.getElementById("journal-mood").value = entry.mood || "";
  } catch (e) {
    // no entry yet today
  }
}

document.getElementById("journal-save").addEventListener("click", async () => {
  const content = document.getElementById("journal-content").value;
  const mood = document.getElementById("journal-mood").value;
  if (!content.trim()) return;
  await api("/journal", {
    method: "POST",
    body: JSON.stringify({ entry_date: todayISO(), content, mood }),
  });
  const status = document.getElementById("journal-status");
  status.textContent = "Saved.";
  setTimeout(() => (status.textContent = ""), 2000);
});

// ---------- Summary ----------
async function loadDefaultSummary() {
  const label = document.getElementById("summary-label");
  const output = document.getElementById("summary-output");
  try {
    const summary = await api(`/summaries/daily/${yesterdayISO()}`);
    label.textContent = "Yesterday's summary";
    output.textContent = summary.summary_text;
  } catch (e) {
    label.textContent = "Yesterday's summary";
    output.textContent = "Not generated yet. Click \"Generate Today's\" daily to build a history.";
  }
}

document.getElementById("gen-daily").addEventListener("click", async () => {
  const summary = await api("/summaries/daily/generate", { method: "POST" });
  document.getElementById("summary-label").textContent = "Today's summary";
  document.getElementById("summary-output").textContent = summary.summary_text;
});

document.getElementById("gen-weekly").addEventListener("click", async () => {
  const summary = await api("/summaries/weekly/generate", { method: "POST" });
  document.getElementById("summary-label").textContent = `This week (${summary.week_start} to ${summary.week_end})`;
  document.getElementById("summary-output").textContent = summary.summary_text;
});

// ---------- Init ----------
function refreshAll() {
  loadTasks();
  loadAccountability();
}

refreshAll();
loadJournal();
loadDefaultSummary();
