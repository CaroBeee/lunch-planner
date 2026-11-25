/**
 * Lunch Planner – 7-Day Family Meal Planner
 * Frontend JavaScript (vanilla)
 */

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let currentPlan = []; // array of 7 day entries
let currentDates = {}; // { start, end, days }
let swapDayIndex = null; // index of the day being swapped
let detailEditIndex = null;
let editingFreeIndex = null; // index of free card being edited
let excludeRules = {}; // current exclude list data
let builderDayIndex = null;
let ingredientsData = [];
let selectedWeekOffset = 0; // 0 = this week, 1 = next week

const DIET_LABELS = {
  meat: { label: "Fleisch", emoji: "🥩", class: "badge-meat" },
  fish: { label: "Fisch", emoji: "🐟", class: "badge-fish" },
  vegetarian: { label: "Veggie", emoji: "🥦", class: "badge-vegetarian" },
  vegan: { label: "Vegan", emoji: "🌱", class: "badge-vegan" },
  free: { label: "Frei", emoji: "🎫", class: "badge-free" },
};

const DAYS_DE = [
  "Montag",
  "Dienstag",
  "Mittwoch",
  "Donnerstag",
  "Freitag",
  "Samstag",
  "Sonntag",
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function $(sel) {
  return document.querySelector(sel);
}
function $$(sel) {
  return document.querySelectorAll(sel);
}

function showLoading(text) {
  $(".spinner-text").textContent = text || "Wird geladen…";
  $("#loading-overlay").classList.remove("hidden");
}
function hideLoading() {
  $("#loading-overlay").classList.add("hidden");
}

/**
 * Show a toast notification.
 * @param {string} message  – Text to display
 * @param {string} type     – "success" | "error" | "info" | "warning" | "quota" | "key" | "network" | "offline"
 * @param {number} [duration] – ms before fade-out (default varies by type)
 */
function showToast(message, type = "success", duration) {
  const container = $("#toast-container");
  const toast = document.createElement("div");
  // map semantic types to CSS classes
  const cssClass =
    {
      success: "toast-success",
      error: "toast-error",
      info: "toast-info",
      warning: "toast-warning",
      quota: "toast-quota",
      key: "toast-key",
      network: "toast-network",
      offline: "toast-offline",
    }[type] || "toast-error";
  toast.className = `toast ${cssClass}`;
  toast.innerHTML = message; // allow emoji/HTML
  const dur = duration || (type === "success" ? 3000 : 6000);
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transition = "opacity 0.4s";
  }, dur);
  setTimeout(() => toast.remove(), dur + 500);
}

/**
 * Map an API error_type to a user-friendly German toast.
 */
const API_ERROR_MESSAGES = {
  quota_exceeded: {
    text: "⚠️ Dein Spoonacular API-Kontingent ist aufgebraucht. Die App nutzt jetzt gecachte Rezepte. Versuche es morgen erneut.",
    toast: "quota",
  },
  invalid_key: {
    text: "🔑 Ungültiger API-Key. Bitte überprüfe deinen Spoonacular API-Key in der Konfiguration.",
    toast: "key",
  },
  service_unavailable: {
    text: "🌐 Spoonacular API ist momentan nicht verfügbar. Offline-Modus aktiv.",
    toast: "offline",
  },
  network_error: {
    text: "📡 Keine Verbindung zur Spoonacular API möglich. Bitte überprüfe deine Internetverbindung.",
    toast: "network",
  },
};

function showApiError(data) {
  const errorType = data.error_type || "unknown";
  const mapping = API_ERROR_MESSAGES[errorType];
  if (mapping) {
    let msg = mapping.text;
    if (data.used_fallback && data.cached_count > 0) {
      msg += `<br><small>ℹ️ ${data.cached_count} gecachte Rezepte werden verwendet.</small>`;
    }
    showToast(msg, mapping.toast);
  } else {
    showToast(
      `❌ API-Fehler: ${data.message || "Unbekannter Fehler"}`,
      "error",
    );
  }
}

function openModal(id) {
  document.getElementById(id).classList.remove("hidden");
}
function closeModal(id) {
  document.getElementById(id).classList.add("hidden");
}

async function apiCall(url, options = {}) {
  const resp = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await resp.json();
  if (!data.success) throw new Error(data.error || "Unbekannter Fehler");
  return data;
}

function getTimeBadge(minutes) {
  if (!minutes || minutes === 0) return "";
  let cls = "time-quick",
    label = "Schnell";
  if (minutes > 45) {
    cls = "time-long";
    label = `${minutes} Min`;
  } else if (minutes > 25) {
    cls = "time-medium";
    label = `${minutes} Min`;
  } else {
    label = `${minutes} Min`;
  }
  return `<span class="card-time-badge ${cls}">⏱️ ${label}</span>`;
}

function getDietBadgeHTML(dietType) {
  const info = DIET_LABELS[dietType] || DIET_LABELS.vegetarian;
  return `<span class="card-diet-badge ${info.class}">${info.emoji} ${info.label}</span>`;
}

