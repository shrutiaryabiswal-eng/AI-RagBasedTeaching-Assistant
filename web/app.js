const videoList = document.querySelector("#video-list");
const libraryCount = document.querySelector("#library-count");
const libraryMessage = document.querySelector("#library-message");
const connectionStatus = document.querySelector("#connection-status");
const statusDot = document.querySelector("#status-dot");
const messageList = document.querySelector("#message-list");
const intro = document.querySelector("#intro");
const questionForm = document.querySelector("#question-form");
const questionInput = document.querySelector("#question-input");
const sendButton = document.querySelector("#send-button");

function setConnection(online) {
  connectionStatus.textContent = online ? "Course library ready" : "API unavailable";
  statusDot.classList.toggle("online", online);
  statusDot.classList.toggle("offline", !online);
}

async function loadCatalog() {
  try {
    const response = await fetch("/api/catalog", { signal: AbortSignal.timeout(15000) });
    if (!response.ok) throw new Error("Could not load the course library");
    const { videos } = await response.json();
    libraryCount.textContent = String(videos.length).padStart(2, "0");
    libraryMessage.remove();
    for (const video of videos) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "video-link";
      button.dataset.title = video.title;

      const number = document.createElement("span");
      number.className = "video-number";
      number.textContent = String(video.video_number).padStart(2, "0");
      const title = document.createElement("span");
      title.className = "video-title";
      title.textContent = video.title.replaceAll("_", " ");
      button.append(number, title);
      button.addEventListener("click", () => {
        questionInput.value = `What are the key ideas in ${title.textContent}?`;
        questionInput.focus();
        questionInput.dispatchEvent(new Event("input"));
      });
      videoList.append(button);
    }
    setConnection(true);
  } catch {
    libraryCount.textContent = "--";
    libraryMessage.textContent = "The course library could not connect. Check the API deployment and try again.";
    setConnection(false);
  }
}

function formatTime(seconds) {
  const totalSeconds = Math.max(0, Math.floor(Number(seconds) || 0));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const remaining = totalSeconds % 60;
  return hours > 0
    ? `${hours}:${String(minutes).padStart(2, "0")}:${String(remaining).padStart(2, "0")}`
    : `${String(minutes).padStart(2, "0")}:${String(remaining).padStart(2, "0")}`;
}

function addMessage(role, text, sources = [], isError = false) {
  const message = document.createElement("article");
  message.className = `message ${role}${isError ? " error" : ""}`;
  if (role === "assistant") {
    const label = document.createElement("div");
    label.className = "message-label";
    label.textContent = "FIELDNOTES";
    message.append(label);
  }
  const body = document.createElement("div");
  body.className = role === "assistant" ? "answer-text" : "user-text";
  body.textContent = text;
  message.append(body);

  if (sources.length > 0) {
    const sourceList = document.createElement("div");
    sourceList.className = "source-list";
    for (const source of sources) {
      const card = document.createElement("div");
      card.className = "source";
      const time = document.createElement("span");
      time.className = "source-time";
      time.textContent = formatTime(source.start);
      const detail = document.createElement("div");
      const title = document.createElement("div");
      title.className = "source-title";
      title.textContent = `Video ${String(source.video_number).padStart(2, "0")} / ${String(source.title).replaceAll("_", " ")}`;
      const excerpt = document.createElement("div");
      excerpt.className = "source-excerpt";
      excerpt.textContent = source.text;
      detail.append(title, excerpt);
      card.append(time, detail);
      sourceList.append(card);
    }
    message.append(sourceList);
  }

  messageList.append(message);
  message.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function ask(question) {
  intro.hidden = true;
  addMessage("user", question);
  sendButton.disabled = true;
  questionInput.disabled = true;
  sendButton.innerHTML = "<span aria-hidden=\"true\">...</span>";

  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
      signal: AbortSignal.timeout(180000),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "The assistant could not answer right now.");
    addMessage("assistant", result.answer, result.sources || []);
  } catch (error) {
    addMessage("assistant", error.name === "TimeoutError"
      ? "The assistant took too long to respond. Please try again."
      : error.message || "The assistant could not connect. Please try again.", [], true);
  } finally {
    sendButton.disabled = false;
    questionInput.disabled = false;
    sendButton.innerHTML = "<span aria-hidden=\"true\">&#8593;</span>";
    questionInput.focus();
  }
}

questionForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (question.length < 3) return;
  questionInput.value = "";
  questionInput.style.height = "auto";
  ask(question);
});

questionInput.addEventListener("input", () => {
  questionInput.style.height = "auto";
  questionInput.style.height = `${Math.min(questionInput.scrollHeight, 150)}px`;
});

questionInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    questionForm.requestSubmit();
  }
});

document.querySelectorAll(".suggestion").forEach((button) => {
  button.addEventListener("click", () => {
    questionInput.value = button.dataset.question;
    questionForm.requestSubmit();
  });
});

document.querySelector("#video-filter").addEventListener("input", (event) => {
  const filter = event.target.value.trim().toLowerCase();
  for (const video of videoList.querySelectorAll(".video-link")) {
    video.hidden = !video.dataset.title.toLowerCase().includes(filter);
  }
  if (window.matchMedia("(max-width: 760px)").matches) {
    videoList.classList.toggle("is-open", filter.length > 0);
  }
});

loadCatalog();