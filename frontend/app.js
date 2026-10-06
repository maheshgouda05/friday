const state = {
  tasks: [],
  events: [],
  profile: null,
  taskFilter: "all",
  conversations: [],
  currentConversation: null,
};

const elements = {
  taskList: document.querySelector("#task-list"),
  eventList: document.querySelector("#event-list"),
  taskForm: document.querySelector("#task-form"),
  eventForm: document.querySelector("#event-form"),
  profileForm: document.querySelector("#profile-form"),
  chatForm: document.querySelector("#chat-form"),
  chatInput: document.querySelector("#chat-input"),
  chatMessages: document.querySelector("#chat-messages"),
  conversationList: document.querySelector("#conversation-list"),
  toast: document.querySelector("#toast"),
};

let toastTimer;
let activeRecognition = null;

async function apiRequest(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload?.detail;
    const message = Array.isArray(detail)
      ? detail.map((item) => item.msg).join("; ")
      : detail || `Request failed (${response.status})`;
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  return payload;
}

function showToast(message, isError = false) {
  elements.toast.textContent = message;
  elements.toast.classList.toggle("is-error", isError);
  elements.toast.classList.add("is-visible");
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => {
    elements.toast.classList.remove("is-visible");
  }, 3200);
}

function setTodayLabel() {
  const now = new Date();
  document.querySelector("#current-date").textContent = new Intl.DateTimeFormat(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  }).format(now).toUpperCase();
}

function createEmptyState(message) {
  const item = document.createElement("li");
  item.className = "empty-state";
  item.textContent = message;
  return item;
}

function updateTaskSummary() {
  const completedCount = state.tasks.filter((task) => task.completed).length;
  const openCount = state.tasks.length - completedCount;
  const progress = state.tasks.length ? Math.round((completedCount / state.tasks.length) * 100) : 0;

  document.querySelector("#tasks-complete").textContent = String(completedCount);
  document.querySelector("#tasks-total").textContent = `of ${state.tasks.length}`;
  document.querySelector("#open-task-count").textContent = String(openCount);
  document.querySelector("#task-progress").style.width = `${progress}%`;
}

function renderTasks() {
  elements.taskList.replaceChildren();
  const visibleTasks = state.tasks.filter((task) => {
    if (state.taskFilter === "open") return !task.completed;
    if (state.taskFilter === "done") return task.completed;
    return true;
  });

  if (!visibleTasks.length) {
    const message = state.tasks.length ? "Nothing in this view." : "No tasks yet. Add one small thing to get started.";
    elements.taskList.append(createEmptyState(message));
  }

  for (const task of visibleTasks) {
    const item = document.createElement("li");
    item.className = `task-item${task.completed ? " is-complete" : ""}`;

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "task-check";
    checkbox.checked = task.completed;
    checkbox.setAttribute("aria-label", `${task.completed ? "Reopen" : "Complete"} ${task.title}`);
    checkbox.addEventListener("change", () => toggleTask(task));

    const copy = document.createElement("div");
    copy.className = "task-copy";
    const title = document.createElement("p");
    title.className = "task-title";
    title.textContent = task.title;
    copy.append(title);
    if (task.description) {
      const description = document.createElement("p");
      description.className = "task-description";
      description.textContent = task.description;
      copy.append(description);
    }

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "text-action";
    deleteButton.textContent = "Delete";
    deleteButton.setAttribute("aria-label", `Delete ${task.title}`);
    deleteButton.addEventListener("click", () => deleteTask(task));

    item.append(checkbox, copy, deleteButton);
    elements.taskList.append(item);
  }

  updateTaskSummary();
}

async function toggleTask(task) {
  try {
    if (task.completed) {
      await apiRequest(`/tasks/${task.id}`, {
        method: "PUT",
        body: JSON.stringify({ completed: false }),
      });
    } else {
      await apiRequest(`/tasks/${task.id}/complete`, { method: "PATCH" });
    }
    await loadTasks();
  } catch (error) {
    showToast(error.message, true);
    await loadTasks();
  }
}

async function deleteTask(task) {
  if (!window.confirm(`Delete “${task.title}”? This cannot be undone.`)) return;
  try {
    await apiRequest(`/tasks/${task.id}`, { method: "DELETE" });
    await loadTasks();
    showToast("Task deleted.");
  } catch (error) {
    showToast(error.message, true);
  }
}