function getImageSrc(entry) {
  if (entry.image && entry.image.startsWith("http")) return entry.image;
  if (entry.image && entry.image.length > 5)
    return `https://miro.medium.com/v2/resize:fit:1400/1*WHfZH2ok8Ti2uIYoeslm6Q.jpeg || "jpg"}`;
  return "";
}

function getPlaceholderEmoji(dietType) {
  const emojis = {
    meat: "🥩",
    fish: "🐟",
    vegetarian: "🥗",
    vegan: "🌱",
    free: "🎫",
  };
  return emojis[dietType] || "🍽️";
}

// ---------------------------------------------------------------------------
// Render functions
// ---------------------------------------------------------------------------

function renderDateRange() {
  if (currentDates.start) {
    $("#date-range").textContent =
      `${currentDates.start} – ${currentDates.end}`;
  }
}

function getDayMeta(idx) {
  const day =
    currentDates.days && currentDates.days[idx] ? currentDates.days[idx] : null;
  return {
    day_name: day ? day.name : DAYS_DE[idx],
    day_index: idx,
    date: day
      ? day.date
      : currentPlan[idx] && currentPlan[idx].date
        ? currentPlan[idx].date
        : "",
  };
}

function normalizePlanDayMeta(slotMeta = null) {
  currentPlan = currentPlan.map((entry, idx) => ({
    ...entry,
    ...(slotMeta && slotMeta[idx] ? slotMeta[idx] : getDayMeta(idx)),
  }));
}

function renderDietOverview() {
  const counts = {};
  currentPlan.forEach((entry) => {
    const dt = entry.diet_type || "vegetarian";
    counts[dt] = (counts[dt] || 0) + 1;
  });
  const container = $("#diet-overview");
  container.innerHTML = "";
  for (const [dt, count] of Object.entries(counts)) {
    const info = DIET_LABELS[dt] || DIET_LABELS.vegetarian;
    const badge = document.createElement("span");
    badge.className = "diet-badge";
    badge.textContent = `${info.emoji} ${count}× ${info.label}`;
    container.appendChild(badge);
  }
}

function renderPlan() {
  const grid = $("#plan-grid");
  grid.innerHTML = "";

  if (!currentPlan || currentPlan.length === 0) {
    grid.innerHTML = `
            <div class="empty-state" id="empty-state">
                <div class="empty-icon">🍳</div>
                <h2>Noch kein Plan erstellt</h2>
                <p>Klicke auf <strong>„Neuer Plan"</strong>, um deinen 7-Tage Mittagsplan zu generieren.</p>
                <button class="btn btn-primary btn-lg" id="btn-generate-empty">
                    <span class="btn-icon">🔄</span> Plan generieren
                </button>
            </div>`;
    const btn = $("#btn-generate-empty");
    if (btn) btn.addEventListener("click", () => openGenerateModal());
    return;
  }

  currentPlan.forEach((entry, idx) => {
    const isFree = entry.source === "free" || entry.diet_type === "free";
    const isCustom = entry.source === "custom";
    const card = document.createElement("div");
    card.className = `day-card${isFree ? " free-card" : ""}`;

    const imgSrc = getImageSrc(entry);
    const imageHTML = imgSrc
      ? `<img class="card-image" src="${imgSrc}" alt="${entry.title}" loading="lazy" onerror="this.outerHTML='<div class=\\'card-image-placeholder\\'>${getPlaceholderEmoji(entry.diet_type)}</div>'">`
      : `<div class="card-image-placeholder">${getPlaceholderEmoji(entry.diet_type)}</div>`;

    const timeHTML = entry.readyInMinutes
      ? getTimeBadge(entry.readyInMinutes)
      : "";
    const noteText = entry.note || entry.description || "";
    const descHTML = noteText
      ? `<p class="card-description">${noteText}</p>`
      : "";
    const dayOptions = DAYS_DE.map(
      (day, dayIdx) =>
        `<option value="${dayIdx}" ${dayIdx === idx ? "selected" : ""}>${day}</option>`,
    ).join("");

    let detailBtn = `<button class="btn btn-secondary btn-details" data-idx="${idx}"><span class="btn-icon">✏️</span> <span class="btn-text">Details</span></button>`;
    if (isFree) {
      detailBtn += `<button class="btn btn-primary btn-create-dish" data-idx="${idx}"><span class="btn-icon">🍳</span> <span class="btn-text">Gericht erstellen</span></button>`;
    } else if (isCustom) {
      detailBtn += `<button class="btn btn-secondary btn-create-dish" data-idx="${idx}"><span class="btn-icon">✏️</span> <span class="btn-text">Bearbeiten</span></button>`;
    }

    card.innerHTML = `
            <div class="card-header">
                <div>
                    <span class="card-day">${entry.day_name || DAYS_DE[idx]}</span>
                    <span class="card-date">${entry.date || ""}</span>
                </div>
                ${getDietBadgeHTML(entry.diet_type)}
            </div>
            ${imageHTML}
            <div class="card-body">
                <div class="card-title">${entry.title}</div>
                <div class="card-meta">${timeHTML}</div>
                ${descHTML}
                <div class="card-actions">
                    ${detailBtn}
                    <button class="btn btn-primary btn-swap" data-idx="${idx}"><span class="btn-icon">🔁</span> <span class="btn-text">Tauschen</span></button>
                </div>
                <div class="card-day-move">
                    <label class="card-day-move-label" for="card-day-select-${idx}">Wochentag</label>
                    <select class="card-day-select" id="card-day-select-${idx}" data-idx="${idx}">${dayOptions}</select>
                </div>
            </div>`;
    grid.appendChild(card);
  });

  // Attach card event listeners
  $$(".btn-details").forEach((btn) =>
    btn.addEventListener("click", (e) => {
      openDetailsModal(parseInt(e.currentTarget.dataset.idx));
    }),
  );
  $$(".btn-swap").forEach((btn) =>
    btn.addEventListener("click", (e) => {
      openSwapModal(parseInt(e.currentTarget.dataset.idx));
    }),
  );
  $$(".btn-create-dish").forEach((btn) =>
    btn.addEventListener("click", (e) => {
      openDishBuilder(parseInt(e.currentTarget.dataset.idx));
    }),
  );
  $$(".card-day-select").forEach((select) =>
    select.addEventListener("change", (e) => {
      moveDishToDay(
        parseInt(e.currentTarget.dataset.idx),
        parseInt(e.currentTarget.value),
      );
    }),
  );

  renderDietOverview();
}

