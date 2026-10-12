const voices = window.VOICE_DATA ?? [];
const families = ["Dragon HD", "Dragon HD Omni", "Multilingual Neural", "Standard Neural"];
const caseLabels = {
  "01": "Case 01 · Programme intro",
  "02": "Case 02 · Pronunciation stress",
  "03": "Case 03 · Office code-switching",
  "04": "Case 04 · Long-form mixed narration",
};
const familyNotes = {
  "Dragon HD": {
    points: [
      "Generally the most natural-sounding family.",
      "Relatively authentic Cantonese accents.",
      "Most voices handle Cantonese–English code-switching well.",
      "English phrases retain suitable intonation without disrupting the Cantonese flow.",
    ],
    recommendation: "Most recommended · Start evaluation with this family.",
  },
  "Dragon HD Omni": {
    points: [
      "Smooth, controlled delivery similar to Dragon HD Latest.",
      "Many voices retain a noticeable non-native accent when speaking Cantonese.",
    ],
    recommendation: "Consider when smooth delivery matters more than local accent authenticity.",
  },
  "Multilingual Neural": {
    points: [
      "The listed voices support the zh-HK locale.",
      "Most have a less pronounced non-native accent than broader multilingual options.",
      "English phrases often retain natural English intonation.",
      "The contrast can make Cantonese–English transitions sound flatter or less integrated.",
    ],
    recommendation: "Useful for multilingual content where clear English pronunciation is important.",
  },
  "Standard Neural": {
    points: [
      "The listed voices support zh-HK and are relatively fluent in Cantonese.",
      "Voices from zh-HK, zh-CN, and yue-CN generally sound more locally natural.",
      "Voices from other locales often retain a non-native accent.",
      "English phrases may preserve their original intonation, making code-switching sound less integrated.",
      "Within this family, DragonLatestNeural voices generally handle Cantonese–English tone transitions better than the other Standard Neural voices.",
    ],
    recommendation: "Second recommendation · Evaluate DragonLatestNeural voices after Dragon HD Latest.",
  },
};

const state = {
  family: "All",
  query: "",
  activeButton: null,
  draggingProgress: false,
  pendingSeekTime: null,
  resumeAfterSeek: false,
  loadedSource: null,
  loadController: null,
  objectUrl: null,
};

const tableBody = document.querySelector("#voice-table-body");
const familyFilters = document.querySelector("#family-filters");
const searchInput = document.querySelector("#voice-search");
const visibleCount = document.querySelector("#visible-count");
const audioPlayer = document.querySelector("#audio-player");
const playerDock = document.querySelector("#player-dock");
const dockPlay = document.querySelector("#dock-play");
const dockTitle = document.querySelector("#dock-title");
const dockCase = document.querySelector("#dock-case");
const dockTime = document.querySelector("#dock-time");
const dockProgress = document.querySelector("#dock-progress");
const dockClose = document.querySelector("#dock-close");

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderFamilyFilters() {
  const counts = Object.fromEntries(
    families.map((family) => [family, voices.filter((voice) => voice.family === family).length])
  );
  familyFilters.innerHTML = ["All", ...families]
    .map((family) => {
      const count = family === "All" ? voices.length : counts[family];
      return `<button class="filter-chip ${state.family === family ? "active" : ""}" type="button" data-family="${family}">${family} · ${count}</button>`;
    })
    .join("");
}

function filteredVoices() {
  const query = state.query.trim().toLocaleLowerCase();
  return voices.filter((voice) => {
    const familyMatches = state.family === "All" || voice.family === state.family;
    const searchText = [
      voice.shortName,
      voice.localName,
      voice.locale,
      voice.gender,
      voice.status,
      voice.family,
    ].join(" ").toLocaleLowerCase();
    return familyMatches
      && (!query || searchText.includes(query));
  });
}

function audioCell(voice, caseId) {
  const source = voice.audio[caseId];
  if (!source) {
    return `<td class="audio-cell"><span class="missing-audio" title="No valid audio result">—</span></td>`;
  }
  return `<td class="audio-cell"><button class="play-button" type="button" aria-label="Play ${escapeHtml(voice.shortName)}, case ${caseId}" data-audio="${escapeHtml(source)}" data-title="${escapeHtml(voice.shortName)}" data-case="${caseId}">▶</button></td>`;
}

function renderTable() {
  const visible = filteredVoices();
  visibleCount.textContent = visible.length;
  tableBody.innerHTML = visible
    .map((voice) => `
      <tr>
        <td class="voice-name">
          <strong>${escapeHtml(voice.shortName)}</strong>
          <span>${escapeHtml(voice.localName || "—")}</span>
        </td>
        <td><span class="family-tag ${voice.familySlug}">${escapeHtml(voice.family)}</span></td>
        <td class="locale-cell">${escapeHtml(voice.locale)}<small>${escapeHtml(voice.gender)} · ${voice.status === "Preview" ? "Preview" : "GA"}</small></td>
        ${audioCell(voice, "01")}
        ${audioCell(voice, "02")}
        ${audioCell(voice, "03")}
        ${audioCell(voice, "04")}
      </tr>
    `)
    .join("");
}

