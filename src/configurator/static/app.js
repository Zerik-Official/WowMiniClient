"use strict";

/**
 * Chat colors used by the default WoW interface, keyed by chat type.
 * @type {Record<string, string>}
 */
const CHAT_COLORS = {
  Guild: "#40ff40",
  Officer: "#40c040",
  Say: "#ffffff",
  Yell: "#ff4040",
  Emote: "#ff8040",
  Whisper: "#ff80ff",
  Party: "#aaaaff",
  Raid: "#ff7f00",
  Battleground: "#ff7f00",
  System: "#ffff00",
  Channel: "#ffc0c0",
};

/**
 * Icon shown between both sides of a relay, keyed by direction.
 * @type {Record<string, string>}
 */
const DIRECTION_ICONS = {
  both: "fa-arrows-left-right",
  wow_to_discord: "fa-arrow-right",
  discord_to_wow: "fa-arrow-left",
};

/**
 * Raw configuration being edited, as received from the server.
 * @type {Record<string, any>}
 */
const state = JSON.parse(document.getElementById("initial-config").textContent);

/**
 * Random key the server requires on every API call.
 * @type {string}
 */
const setupKey = JSON.parse(document.getElementById("setup-key").textContent);

/**
 * Read a nested value using a dotted path.
 * @param {Record<string, any>} source Object to read from.
 * @param {string} path Dotted key path such as "wow.realm".
 * @returns {any} The value, or undefined when a segment is missing.
 */
function getPath(source, path) {
  return path.split(".").reduce((node, key) => (node == null ? undefined : node[key]), source);
}

/**
 * Write a nested value using a dotted path, creating objects on the way.
 * @param {Record<string, any>} target Object to write to.
 * @param {string} path Dotted key path.
 * @param {any} value Value to store.
 * @returns {void}
 */
function setPath(target, path, value) {
  const keys = path.split(".");
  const last = keys.pop();
  let node = target;
  for (const key of keys) {
    if (typeof node[key] !== "object" || node[key] === null) {
      node[key] = {};
    }
    node = node[key];
  }
  node[last] = value;
}

/**
 * Show a message in the footer status line.
 * @param {string} message Text to show.
 * @param {"info" | "error" | "success"} tone Visual tone of the message.
 * @returns {void}
 */
function setStatus(message, tone = "info") {
  const status = document.getElementById("status");
  status.textContent = message;
  status.className = {
    info: "text-sm text-muted",
    error: "text-sm font-semibold text-danger",
    success: "text-sm font-semibold text-quest",
  }[tone];
}

/**
 * Show or hide the blocks that depend on a switch.
 * @returns {void}
 */
function syncDependents() {
  document.querySelectorAll("[data-depends]").forEach((block) => {
    block.classList.toggle("hidden", !getPath(state, block.dataset.depends));
  });
}

/**
 * Bind a switch button to a boolean value of the state.
 * @param {HTMLButtonElement} toggle Switch element with a data-path attribute.
 * @returns {void}
 */
function bindToggle(toggle) {
  const path = toggle.dataset.path;
  const render = () => toggle.setAttribute("aria-checked", String(Boolean(getPath(state, path))));
  render();
  toggle.addEventListener("click", () => {
    setPath(state, path, !getPath(state, path));
    render();
    syncDependents();
  });
}

/**
 * Bind a text, number or select field to a value of the state.
 * @param {HTMLInputElement | HTMLSelectElement} field Field with a data-path attribute.
 * @returns {void}
 */
function bindField(field) {
  const path = field.dataset.path;
  const value = getPath(state, path);
  field.value = value == null ? "" : String(value);
  field.addEventListener("input", () => {
    const raw = field.value;
    setPath(state, path, field.dataset.kind === "number" ? Number(raw) : raw);
    field.classList.remove("border-danger");
  });
}

/**
 * Turn a container into an editable list of chips bound to an array of the state.
 * @param {HTMLElement} container Element with data-path and data-placeholder attributes.
 * @returns {void}
 */