// ---------------------------------------------------------------------------
// Generate plan
// ---------------------------------------------------------------------------

function openGenerateModal() {
  const picker = $("#free-day-picker");
  picker.innerHTML = "";
  DAYS_DE.forEach((day, i) => {
    const btn = document.createElement("button");
    btn.className = "free-day-btn";
    btn.textContent = day;
    btn.dataset.idx = i;
    btn.addEventListener("click", () => btn.classList.toggle("selected"));
    picker.appendChild(btn);
  });
  const sourceMode = $("#generate-source-mode");
  if (sourceMode) sourceMode.value = "all";
  $$(".week-tab").forEach((tab) => {
    tab.classList.toggle(
      "active",
      parseInt(tab.dataset.offset) === selectedWeekOffset,
    );
    tab.addEventListener("click", () => {
      selectedWeekOffset = parseInt(tab.dataset.offset);
      $$(".week-tab").forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
    });
  });
  openModal("modal-generate");
}

async function generatePlan() {
  const selected = [...$$("#free-day-picker .free-day-btn.selected")].map((b) =>
    parseInt(b.dataset.idx),
  );
  const sourceMode = $("#generate-source-mode")?.value || "all";
  closeModal("modal-generate");
  showLoading("Plan wird generiert…");
  try {
    const resp = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        free_days: selected,
        week_offset: selectedWeekOffset,
        include_api_recipes: sourceMode !== "fixed_only",
      }),
    });
    const data = await resp.json();
    if (!data.success) {
      if (data.error_type) {
        showApiError(data);
      } else {
        showToast(`❌ ${data.error || "Fehler beim Generieren"}`, "error");
      }
      return;
    }
    currentPlan = data.plan;
    const dateData = await apiCall(
      `/api/week-dates?week_offset=${selectedWeekOffset}`,
    );
    currentDates = dateData.dates;
    normalizePlanDayMeta();
    renderDateRange();
    renderPlan();
    showToast("Neuer Plan wurde erstellt! 🎉");
  } catch (err) {
    showToast("📡 Netzwerkfehler: " + err.message, "network");
  } finally {
    hideLoading();
  }
}

// ---------------------------------------------------------------------------
// Details modal
// ---------------------------------------------------------------------------

function openDetailsModal(idx) {
  const entry = currentPlan[idx];
  if (!entry) return;

  detailEditIndex = idx;

  const imgSrc = getImageSrc(entry);
  const imgEl = $("#detail-image");
  if (imgSrc) {
    imgEl.src = imgSrc;
    imgEl.alt = entry.title;
    imgEl.style.display = "";
  } else {
    imgEl.style.display = "none";
  }

  $("#detail-title-input").value = entry.title || "";
  $("#detail-diet-type").value = entry.diet_type || "vegetarian";
  $("#detail-servings-input").value = entry.servings || 0;
  $("#detail-note").value = entry.note || entry.description || "";

  const ingredients = entry.ingredients || [];
  if (ingredients.length === 0 && entry.extendedIngredients) {
    const fallbackIngredients = entry.extendedIngredients
      .map((ing) => ing.original || ing.originalString || ing.name || "")
      .filter(Boolean);
    $("#detail-ingredients-text").value = fallbackIngredients.join("\n");
  } else {
    $("#detail-ingredients-text").value = ingredients.join("\n");
  }

  $("#detail-instructions").value = entry.instructions_text || "";

  openModal("modal-details");
}

