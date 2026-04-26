// Simple BORG Launcher Frontend
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/api/dialog";

// DOM Elements (will be assigned in init)
let nicknameInput: HTMLInputElement;
let ramInput: HTMLInputElement;
let ramValue: HTMLElement;
let versionSelect: HTMLSelectElement;
let gameDirInput: HTMLInputElement;
let btnSettings: HTMLElement;
let btnPlay: HTMLElement;
let btnInstall: HTMLElement;
let btnSync: HTMLElement;
let btnClear: HTMLElement;
let logContent: HTMLElement;
let settingsModal: HTMLElement;
let btnCloseSettings: HTMLElement;
let btnSaveSettings: HTMLElement;
let btnBrowse: HTMLElement;
let statusDot: HTMLElement;
let serverStatus: HTMLElement;

// State
let currentConfig: any = {};
let isPlaying = false;
let isInstalling = false;

async function init() {
  // Get elements
  nicknameInput = document.getElementById("nickname") as HTMLInputElement;
  ramInput = document.getElementById("ram") as HTMLInputElement;
  ramValue = document.getElementById("ram-value") as HTMLElement;
  versionSelect = document.getElementById("version") as HTMLSelectElement;
  gameDirInput = document.getElementById("game-dir") as HTMLInputElement;
  btnSettings = document.getElementById("btn-settings") as HTMLElement;
  btnPlay = document.getElementById("btn-play") as HTMLElement;
  btnInstall = document.getElementById("btn-install") as HTMLElement;
  btnSync = document.getElementById("btn-sync") as HTMLElement;
  btnClear = document.getElementById("btn-clear") as HTMLElement;
  logContent = document.getElementById("log-content") as HTMLElement;
  settingsModal = document.getElementById("settings-modal") as HTMLElement;
  btnCloseSettings = document.getElementById("btn-close-settings") as HTMLElement;
  btnSaveSettings = document.getElementById("btn-save-settings") as HTMLElement;
  btnBrowse = document.getElementById("btn-browse") as HTMLElement;
  statusDot = document.getElementById("status-dot") as HTMLElement;
  serverStatus = document.getElementById("server-status") as HTMLElement;

  // Load config
  await loadConfig();

  // Setup events
  setupEvents();

  // Check server
  checkServerStatus();

  log("BORG Launcher ready!");
}

async function loadConfig() {
  try {
    const result = await invoke("load_config_simple") as string;
    currentConfig = JSON.parse(result);

    // Apply to UI
    nicknameInput.value = currentConfig.nickname || "Player";
    ramInput.value = String((currentConfig.ram_mb || 4096) / 1024);
    ramValue.textContent = String((currentConfig.ram_mb || 4096) / 1024);
    versionSelect.value = currentConfig.last_version || "neoforge-21.1.227";
    gameDirInput.value = currentConfig.game_dir || "";

    log(`Config loaded: ${currentConfig.game_dir}`);
  } catch (e) {
    log("Using default settings");
  }
}

async function saveSettings() {
  try {
    const newConfig = {
      nickname: nicknameInput.value,
      ram_mb: parseInt(ramInput.value) * 1024,
      last_version: versionSelect.value,
      game_dir: gameDirInput.value,
      window_width: currentConfig.window_width || 1200,
      window_height: currentConfig.window_height || 700,
    };

    await invoke("save_config_simple", { configJson: JSON.stringify(newConfig) });
    currentConfig = newConfig;
    log("Settings saved!");
    closeSettings();
  } catch (e: any) {
    log(`Save error: ${e}`);
  }
}

function setupEvents() {
  // RAM slider
  ramInput?.addEventListener("input", () => {
    if (ramValue) ramValue.textContent = ramInput.value;
  });

  // Modal
  btnSettings?.addEventListener("click", openSettings);
  btnCloseSettings?.addEventListener("click", closeSettings);
  btnSaveSettings?.addEventListener("click", saveSettings);

  // Browse
  btnBrowse?.addEventListener("click", async () => {
    const selected = await open({ directory: true });
    if (selected && typeof selected === "string") {
      gameDirInput.value = selected.replace(/\\/g, "/");
    }
  });

  // Game actions
  btnPlay?.addEventListener("click", launchGame);
  btnInstall?.addEventListener("click", installGame);
  btnSync?.addEventListener("click", syncMods);
  btnClear?.addEventListener("click", () => {
    if (logContent) logContent.innerHTML = "";
  });
}

function openSettings() {
  settingsModal?.classList.add("active");
}

function closeSettings() {
  settingsModal?.classList.remove("active");
}

async function checkServerStatus() {
  try {
    const status = await invoke("check_server_status") as boolean;
    if (status) {
      statusDot?.classList.add("online");
      statusDot?.classList.remove("offline");
      if (serverStatus) serverStatus.textContent = "Online";
    } else {
      statusDot?.classList.add("offline");
      statusDot?.classList.remove("online");
      if (serverStatus) serverStatus.textContent = "Offline";
    }
  } catch {
    statusDot?.classList.add("offline");
    if (serverStatus) serverStatus.textContent = "Error";
  }
}

async function launchGame() {
  if (isInstalling) {
    log("Wait for install to finish");
    return;
  }
  if (isPlaying) {
    log("Game already running");
    return;
  }
  if (!nicknameInput?.value.trim()) {
    log("Enter nickname first");
    return;
  }

  log("Launching...");
  isPlaying = true;
  if (btnPlay) btnPlay.textContent = "Running...";

  try {
    const result = await invoke("launch_game_simple", {
      nickname: nicknameInput.value,
      ramMb: parseInt(ramInput.value) * 1024,
      version: versionSelect.value,
      gameDir: gameDirInput.value,
    });
    log(String(result));
  } catch (e: any) {
    log(`Launch error: ${e}`);
  } finally {
    isPlaying = false;
    if (btnPlay) btnPlay.textContent = "Play";
  }
}

async function installGame() {
  if (isInstalling || isPlaying) {
    log("Wait for current operation to finish");
    return;
  }

  log("Installing...");
  isInstalling = true;
  if (btnInstall) btnInstall.textContent = "Installing...";

  try {
    const result = await invoke("install_game_simple", {
      gameDir: gameDirInput.value,
    });
    log(String(result));
  } catch (e: any) {
    log(`Install error: ${e}`);
  } finally {
    isInstalling = false;
    if (btnInstall) btnInstall.textContent = "Install";
  }
}

async function syncMods() {
  log("Syncing mods...");
  try {
    const result = await invoke("sync_mods_simple", {
      gameDir: gameDirInput.value,
    });
    log(String(result));
  } catch (e: any) {
    log(`Sync error: ${e}`);
  }
}

function log(message: string) {
  const line = document.createElement("div");
  line.className = "log-line";
  line.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
  logContent?.appendChild(line);
  logContent?.scrollTo(0, logContent.scrollHeight);
}

// Start
document.addEventListener("DOMContentLoaded", init);