async function loadTasks() {
  state.tasks = await apiRequest("/tasks/");
  renderTasks();
}

function formatEventDate(dateValue) {
  const date = new Date(`${dateValue}T12:00:00`);
  return {
    day: new Intl.DateTimeFormat(undefined, { day: "numeric" }).format(date),
    month: new Intl.DateTimeFormat(undefined, { month: "short" }).format(date),
    full: new Intl.DateTimeFormat(undefined, { weekday: "short", month: "short", day: "numeric" }).format(date),
  };
}

function formatEventTime(timeValue) {
  if (!timeValue) return "Time not set";
  const [hours, minutes] = timeValue.split(":").map(Number);
  const date = new Date();
  date.setHours(hours, minutes, 0, 0);
  return new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(date);
}

function renderEvents() {
  const today = new Date().toISOString().slice(0, 10);
  const upcoming = state.events
    .filter((event) => event.status === "upcoming" && event.date >= today)
    .slice(0, 5);
  elements.eventList.replaceChildren();
  document.querySelector("#event-count").textContent = String(upcoming.length);

  if (!upcoming.length) {
    elements.eventList.append(createEmptyState("Nothing coming up. Add an event when you’re ready."));
  }

  for (const event of upcoming) {
    const item = document.createElement("li");
    item.className = "event-item";
    const date = formatEventDate(event.date);

    const dateBadge = document.createElement("div");
    dateBadge.className = "event-date";
    const day = document.createElement("strong");
    day.textContent = date.day;
    const month = document.createElement("span");
    month.textContent = date.month;
    dateBadge.append(day, month);

    const copy = document.createElement("div");
    copy.className = "event-copy";
    const title = document.createElement("p");
    title.className = "event-title";
    title.textContent = event.title;
    const meta = document.createElement("p");
    meta.className = "event-meta";
    meta.textContent = `${date.full} · ${formatEventTime(event.time)}`;
    const type = document.createElement("span");
    type.className = "event-type";
    type.textContent = event.event_type.replaceAll("_", " ");
    copy.append(title, meta, type);

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "event-delete";
    deleteButton.textContent = "×";
    deleteButton.setAttribute("aria-label", `Delete event ${event.title}`);
    deleteButton.addEventListener("click", () => deleteEvent(event));

    item.append(dateBadge, copy, deleteButton);
    elements.eventList.append(item);
  }

  const nextEvent = upcoming[0];
  document.querySelector("#next-event").textContent = nextEvent?.title || "Nothing scheduled";
  document.querySelector("#next-event-time").textContent = nextEvent
    ? `${formatEventDate(nextEvent.date).full} · ${formatEventTime(nextEvent.time)}`
    : "Add an event to see it here";
}

async function loadEvents() {
  state.events = await apiRequest("/events/");
  renderEvents();
}

async function deleteEvent(event) {
  if (!window.confirm(`Delete “${event.title}”? This cannot be undone.`)) return;
  try {
    await apiRequest(`/events/${event.id}?confirm=true`, { method: "DELETE" });
    await loadEvents();
    showToast("Event deleted.");
  } catch (error) {
    showToast(error.message, true);
  }
}