function saveDetailsEdit() {
  if (detailEditIndex === null) return;
  const entry = { ...currentPlan[detailEditIndex] };

  const title = $("#detail-title-input").value.trim();
  const dietType = $("#detail-diet-type").value;
  const servings = parseInt($("#detail-servings-input").value, 10);
  const note = $("#detail-note").value.trim();
  const ingredients = $("#detail-ingredients-text")
    .value.split("\n")
    .map((v) => v.trim())
    .filter(Boolean);
  const instructions = $("#detail-instructions").value.trim();

  entry.title = title || entry.title || "Ohne Titel";
  entry.diet_type = DIET_LABELS[dietType]
    ? dietType
    : entry.diet_type || "vegetarian";
  entry.servings = Number.isNaN(servings) ? 0 : Math.max(0, servings);
  entry.note = note;
  if (entry.source === "free" || entry.diet_type === "free") {
    entry.description = note;
  }
  entry.ingredients = ingredients;
  entry.instructions_text = instructions;

  currentPlan[detailEditIndex] = entry;
  closeModal("modal-details");
  renderPlan();
  showToast(
    `${entry.day_name || DAYS_DE[detailEditIndex]} aktualisiert ✏️`,
    "success",
  );
}

// ---------------------------------------------------------------------------
// Swap modal
// ---------------------------------------------------------------------------

function openSwapModal(idx) {
  swapDayIndex = idx;
  const entry = currentPlan[idx];
  $("#swap-day-name").textContent = entry.day_name || DAYS_DE[idx];

  // Reset tabs
  $$(".swap-tab").forEach((t) => t.classList.remove("active"));
  $(".swap-tab[data-tab='all']").classList.add("active");
  $("#swap-free-form").classList.add("hidden");

  loadSwapCandidates("all");
  openModal("modal-swap");
}

async function loadSwapCandidates(type) {
  if (type === "free") {
    $("#swap-list").innerHTML = "";
    $("#swap-free-form").classList.remove("hidden");
    return;
  }
  $("#swap-free-form").classList.add("hidden");
  $("#swap-free-text").value = "";
  const list = $("#swap-list");
  list.innerHTML =
    '<div style="text-align:center;padding:1rem;color:#999">Laden…</div>';

  try {
    const titles = currentPlan.map((e) => e.title);
    const data = await apiCall("/api/swap", {
      method: "POST",
      body: JSON.stringify({
        day_index: swapDayIndex,
        current_titles: titles,
        swap_type: type,
      }),
    });
    renderSwapList(data.candidates);
  } catch (err) {
    list.innerHTML = `<div style="text-align:center;padding:1rem;color:#c62828">${err.message}</div>`;
  }
}

function renderSwapList(candidates) {
  const list = $("#swap-list");
  if (!candidates || candidates.length === 0) {
    list.innerHTML =
      '<div style="text-align:center;padding:1rem;color:#999">Keine Alternativen verfügbar.</div>';
    return;
  }
  list.innerHTML = "";
  candidates.forEach((c) => {
    const imgSrc = getImageSrc(c);
    const item = document.createElement("div");
    item.className = "swap-item";
    const info = DIET_LABELS[c.diet_type] || DIET_LABELS.vegetarian;
    item.innerHTML = `
            ${imgSrc ? `<img class="swap-item-img" src="${imgSrc}" alt="" loading="lazy" onerror="this.style.display='none'">` : `<div class="swap-item-img" style="display:flex;align-items:center;justify-content:center;font-size:1.5rem">${getPlaceholderEmoji(c.diet_type)}</div>`}
            <div class="swap-item-info">
                <div class="swap-item-title">${c.title}</div>
                <div class="swap-item-meta">
                    <span class="card-diet-badge ${info.class}" style="font-size:0.7rem">${info.emoji} ${info.label}</span>
                    ${c.readyInMinutes ? `<span>⏱️ ${c.readyInMinutes} Min</span>` : ""}
                    <span style="color:#aaa">${c.source === "fixed" ? "📌 Eigenes" : "☁️ API"}</span>
                </div>
            </div>`;
    item.addEventListener("click", () => swapDish(c));
    list.appendChild(item);
  });
}

function swapDish(candidate) {
  if (swapDayIndex === null) return;
  const dayInfo = currentPlan[swapDayIndex];

  const entry = { ...candidate };
  entry.day_name = dayInfo.day_name;
  entry.day_index = dayInfo.day_index;
  entry.date = dayInfo.date;

  currentPlan[swapDayIndex] = entry;
  closeModal("modal-swap");
  renderPlan();
  showToast(`${entry.day_name}: ${entry.title} eingesetzt ✅`);
}

function moveDishToDay(fromIdx, toIdx) {
  if (fromIdx === toIdx) return;
  const fromEntry = currentPlan[fromIdx];
  const toEntry = currentPlan[toIdx];
  if (!fromEntry || !toEntry) {
    renderPlan();
    return;
  }
  const slotMeta = currentPlan.map((entry, idx) => ({
    day_name: entry.day_name || getDayMeta(idx).day_name,
    day_index: entry.day_index ?? idx,
    date: entry.date || getDayMeta(idx).date,
  }));
  currentPlan[fromIdx] = toEntry;
  currentPlan[toIdx] = fromEntry;
  normalizePlanDayMeta(slotMeta);
  renderPlan();
  showToast(`${fromEntry.title} nach ${DAYS_DE[toIdx]} verschoben 🔁`, "info");
}