function bindChips(container) {
  const path = container.dataset.path;
  const numeric = container.hasAttribute("data-numeric");
  if (!Array.isArray(getPath(state, path))) {
    setPath(state, path, []);
  }
  container.className = "flex flex-wrap items-center gap-2 rounded-md border border-bronze/40 bg-well p-2 focus-within:border-quest";

  const input = document.createElement("input");
  input.className = "min-w-[12rem] flex-1 bg-transparent px-1 py-1 text-parchment placeholder:text-muted/60 focus:outline-none";
  input.placeholder = container.dataset.placeholder || "";
  input.setAttribute("aria-label", container.dataset.placeholder || path);

  const render = () => {
    container.querySelectorAll(".chip").forEach((chip) => chip.remove());
    getPath(state, path).forEach((item, index) => {
      const chip = document.createElement("span");
      chip.className = "chip";
      chip.textContent = item;
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "text-muted hover:text-danger";
      remove.setAttribute("aria-label", `Remove ${item}`);
      remove.innerHTML = '<i class="fa-solid fa-xmark"></i>';
      remove.addEventListener("click", () => {
        getPath(state, path).splice(index, 1);
        render();
      });
      chip.appendChild(remove);
      container.insertBefore(chip, input);
    });
  };

  const commit = () => {
    const value = input.value.trim();
    if (!value) {
      return;
    }
    if (numeric && !/^\d+$/.test(value)) {
      setStatus("Role IDs only contain digits.", "error");
      return;
    }
    getPath(state, path).push(value);
    input.value = "";
    render();
  };

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      commit();
    } else if (event.key === "Backspace" && !input.value && getPath(state, path).length) {
      getPath(state, path).pop();
      render();
    }
  });
  input.addEventListener("blur", commit);
  container.appendChild(input);
  render();
}

/**
 * Update the one-line preview of a relay.
 * @param {HTMLElement} item List item of the relay.
 * @param {Record<string, any>} entry Relay entry from the state.
 * @returns {void}
 */
function renderChannelPreview(item, entry) {
  const type = entry.wow.type || "Say";
  const label = type === "Channel" ? `[${entry.wow.channel || "channel"}]` : `[${type}]`;
  const wow = item.querySelector('[data-preview="wow"]');
  wow.textContent = `${label} [Thrall]: Lok'tar!`;
  wow.style.color = CHAT_COLORS[type] || "#ffffff";

  const direction = item.querySelector('[data-preview="direction"]');
  direction.className = `fa-solid text-muted ${DIRECTION_ICONS[entry.direction] || DIRECTION_ICONS.both}`;

  const discord = item.querySelector('[data-preview="discord"]');
  discord.textContent = `#${entry.discord.channel || "channel"}`;

  item.querySelector("[data-only-custom]").classList.toggle("hidden", type !== "Channel");
}

/**
 * Render every relay of the state into the relay list.
 * @param {number} [openIndex] Index of a relay to show expanded.
 * @returns {void}
 */
function renderChannels(openIndex) {
  const list = document.getElementById("channel-list");
  const template = document.getElementById("channel-template");
  list.innerHTML = "";

  if (!state.chat.channels.length) {
    const empty = document.createElement("li");
    empty.className = "rounded-md border border-dashed border-bronze/50 p-5 text-center text-muted";
    empty.textContent = "No relays yet. Add one to start sending chat between WoW and Discord.";
    list.appendChild(empty);
    return;
  }

  state.chat.channels.forEach((entry, index) => {
    entry.wow = entry.wow || {};
    entry.discord = entry.discord || {};
    entry.wow.type = Object.keys(CHAT_COLORS).find((key) => key.toLowerCase() === String(entry.wow.type || "say").toLowerCase()) || "Say";
    const item = template.content.firstElementChild.cloneNode(true);
    const editor = item.querySelector("[data-editor]");
    const toggle = item.querySelector('[data-action="toggle"]');

    item.querySelectorAll("[data-field]").forEach((field) => {
      const value = getPath(entry, field.dataset.field);
      field.value = value == null ? "" : String(value);
      field.addEventListener("input", () => {
        setPath(entry, field.dataset.field, field.value);
        renderChannelPreview(item, entry);
      });
    });

    const setOpen = (open) => {
      editor.classList.toggle("hidden", !open);
      toggle.setAttribute("aria-expanded", String(open));
    };
    setOpen(index === openIndex);
    toggle.addEventListener("click", () => setOpen(editor.classList.contains("hidden")));

    item.querySelector('[data-action="remove"]').addEventListener("click", () => {
      state.chat.channels.splice(index, 1);
      renderChannels();
    });

    renderChannelPreview(item, entry);
    list.appendChild(item);
  });
}