function splitList(value) {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

function fillProfileForm(profile) {
  const form = elements.profileForm.elements;
  form.name.value = profile?.name || "";
  form.preferred_name.value = profile?.preferred_name || "";
  form.timezone.value = profile?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  form.daily_wake_time.value = profile?.daily_wake_time?.slice(0, 5) || "";
  form.usual_sleep_time.value = profile?.usual_sleep_time?.slice(0, 5) || "";
  form.interests.value = profile?.interests?.join(", ") || "";
  form.learning_goals.value = profile?.learning_goals?.join(", ") || "";
  form.personal_goals.value = profile?.personal_goals?.join(", ") || "";
  form.communication_style.value = profile?.communication_style || "";

  document.querySelector("#profile-submit").textContent = profile ? "Save changes" : "Create profile";
  document.querySelector("#profile-intro").textContent = profile
    ? "Keep your preferences and goals up to date."
    : "Set a few details so FRIDAY can keep your preferences together.";
  document.querySelector("#welcome-name").textContent = profile
    ? `Good to see you, ${profile.preferred_name || profile.name}.`
    : "Welcome to FRIDAY.";
  document.querySelector("#welcome-detail").textContent = profile?.preferred_name
    ? "Your day, at a glance."
    : profile?.name || "Your day, at a glance.";
}

async function loadProfile() {
  try {
    state.profile = await apiRequest("/profile");
    fillProfileForm(state.profile);
  } catch (error) {
    if (error.status === 404) {
      state.profile = null;
      fillProfileForm(null);
      return;
    }
    throw error;
  }
}

async function handleTaskSubmit(event) {
  event.preventDefault();
  const formData = new FormData(elements.taskForm);
  const payload = {
    title: formData.get("title"),
    description: formData.get("description") || null,
  };
  try {
    await apiRequest("/tasks/", { method: "POST", body: JSON.stringify(payload) });
    elements.taskForm.reset();
    await loadTasks();
    showToast("Task added.");
  } catch (error) {
    showToast(error.message, true);
  }
}

async function handleEventSubmit(event) {
  event.preventDefault();
  const formData = new FormData(elements.eventForm);
  const payload = {
    title: formData.get("title"),
    date: formData.get("date"),
    time: formData.get("time") || null,
    event_type: formData.get("event_type"),
    location: formData.get("location") || null,
  };
  try {
    await apiRequest("/events/", { method: "POST", body: JSON.stringify(payload) });
    elements.eventForm.reset();
    await loadEvents();
    showToast("Event added.");
  } catch (error) {
    showToast(error.message, true);
  }
}

async function handleProfileSubmit(event) {
  event.preventDefault();
  const formData = new FormData(elements.profileForm);
  const payload = {
    name: formData.get("name"),
    preferred_name: formData.get("preferred_name") || null,
    timezone: formData.get("timezone"),
    daily_wake_time: formData.get("daily_wake_time") || null,
    usual_sleep_time: formData.get("usual_sleep_time") || null,
    interests: splitList(formData.get("interests")),
    learning_goals: splitList(formData.get("learning_goals")),
    personal_goals: splitList(formData.get("personal_goals")),
    communication_style: formData.get("communication_style") || null,
  };

  const status = document.querySelector("#profile-save-status");
  status.textContent = "Saving…";
  try {
    const method = state.profile ? "PATCH" : "POST";
    state.profile = await apiRequest("/profile", { method, body: JSON.stringify(payload) });
    fillProfileForm(state.profile);
    status.textContent = "Saved just now";
    showToast("Profile saved.");
  } catch (error) {
    status.textContent = "Not saved";
    showToast(error.message, true);
  }
}

function formatMessageTime(timestamp) {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return "";
  const options = localDateKey(date) === localDateKey(new Date())
    ? { hour: "numeric", minute: "2-digit" }
    : { dateStyle: "medium", timeStyle: "short" };
  return new Intl.DateTimeFormat(undefined, {
    ...options,
    timeZone: state.profile?.timezone || "Asia/Kolkata",
  }).format(date);
}

function appendChatMessage(role, content, createdAt, isError = false) {
  const message = document.createElement("article");
  message.className = `chat-message ${role === "user" ? "user-message" : "assistant-message"}${isError ? " error-message" : ""}`;

  const sender = document.createElement("span");
  sender.className = "message-sender";
  sender.textContent = role === "user" ? "YOU" : "FRIDAY";

  const text = document.createElement("p");
  text.className = "message-content";
  text.textContent = content;
  message.append(sender, text);
  if (createdAt) {
    const timestamp = document.createElement("time");
    timestamp.className = "message-time";
    timestamp.dateTime = createdAt;
    timestamp.textContent = formatMessageTime(createdAt);
    message.append(timestamp);
  }
  elements.chatMessages.append(message);
  elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

function renderConversationMessages(messages = []) {
  elements.chatMessages.replaceChildren();
  if (!messages.length) {
    const empty = document.createElement("p");
    empty.className = "conversation-empty-state";
    empty.textContent = "Start a conversation. FRIDAY will keep it here for next time.";
    elements.chatMessages.append(empty);
    return;
  }
  for (const message of messages) {
    appendChatMessage(message.role, message.content, message.created_at);
  }
}

function localDateKey(date) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: state.profile?.timezone || "Asia/Kolkata",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date);
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}

function conversationGroup(conversation) {
  const messageDate = new Date(conversation.last_message_at || conversation.created_at);
  const today = localDateKey(new Date());
  const yesterdayDate = new Date();
  yesterdayDate.setDate(yesterdayDate.getDate() - 1);
  const yesterday = localDateKey(yesterdayDate);
  const key = localDateKey(messageDate);
  if (key === today) return "Today";
  if (key === yesterday) return "Yesterday";
  return "Older";
}