function swapFreeCard() {
  if (swapDayIndex === null) return;
  const desc = $("#swap-free-text").value || "";
  const dayInfo = currentPlan[swapDayIndex];
  const freeEntry = {
    id: `free_${Math.random().toString(36).slice(2)}`,
    title: "Freie Karte",
    image: "",
    readyInMinutes: 0,
    diet_type: "free",
    source: "free",
    servings: 0,
    ingredients: [],
    instructions_text: "",
    description: desc,
    day_name: dayInfo.day_name,
    day_index: dayInfo.day_index,
    date: dayInfo.date,
  };
  currentPlan[swapDayIndex] = freeEntry;
  closeModal("modal-swap");
  $("#swap-free-text").value = "";
  renderPlan();
  showToast(`${dayInfo.day_name}: Freie Karte gesetzt 🎫`);
}

// ---------------------------------------------------------------------------
// Free card edit
// ---------------------------------------------------------------------------

function openFreeEditModal(idx) {
  editingFreeIndex = idx;
  const entry = currentPlan[idx];
  $("#free-edit-text").value = entry.description || "";
  openModal("modal-free-edit");
}

function saveFreeEdit() {
  if (editingFreeIndex === null) return;
  currentPlan[editingFreeIndex].description = $("#free-edit-text").value || "";
  closeModal("modal-free-edit");
  renderPlan();
  showToast("Freie Karte aktualisiert ✏️");
}

// ---------------------------------------------------------------------------
// Dish builder
// ---------------------------------------------------------------------------

const BUILDER_CATEGORY_LABELS = {
  side_dishes: "Beilage",
  sauces: "Soße",
  vegetables: "Gemüse",
  salads: "Salat",
  meat_fish: "Fleisch & Fisch",
  veggie: "Veggie / Ei",
};

const FISH_ITEMS = ["Lachs (Markt)", "Backfisch", "Garnelen", "Fischstäbchen"];

async function openDishBuilder(idx) {
  builderDayIndex = idx;
  if (ingredientsData.length === 0) {
    showLoading("Zutaten laden…");
    try {
      const data = await apiCall("/api/ingredients");
      ingredientsData = data.categories || [];
    } catch (err) {
      showToast("Fehler beim Laden der Zutaten: " + err.message, "error");
      return;
    } finally {
      hideLoading();
    }
  }
  renderBuilderCategories();
  const entry = currentPlan[idx];
  if (entry && entry.source === "custom") {
    // Pre-fill name and re-select chips
    $("#builder-dish-name").value = entry.title || "";
    const selectedNames = entry.ingredients || [];
    $$(".builder-chip").forEach((chip) => {
      if (selectedNames.includes(chip.dataset.name)) {
        chip.classList.add("selected");
      }
    });
  } else {
    $("#builder-dish-name").value = "";
  }
  openModal("modal-dish-builder");
}

function renderBuilderCategories() {
  const container = $("#builder-categories");
  container.innerHTML = "";
  ingredientsData.forEach((cat) => {
    const label = BUILDER_CATEGORY_LABELS[cat.category] || cat.category;
    const section = document.createElement("div");
    section.className = "builder-category";
    const chips = cat.items
      .map(
        (item) =>
          `<button class="builder-chip" data-name="${item.original_de}" data-category="${cat.category}">${item.original_de}</button>`,
      )
      .join("");
    section.innerHTML = `<div class="builder-category-label">${label}</div><div class="builder-chips">${chips}</div>`;
    container.appendChild(section);
  });
  container.querySelectorAll(".builder-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      chip.classList.toggle("selected");
      updateBuilderName();
    });
  });
}

function updateBuilderName() {
  const selected = [...$$(".builder-chip.selected")].map((c) => c.dataset.name);
  if (selected.length === 0) {
    $("#builder-dish-name").value = "";
    return;
  }
  const proteins = selected.filter((n) => {
    const chip = document.querySelector(
      `.builder-chip[data-name="${CSS.escape(n)}"]`,
    );
    return (
      chip &&
      (chip.dataset.category === "meat_fish" ||
        chip.dataset.category === "veggie")
    );
  });
  const rest = selected.filter((n) => !proteins.includes(n));
  const parts = [...proteins, ...rest];
  let name = parts[0] || "";
  if (parts.length === 2) name += ` mit ${parts[1]}`;
  else if (parts.length >= 3) name += ` mit ${parts[1]} und ${parts[2]}`;
  if (parts.length > 3) name += ` (+${parts.length - 3})`;
  const field = $("#builder-dish-name");
  field.value = name;
}