/**
 * Check required fields and highlight the empty ones.
 * @returns {boolean} True when every required field has a value.
 */
function validateRequired() {
  const empty = [...document.querySelectorAll("[data-required]")].filter((field) => {
    const missing = !field.value.trim() && field.dataset.path !== "discord.token";
    field.classList.toggle("border-danger", missing);
    return missing;
  });
  if (empty.length) {
    empty[0].focus();
    setStatus("Fill in the highlighted fields before saving.", "error");
    return false;
  }
  return true;
}

/**
 * Send a request to the setup server.
 * @param {string} url API endpoint.
 * @param {Record<string, any>} [body] JSON body to send.
 * @returns {Promise<Record<string, any>>} Parsed JSON response.
 */
async function callApi(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Setup-Key": setupKey },
    body: JSON.stringify(body || {}),
  });
  const data = await response.json().catch(() => ({ ok: false, error: `Server answered ${response.status}.` }));
  return data;
}

/**
 * Save the configuration and show the confirmation dialog.
 * @returns {Promise<void>}
 */
async function saveConfig() {
  if (!validateRequired()) {
    return;
  }
  const button = document.getElementById("save");
  button.disabled = true;
  setStatus("Saving...");
  try {
    const result = await callApi("/api/config", state);
    if (!result.ok) {
      setStatus(result.error, "error");
      return;
    }
    setStatus(`Saved to ${result.path}`, "success");
    const done = document.getElementById("done");
    done.classList.replace("hidden", "flex");
    document.getElementById("finish").focus();
  } catch (error) {
    setStatus("The setup server is not reachable. Start it again from the console.", "error");
  } finally {
    button.disabled = false;
  }
}

/**
 * Stop the setup server and replace the page with a closing message.
 * @returns {Promise<void>}
 */
async function closeSetup() {
  try {
    await callApi("/api/close");
  } catch (error) {
    setStatus("The setup server was already stopped.", "info");
  }
  document.body.innerHTML =
    '<main class="flex min-h-screen items-center justify-center p-6 text-center">' +
    '<div><h1 class="font-display text-3xl text-quest">Setup closed</h1>' +
    '<p class="mt-2 text-muted">You can close this tab. Run <code>python src/configure.py</code> to edit the settings again.</p></div></main>';
}

/**
 * Show or hide a password field.
 * @param {HTMLButtonElement} button Button with a data-reveal attribute naming the field.
 * @returns {void}
 */
function bindReveal(button) {
  const field = document.getElementById(button.dataset.reveal);
  button.addEventListener("click", () => {
    const hidden = field.type === "password";
    field.type = hidden ? "text" : "password";
    button.querySelector("i").className = hidden ? "fa-solid fa-eye-slash" : "fa-solid fa-eye";
  });
}

document.querySelectorAll("button.toggle[data-path]").forEach(bindToggle);
document.querySelectorAll("input[data-path], select[data-path]").forEach(bindField);
document.querySelectorAll(".chips[data-path]").forEach(bindChips);
document.querySelectorAll("[data-reveal]").forEach(bindReveal);
syncDependents();
renderChannels();

document.getElementById("add-channel").addEventListener("click", () => {
  state.chat.channels.push({
    direction: "both",
    wow: { type: "Guild", format: "%message" },
    discord: { channel: "", format: "[%user]: %message" },
  });
  renderChannels(state.chat.channels.length - 1);
});
document.getElementById("save").addEventListener("click", saveConfig);
document.getElementById("close-setup").addEventListener("click", closeSetup);
document.getElementById("finish").addEventListener("click", closeSetup);
document.getElementById("keep-editing").addEventListener("click", () => {
  document.getElementById("done").classList.replace("flex", "hidden");
});