function renderConversationList() {
  elements.conversationList.replaceChildren();
  if (!state.conversations.length) {
    const empty = document.createElement("p");
    empty.className = "conversation-empty";
    empty.textContent = "Your saved chats will appear here.";
    elements.conversationList.append(empty);
    return;
  }

  let currentGroup = "";
  for (const conversation of state.conversations) {
    const group = conversationGroup(conversation);
    if (group !== currentGroup) {
      const heading = document.createElement("p");
      heading.className = "conversation-group-title";
      heading.textContent = group;
      elements.conversationList.append(heading);
      currentGroup = group;
    }

    const item = document.createElement("div");
    item.className = `conversation-item${conversation.id === state.currentConversation?.id ? " is-current" : ""}`;
    const openButton = document.createElement("button");
    openButton.type = "button";
    openButton.className = "conversation-open";
    openButton.textContent = conversation.title;
    openButton.title = conversation.title;
    openButton.setAttribute("aria-current", conversation.id === state.currentConversation?.id ? "page" : "false");
    openButton.addEventListener("click", () => openConversation(conversation.id));

    const archiveButton = document.createElement("button");
    archiveButton.type = "button";
    archiveButton.className = "conversation-archive";
    archiveButton.textContent = "×";
    archiveButton.title = `Archive ${conversation.title}`;
    archiveButton.setAttribute("aria-label", `Archive ${conversation.title}`);
    archiveButton.addEventListener("click", () => archiveConversation(conversation));

    item.append(openButton, archiveButton);
    elements.conversationList.append(item);
  }
}

async function refreshConversationList() {
  state.conversations = await apiRequest("/conversations");
  renderConversationList();
}

async function openConversation(conversationId) {
  try {
    state.currentConversation = await apiRequest(`/conversations/${conversationId}`);
    localStorage.setItem("friday.currentConversationId", conversationId);
    document.querySelector("#conversation-title").textContent = state.currentConversation.title;
    renderConversationMessages(state.currentConversation.messages);
    renderConversationList();
  } catch (error) {
    showToast(error.message, true);
  }
}

async function createNewConversation() {
  try {
    state.currentConversation = await apiRequest("/conversations", { method: "POST" });
    localStorage.setItem("friday.currentConversationId", state.currentConversation.id);
    document.querySelector("#conversation-title").textContent = state.currentConversation.title;
    renderConversationMessages();
    await refreshConversationList();
    elements.chatInput.focus();
  } catch (error) {
    showToast(error.message, true);
  }
}

async function archiveConversation(conversation) {
  try {
    await apiRequest(`/conversations/${conversation.id}`, { method: "DELETE" });
    if (state.currentConversation?.id === conversation.id) {
      state.currentConversation = null;
      localStorage.removeItem("friday.currentConversationId");
      document.querySelector("#conversation-title").textContent = "New Chat";
      renderConversationMessages();
    }
    await refreshConversationList();
    showToast("Conversation archived.");
  } catch (error) {
    showToast(error.message, true);
  }
}

async function loadConversations() {
  await refreshConversationList();
  const savedId = localStorage.getItem("friday.currentConversationId");
  const selected = state.conversations.find((item) => item.id === savedId) || state.conversations[0];
  if (selected) {
    await openConversation(selected.id);
  } else {
    state.currentConversation = null;
    localStorage.removeItem("friday.currentConversationId");
    document.querySelector("#conversation-title").textContent = "New Chat";
    renderConversationMessages();
  }
}

function speakReply(text) {
  if (!document.querySelector("#speak-replies").checked) return;
  if (!("speechSynthesis" in window) || !("SpeechSynthesisUtterance" in window)) {
    document.querySelector("#chat-hint").textContent = "Speech output is not supported by this browser. The reply is available above.";
    return;
  }

  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.onerror = () => {
    document.querySelector("#chat-hint").textContent = "Could not play speech. The reply is available above.";
  };
  window.speechSynthesis.speak(utterance);
}