function detectDietType() {
  const meatFishSelected = [
    ...$$(".builder-chip.selected[data-category='meat_fish']"),
  ].map((c) => c.dataset.name);
  const veggieSelected = [
    ...$$(".builder-chip.selected[data-category='veggie']"),
  ];
  if (meatFishSelected.length > 0) {
    const hasFish = meatFishSelected.some((n) => FISH_ITEMS.includes(n));
    const hasMeat = meatFishSelected.some((n) => !FISH_ITEMS.includes(n));
    if (hasFish && !hasMeat) return "fish";
    return "meat";
  }
  if (veggieSelected.length > 0) return "vegetarian";
  const anySelected = $$(".builder-chip.selected").length;
  return anySelected > 0 ? "vegetarian" : "vegetarian";
}

function confirmDishBuilder() {
  if (builderDayIndex === null) return;
  const title = $("#builder-dish-name").value.trim();
  if (!title) {
    showToast(
      "Bitte gib einen Gerichtsnamen ein oder wähle Zutaten aus.",
      "warning",
    );
    return;
  }
  const selected = [...$$(".builder-chip.selected")].map((c) => c.dataset.name);
  const dietType = detectDietType();
  const dayInfo = currentPlan[builderDayIndex];
  const entry = {
    id: `custom_${Math.random().toString(36).slice(2)}`,
    title,
    image: "",
    readyInMinutes: 0,
    diet_type: dietType,
    source: "custom",
    servings: 4,
    ingredients: selected,
    instructions_text: "",
    day_name: dayInfo.day_name,
    day_index: dayInfo.day_index,
    date: dayInfo.date,
  };
  currentPlan[builderDayIndex] = entry;
  closeModal("modal-dish-builder");
  renderPlan();
  showToast(`${dayInfo.day_name}: „${title}" erstellt 🍳`);
}

async function saveBuilderAsFixed() {
  const title = $("#builder-dish-name").value.trim();
  if (!title) {
    showToast("Bitte zuerst einen Gerichtsnamen eingeben.", "warning");
    return;
  }
  const selected = [...$$(".builder-chip.selected")].map((c) => c.dataset.name);
  const dietType = detectDietType();
  const dish = {
    title,
    diet_type: dietType,
    readyInMinutes: 30,
    ingredients: selected,
  };
  try {
    await apiCall("/api/fixed-dishes/save", {
      method: "POST",
      body: JSON.stringify(dish),
    });
    showToast(`„${title}" als fixes Gericht gespeichert! ⭐`);
  } catch (err) {
    showToast(err.message, "error");
  }
}

// ---------------------------------------------------------------------------
// Save / Load plans
// ---------------------------------------------------------------------------

async function savePlan() {
  if (!currentPlan || currentPlan.length === 0) {
    showToast("Kein Plan zum Speichern vorhanden.", "error");
    return;
  }
  showLoading("Plan wird gespeichert…");
  try {
    await apiCall("/api/plans/save", {
      method: "POST",
      body: JSON.stringify({
        plan: currentPlan,
        dates: currentDates,
        name: `Plan ${currentDates.start || ""}`,
      }),
    });
    showToast("Plan gespeichert! 💾");
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    hideLoading();
  }
}

async function loadPlansList() {
  const list = $("#plans-list");
  list.innerHTML =
    '<div style="text-align:center;padding:1rem;color:#999">Laden…</div>';
  openModal("modal-plans");
  try {
    const data = await apiCall("/api/plans/list");
    if (data.plans.length === 0) {
      list.innerHTML =
        '<div style="text-align:center;padding:1rem;color:#999">Keine gespeicherten Pläne vorhanden.</div>';
      return;
    }
    list.innerHTML = "";
    data.plans.forEach((p) => {
      const item = document.createElement("div");
      item.className = "plan-item";
      const created = p.created
        ? new Date(p.created).toLocaleDateString("de-DE", {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          })
        : "";
      item.innerHTML = `
                <div class="plan-item-info">
                    <div class="plan-item-name">${p.name}</div>
                    <div class="plan-item-date">${created}</div>
                </div>
                <div class="plan-item-actions">
                    <button class="btn btn-sm btn-primary btn-load-plan" data-file="${p.filename}">Laden</button>
                    <button class="btn btn-sm btn-danger btn-delete-plan" data-file="${p.filename}">🗑️</button>
                </div>`;
      list.appendChild(item);
    });

    $$(".btn-load-plan").forEach((btn) =>
      btn.addEventListener("click", async (e) => {
        const filename = e.currentTarget.dataset.file;
        await loadPlan(filename);
      }),
    );
    $$(".btn-delete-plan").forEach((btn) =>
      btn.addEventListener("click", async (e) => {
        const filename = e.currentTarget.dataset.file;
        if (confirm("Plan wirklich löschen?")) {
          await deletePlan(filename);
          loadPlansList();
        }
      }),
    );
  } catch (err) {
    list.innerHTML = `<div style="text-align:center;padding:1rem;color:#c62828">${err.message}</div>`;
  }
}

async function loadPlan(filename) {
  showLoading("Plan wird geladen…");
  closeModal("modal-plans");
  try {
    const data = await apiCall(`/api/plans/load/${filename}`);
    currentPlan = data.plan;
    currentDates = data.dates || {};
    if (!currentDates.days || currentDates.days.length !== 7) {
      const weekOffset = selectedWeekOffset || 0;
      const dateData = await apiCall(
        `/api/week-dates?week_offset=${weekOffset}`,
      );
      currentDates = dateData.dates;
    }
    normalizePlanDayMeta();
    renderDateRange();
    renderPlan();
    showToast("Plan geladen! 📂");
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    hideLoading();
  }
}