function formatTime(seconds) {
  if (!Number.isFinite(seconds)) return "0:00";
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
}

function setPlayingState(isPlaying) {
  dockPlay.textContent = isPlaying ? "Ⅱ" : "▶";
  if (state.activeButton) {
    state.activeButton.textContent = isPlaying ? "Ⅱ" : "▶";
    state.activeButton.classList.toggle("playing", isPlaying);
  }
}

function hasDuration() {
  return Number.isFinite(audioPlayer.duration) && audioPlayer.duration > 0;
}

function renderProgress(time, duration = audioPlayer.duration) {
  const safeDuration = Number.isFinite(duration) && duration > 0 ? duration : 0;
  const safeTime = Math.min(Math.max(Number.isFinite(time) ? time : 0, 0), safeDuration);
  const percent = safeDuration ? (safeTime / safeDuration) * 100 : 0;
  dockProgress.value = safeTime;
  dockProgress.style.setProperty("--progress", `${percent}%`);
  dockProgress.setAttribute(
    "aria-valuetext",
    `${formatTime(safeTime)} of ${formatTime(safeDuration)}`
  );
  dockTime.textContent = `${formatTime(safeTime)} / ${formatTime(safeDuration)}`;
}

function resetProgress() {
  state.draggingProgress = false;
  state.pendingSeekTime = null;
  state.resumeAfterSeek = false;
  dockProgress.disabled = true;
  dockProgress.max = 0;
  renderProgress(0, 0);
}

function isTimeSeekable(time) {
  for (let index = 0; index < audioPlayer.seekable.length; index += 1) {
    if (
      audioPlayer.seekable.start(index) <= time
      && audioPlayer.seekable.end(index) >= time
    ) {
      return true;
    }
  }
  return false;
}

function commitPendingSeek() {
  if (
    state.pendingSeekTime === null
    || !hasDuration()
  ) return;
  if (!isTimeSeekable(state.pendingSeekTime)) {
    if (!audioPlayer.paused) {
      state.resumeAfterSeek = true;
      audioPlayer.pause();
    }
    return;
  }
  const target = Math.min(Math.max(state.pendingSeekTime, 0), audioPlayer.duration);
  state.pendingSeekTime = target;
  audioPlayer.currentTime = target;
}

function releaseLoadedAudio() {
  audioPlayer.pause();
  audioPlayer.removeAttribute("src");
  audioPlayer.load();
  if (state.objectUrl) {
    URL.revokeObjectURL(state.objectUrl);
    state.objectUrl = null;
  }
  state.loadedSource = null;
}

function waitForAudioReady(signal) {
  return new Promise((resolve, reject) => {
    function cleanup() {
      audioPlayer.removeEventListener("canplaythrough", handleReady);
      audioPlayer.removeEventListener("error", handleError);
      signal.removeEventListener("abort", handleAbort);
    }
    function handleReady() {
      cleanup();
      resolve();
    }
    function handleError() {
      cleanup();
      reject(new Error("The downloaded audio could not be decoded"));
    }
    function handleAbort() {
      cleanup();
      reject(new DOMException("Audio loading was canceled", "AbortError"));
    }
    audioPlayer.addEventListener("canplaythrough", handleReady);
    audioPlayer.addEventListener("error", handleError);
    signal.addEventListener("abort", handleAbort, { once: true });
  });
}

async function loadAudio(button) {
  const nextSource = button.dataset.audio;
  if (state.activeButton === button && state.loadController) return;
  if (state.activeButton === button && state.loadedSource === nextSource) {
    if (audioPlayer.paused) audioPlayer.play();
    else audioPlayer.pause();
    return;
  }

  if (state.activeButton && state.activeButton !== button) {
    state.activeButton.textContent = "▶";
    state.activeButton.classList.remove("playing");
  }
  if (state.loadController) {
    state.loadController.abort();
  }

  state.activeButton = button;
  const controller = new AbortController();
  state.loadController = controller;
  releaseLoadedAudio();
  resetProgress();
  dockPlay.disabled = true;
  dockTime.textContent = "Loading audio…";
  dockTitle.textContent = button.dataset.title;
  dockCase.textContent = caseLabels[button.dataset.case];
  playerDock.classList.add("visible");

  try {
    const response = await fetch(nextSource, { signal: controller.signal });
    if (!response.ok) {
      throw new Error(`Audio download failed with HTTP ${response.status}`);
    }
    const audioBlob = await response.blob();
    if (state.loadController !== controller) return;

    state.objectUrl = URL.createObjectURL(audioBlob);
    state.loadedSource = nextSource;
    audioPlayer.src = state.objectUrl;
    audioPlayer.load();
    await waitForAudioReady(controller.signal);
    if (state.loadController !== controller) return;

    dockPlay.disabled = false;
    await audioPlayer.play();
  } catch (error) {
    if (error.name === "AbortError") return;
    console.error(error);
    releaseLoadedAudio();
    resetProgress();
    dockCase.textContent = "Unable to load audio";
    dockTime.textContent = "Load failed";
    if (state.activeButton === button) {
      button.textContent = "▶";
      button.classList.remove("playing");
    }
  } finally {
    if (state.loadController === controller) {
      state.loadController = null;
    }
  }
}