async function handleChatSubmit(event) {
  event.preventDefault();
  const message = elements.chatInput.value.trim();
  if (!message) return;

  const sendButton = document.querySelector("#send-chat");
  const status = document.querySelector("#chat-status");
  elements.chatInput.value = "";
  sendButton.disabled = true;
  status.textContent = "FRIDAY is thinking…";
  status.classList.add("is-busy");

  try {
    if (!state.currentConversation) {
      state.currentConversation = await apiRequest("/conversations", { method: "POST" });
      localStorage.setItem("friday.currentConversationId", state.currentConversation.id);
    }
    const conversationId = state.currentConversation.id;
    await apiRequest(`/conversations/${conversationId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content: message }),
    });
    await openConversation(conversationId);
    await refreshConversationList();
    status.textContent = "Ready";
    const lastAssistantMessage = [...(state.currentConversation?.messages || [])]
      .reverse()
      .find((item) => item.role === "assistant");
    if (lastAssistantMessage) speakReply(lastAssistantMessage.content);
  } catch (error) {
    status.textContent = "Could not respond";
    showToast(error.message, true);
    if (state.currentConversation) await openConversation(state.currentConversation.id);
  } finally {
    sendButton.disabled = false;
    status.classList.remove("is-busy");
  }
}

function initializeVoiceInput() {
  const voiceButton = document.querySelector("#voice-input");
  const hint = document.querySelector("#chat-hint");
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  if (!SpeechRecognition) {
    voiceButton.disabled = true;
    voiceButton.title = "Speech recognition is not supported by this browser";
    hint.textContent = "Voice input is not supported by this browser. You can still type and receive spoken replies.";
    return;
  }

  voiceButton.addEventListener("click", () => {
    if (activeRecognition) {
      activeRecognition.stop();
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = state.profile?.language || navigator.language || "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    activeRecognition = recognition;
    voiceButton.textContent = "Listening…";
    voiceButton.setAttribute("aria-pressed", "true");
    hint.textContent = "Listening. Speak clearly, then FRIDAY will send the recognized message.";
    document.querySelector("#chat-status").textContent = "Listening";

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript.trim();
      if (!transcript) return;
      elements.chatInput.value = transcript;
      elements.chatForm.requestSubmit();
    };
    recognition.onerror = (event) => {
      const message = event.error === "not-allowed"
        ? "Microphone permission was denied. Allow microphone access in your browser settings."
        : "Voice input stopped. You can type your message instead.";
      hint.textContent = message;
    };
    recognition.onend = () => {
      activeRecognition = null;
      voiceButton.textContent = "Use microphone";
      voiceButton.setAttribute("aria-pressed", "false");
      document.querySelector("#chat-status").textContent = "Ready";
    };

    try {
      recognition.start();
    } catch {
      activeRecognition = null;
      voiceButton.textContent = "Use microphone";
      voiceButton.setAttribute("aria-pressed", "false");
      hint.textContent = "Could not start the microphone. Check browser permission and try again.";
    }
  });
}

async function loadDashboard() {
  setTodayLabel();
  const results = await Promise.allSettled([loadTasks(), loadEvents(), loadProfile()]);
  const profileFailure = results[2];
  if (profileFailure.status === "rejected") showToast(profileFailure.reason.message, true);
  const conversationResult = await loadConversations().then(
    () => ({ status: "fulfilled" }),
    (reason) => ({ status: "rejected", reason }),
  );
  if (conversationResult.status === "rejected") showToast(conversationResult.reason.message, true);
}

elements.taskForm.addEventListener("submit", handleTaskSubmit);
elements.eventForm.addEventListener("submit", handleEventSubmit);
elements.profileForm.addEventListener("submit", handleProfileSubmit);
elements.chatForm.addEventListener("submit", handleChatSubmit);
document.querySelector("#new-chat").addEventListener("click", createNewConversation);
elements.chatInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    elements.chatForm.requestSubmit();
  }
});
document.querySelector("#stop-speaking").addEventListener("click", () => {
  if ("speechSynthesis" in window) window.speechSynthesis.cancel();
});

for (const button of document.querySelectorAll("[data-task-filter]")) {
  button.addEventListener("click", () => {
    state.taskFilter = button.dataset.taskFilter;
    document.querySelectorAll("[data-task-filter]").forEach((filterButton) => {
      filterButton.classList.toggle("is-selected", filterButton === button);
    });
    renderTasks();
  });
}

for (const link of document.querySelectorAll(".nav-link")) {
  link.addEventListener("click", () => {
    document.querySelectorAll(".nav-link").forEach((navLink) => {
      navLink.classList.toggle("is-active", navLink === link);
    });
  });
}

loadDashboard();
initializeVoiceInput();