async function deletePlan(filename) {
  try {
    await apiCall(`/api/plans/delete/${filename}`, { method: "DELETE" });
    showToast("Plan gelöscht 🗑️");
  } catch (err) {
    showToast(err.message, "error");
  }
}

// ---------------------------------------------------------------------------
// Settings / Exclude list
// ---------------------------------------------------------------------------

async function openSettings() {
  showLoading("Einstellungen laden…");
  try {
    const [excludeData, fixedData, ingredData] = await Promise.all([
      apiCall("/api/exclude-list"),
      apiCall("/api/fixed-dishes"),
      apiCall("/api/ingredients"),
    ]);
    excludeRules = excludeData.exclude_rules || {};
    renderExcludeChips(
      "chips-ingredients",
      excludeRules.excludeIngredients || [],
      "excludeIngredients",
    );
    renderExcludeChips(
      "chips-cuisines",
      excludeRules.excludeCuisine || [],
      "excludeCuisine",
    );
    renderExcludeChips(
      "chips-tags",
      excludeRules.excludeTags || [],
      "excludeTags",
    );
    renderExcludeChips(
      "chips-dishtypes",
      excludeRules.excludeDishTypes || [],
      "excludeDishTypes",
    );
    renderFixedDishChips(fixedData.dishes || []);
    populateCategoryDropdown(ingredData.categories || []);
    openModal("modal-settings");
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    hideLoading();
  }
}

function renderExcludeChips(containerId, items, ruleKey) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";
  items.forEach((item, idx) => {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.innerHTML = `${item} <button class="chip-remove" data-key="${ruleKey}" data-idx="${idx}">&times;</button>`;
    container.appendChild(chip);
  });
  container.querySelectorAll(".chip-remove").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const key = e.currentTarget.dataset.key;
      const i = parseInt(e.currentTarget.dataset.idx);
      excludeRules[key].splice(i, 1);
      renderExcludeChips(containerId, excludeRules[key], key);
    });
  });
}

function addExcludeItem(inputId, ruleKey, containerId) {
  const input = document.getElementById(inputId);
  const val = input.value.trim();
  if (!val) return;
  if (!excludeRules[ruleKey]) excludeRules[ruleKey] = [];
  if (!excludeRules[ruleKey].includes(val)) {
    excludeRules[ruleKey].push(val);
  }
  input.value = "";
  renderExcludeChips(containerId, excludeRules[ruleKey], ruleKey);
}

async function saveSettings() {
  showLoading("Einstellungen speichern…");
  try {
    await apiCall("/api/exclude-list", {
      method: "POST",
      body: JSON.stringify({ exclude_rules: excludeRules }),
    });
    closeModal("modal-settings");
    showToast("Einstellungen gespeichert! ⚙️");
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    hideLoading();
  }
}

function renderFixedDishChips(dishes) {
  const container = $("#chips-fixed-dishes");
  container.innerHTML = "";
  dishes.forEach((dish) => {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.innerHTML = `${dish.title} <button class="chip-remove" data-title="${dish.title}">&times;</button>`;
    container.appendChild(chip);
  });
  container.querySelectorAll(".chip-remove").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      const title = e.currentTarget.dataset.title;
      try {
        await apiCall("/api/fixed-dishes/delete", {
          method: "POST",
          body: JSON.stringify({ title }),
        });
        const updated = await apiCall("/api/fixed-dishes");
        renderFixedDishChips(updated.dishes || []);
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  });
}

async function addFixedDish() {
  const title = $("#input-new-fixed-dish").value.trim();
  if (!title) return;
  const diet_type = $("#select-fixed-dish-diet").value;
  const time = parseInt($("#input-fixed-dish-time").value) || 30;
  try {
    await apiCall("/api/fixed-dishes/save", {
      method: "POST",
      body: JSON.stringify({
        title,
        diet_type,
        readyInMinutes: time,
        ingredients: [],
      }),
    });
    $("#input-new-fixed-dish").value = "";
    $("#input-fixed-dish-time").value = "";
    const updated = await apiCall("/api/fixed-dishes");
    renderFixedDishChips(updated.dishes || []);
    showToast(`„${title}" als fixes Gericht gespeichert! ⭐`);
  } catch (err) {
    showToast(err.message, "error");
  }
}

function populateCategoryDropdown(categories) {
  const sel = $("#select-ingredient-category");
  sel.innerHTML = "";
  categories.forEach((cat) => {
    const opt = document.createElement("option");
    opt.value = cat;
    opt.textContent = cat;
    sel.appendChild(opt);
  });
}