familyFilters.addEventListener("click", (event) => {
  const button = event.target.closest("[data-family]");
  if (!button) return;
  state.family = button.dataset.family;
  renderFamilyFilters();
  renderTable();
});

searchInput.addEventListener("input", () => {
  state.query = searchInput.value;
  renderTable();
});

tableBody.addEventListener("click", (event) => {
  const button = event.target.closest(".play-button");
  if (button) loadAudio(button);
});

dockPlay.addEventListener("click", () => {
  if (!audioPlayer.src) return;
  if (audioPlayer.paused) audioPlayer.play();
  else audioPlayer.pause();
});

dockProgress.addEventListener("input", () => {
  if (!hasDuration()) return;
  state.pendingSeekTime = Number(dockProgress.value);
  renderProgress(state.pendingSeekTime);
  if (!state.draggingProgress) {
    commitPendingSeek();
  }
});

dockProgress.addEventListener("pointerdown", () => {
  if (dockProgress.disabled) return;
  state.draggingProgress = true;
});

dockProgress.addEventListener("pointerup", () => {
  state.draggingProgress = false;
  commitPendingSeek();
});

dockProgress.addEventListener("pointercancel", () => {
  state.draggingProgress = false;
  state.pendingSeekTime = null;
  renderProgress(audioPlayer.currentTime);
});

dockProgress.addEventListener("change", () => {
  state.draggingProgress = false;
  commitPendingSeek();
});

dockClose.addEventListener("click", () => {
  if (state.loadController) {
    state.loadController.abort();
    state.loadController = null;
  }
  releaseLoadedAudio();
  playerDock.classList.remove("visible");
  resetProgress();
  dockPlay.disabled = false;
  if (state.activeButton) {
    state.activeButton.textContent = "▶";
    state.activeButton.classList.remove("playing");
    state.activeButton = null;
  }
});

audioPlayer.addEventListener("play", () => setPlayingState(true));
audioPlayer.addEventListener("pause", () => setPlayingState(false));
audioPlayer.addEventListener("ended", () => setPlayingState(false));
audioPlayer.addEventListener("loadedmetadata", () => {
  if (!hasDuration()) {
    resetProgress();
    return;
  }
  dockProgress.max = audioPlayer.duration;
  dockProgress.disabled = false;
  renderProgress(audioPlayer.currentTime);
});
audioPlayer.addEventListener("canplay", commitPendingSeek);
audioPlayer.addEventListener("canplaythrough", commitPendingSeek);
audioPlayer.addEventListener("progress", commitPendingSeek);
audioPlayer.addEventListener("seeked", () => {
  if (state.draggingProgress) return;
  if (
    state.pendingSeekTime !== null
    && Math.abs(audioPlayer.currentTime - state.pendingSeekTime) < 0.25
  ) {
    state.pendingSeekTime = null;
    renderProgress(audioPlayer.currentTime);
    if (state.resumeAfterSeek) {
      state.resumeAfterSeek = false;
      audioPlayer.play();
    }
  }
});
audioPlayer.addEventListener("timeupdate", () => {
  if (state.draggingProgress || state.pendingSeekTime !== null) return;
  renderProgress(audioPlayer.currentTime);
});

function renderNotes() {
  const notesGrid = document.querySelector("#notes-grid");
  notesGrid.innerHTML = families.map((family) => {
    const count = voices.filter((voice) => voice.family === family).length;
    const note = familyNotes[family];
    return `
      <article class="note-card">
        <header><h3>${family}</h3><span>${count} voices</span></header>
        <ul class="family-comment">
          ${note.points.map((point) => `<li>${point}</li>`).join("")}
        </ul>
        <p class="family-recommendation">${note.recommendation}</p>
      </article>`;
  }).join("");
}

document.querySelector("#voice-total").textContent = voices.length;
document.querySelector("#audio-total").textContent = voices.reduce(
  (count, voice) => count + Object.values(voice.audio).filter(Boolean).length,
  0
);
renderFamilyFilters();
renderTable();
renderNotes();