async function addNewIngredient() {
  const name = $("#input-new-ingredient-name").value.trim();
  const category = $("#select-ingredient-category").value;
  if (!name || !category) {
    showToast("Bitte Name und Kategorie angeben.", "warning");
    return;
  }
  try {
    await apiCall("/api/ingredients/add", {
      method: "POST",
      body: JSON.stringify({ name, category }),
    });
    $("#input-new-ingredient-name").value = "";
    showToast(`„${name}" zur Kategorie „${category}" hinzugefügt! 🧺`);
  } catch (err) {
    showToast(err.message, "error");
  }
}

// ---------------------------------------------------------------------------
// API refresh
// ---------------------------------------------------------------------------

async function refreshApiCache() {
  if (!confirm("API-Rezepte aktualisieren? Das kann einen Moment dauern."))
    return;
  showLoading("API-Rezepte werden aktualisiert…");
  try {
    const resp = await fetch("/api/refresh-cache", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    const data = await resp.json();
    if (data.success) {
      showToast(`${data.cached_count} Rezepte gecacht! ☁️`, "success");
    } else {
      // Use structured error feedback
      showApiError(data);
    }
  } catch (err) {
    showToast("📡 Netzwerkfehler: " + err.message, "network");
  } finally {
    hideLoading();
  }
}

// ---------------------------------------------------------------------------
// Event listeners
// ---------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
  // Toolbar buttons
  $("#btn-generate").addEventListener("click", openGenerateModal);
  $("#btn-confirm-generate").addEventListener("click", generatePlan);
  $("#btn-save-plan").addEventListener("click", savePlan);
  $("#btn-load-plans").addEventListener("click", loadPlansList);
  $("#btn-settings").addEventListener("click", openSettings);
  $("#btn-refresh-api").addEventListener("click", refreshApiCache);

  // Empty state button
  const emptyBtn = $("#btn-generate-empty");
  if (emptyBtn) emptyBtn.addEventListener("click", openGenerateModal);

  // Swap
  $$(".swap-tab").forEach((tab) =>
    tab.addEventListener("click", (e) => {
      $$(".swap-tab").forEach((t) => t.classList.remove("active"));
      e.currentTarget.classList.add("active");
      loadSwapCandidates(e.currentTarget.dataset.tab);
    }),
  );
  $("#btn-swap-free-confirm").addEventListener("click", swapFreeCard);

  // Details
  $("#btn-detail-save").addEventListener("click", saveDetailsEdit);

  // Free edit
  $("#btn-free-edit-save").addEventListener("click", saveFreeEdit);

  // Dish builder
  $("#btn-builder-confirm").addEventListener("click", confirmDishBuilder);
  $("#btn-builder-save-fixed").addEventListener("click", saveBuilderAsFixed);

  // Settings
  $("#btn-add-fixed-dish").addEventListener("click", addFixedDish);
  $("#btn-add-new-ingredient").addEventListener("click", addNewIngredient);
  $("#btn-add-ingredient").addEventListener("click", () =>
    addExcludeItem(
      "input-add-ingredient",
      "excludeIngredients",
      "chips-ingredients",
    ),
  );
  $("#btn-add-cuisine").addEventListener("click", () =>
    addExcludeItem("input-add-cuisine", "excludeCuisine", "chips-cuisines"),
  );
  $("#btn-add-tag").addEventListener("click", () =>
    addExcludeItem("input-add-tag", "excludeTags", "chips-tags"),
  );
  $("#btn-add-dishtype").addEventListener("click", () =>
    addExcludeItem("input-add-dishtype", "excludeDishTypes", "chips-dishtypes"),
  );
  $("#btn-save-settings").addEventListener("click", saveSettings);

  // Enter key for chip inputs
  [
    "input-add-ingredient",
    "input-add-cuisine",
    "input-add-tag",
    "input-add-dishtype",
  ].forEach((id) => {
    document.getElementById(id).addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        e.currentTarget.nextElementSibling.click();
      }
    });
  });

  // Modal close buttons
  $$("[data-close]").forEach((btn) => {
    btn.addEventListener("click", () => closeModal(btn.dataset.close));
  });

  // Close modals on backdrop click
  $$(".modal-backdrop").forEach((backdrop) => {
    backdrop.addEventListener("click", (e) => {
      if (e.target === backdrop) backdrop.classList.add("hidden");
    });
  });

  // Load week dates + auto-load last saved plan
  fetchWeekDates();
  autoLoadLastPlan();
});

async function fetchWeekDates() {
  try {
    const data = await apiCall("/api/week-dates");
    currentDates = data.dates;
    renderDateRange();
  } catch (e) {
    // silent fail
  }
}

async function autoLoadLastPlan() {
  try {
    const data = await apiCall("/api/plans/list");
    if (!data.plans || data.plans.length === 0) return;
    const latest = data.plans[0];
    const planData = await apiCall(`/api/plans/load/${latest.filename}`);
    currentPlan = planData.plan;
    currentDates = planData.dates || {};
    if (!currentDates.days || currentDates.days.length !== 7) {
      const dateData = await apiCall(
        `/api/week-dates?week_offset=${selectedWeekOffset || 0}`,
      );
      currentDates = dateData.dates;
    }
    normalizePlanDayMeta();
    renderDateRange();
    renderPlan();
  } catch (e) {
    // silent fail
  }
}
