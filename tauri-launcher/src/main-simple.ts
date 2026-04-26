// Simple BORG Launcher Frontend
import { invoke } from "@tauri-apps/api/core";

// DOM Elements
let nicknameInput: HTMLInputElement;
let ramInput: HTMLInputElement;
let ramValue: HTMLElement;
let versionSelect: HTMLSelectElement;
let gameDirInput: HTMLInputElement;
let btnSettings: HTMLElement;
let btnPlay: HTMLElement;
let btnInstall: HTMLElement;
let btnSync: HTMLElement;
let logContent: HTMLElement;
let settingsModal: HTMLElement;
let btnCloseSettings: HTMLElement;
let btnSaveSettings: HTMLElement;
let btnBrowse: HTMLElement;

// State
let currentConfig: any = {};

async function init() {
  console.log("Initializing...");
  
  // Get DOM elements
  nicknameInput = document.getElementById("nickname") as HTMLInputElement;
  ramInput = document.getElementById("ram") as HTMLInputElement;
  ramValue = document.getElementById("ram-value") as HTMLElement;
  versionSelect = document.getElementById("version") as HTMLSelectElement;
  gameDirInput = document.getElementById("game-dir") as HTMLInputElement;
  btnSettings = document.getElementById("btn-settings") as HTMLElement;
  btnPlay = document.getElementById("btn-play") as HTMLElement;
  btnInstall = document.getElementById("btn-install") as HTMLElement;
  btnSync = document.getElementById("btn-sync") as HTMLElement;
  logContent = document.getElementById("log-content") as HTMLElement;
  settingsModal = document.getElementById("settings-modal") as HTMLElement;
  btnCloseSettings = document.getElementById("btn-close-settings") as HTMLElement;
  btnSaveSettings = document.getElementById("btn-save-settings") as HTMLElement;
  btnBrowse = document.getElementById("btn-browse") as HTMLElement;

  // Load config
  await loadConfig();
  
  // Setup events
  setupEvents();
  
  log("Launcher initialized");
}

async function loadConfig() {
  try {
    const config = await invoke("load_config_from_file") as any;
    console.log("Loaded config:", config);
    currentConfig = config;
    
    // Apply to UI - use exact keys from JSON
    if (nicknameInput) nicknameInput.value = config.nickname || "Player";
    if (ramInput) ramInput.value = String(config.ram_mb || 4096);
    if (ramValue) ramValue.textContent = String(config.ram_mb || 4096);
    if (versionSelect) versionSelect.value = config.last_version || "neoforge-21.1.227";
    if (gameDirInput) gameDirInput.value = config.game_dir || "";
    
  } catch (e) {
    console.error("Failed to load config:", e);
    log("Using default settings");
  }
}

async function saveSettings() {
  try {
    const newConfig = {
      nickname: nicknameInput?.value || "Player",
      ram_mb: parseInt(ramInput?.value || "4096"),
      last_version: versionSelect?.value || "neoforge-21.1.227",
      game_dir: gameDirInput?.value || "",
      window_width: currentConfig.window_width || 1200,
      window_height: currentConfig.window_height || 700,
    };
    
    await invoke("save_config_direct", { configJson: JSON.stringify(newConfig) });
    currentConfig = newConfig;
    log("Settings saved!");
    closeSettings();
  } catch (e: any) {
    log(`Error saving: ${e}`);
  }
}

function setupEvents() {
  // RAM slider
  ramInput?.addEventListener("input", () => {
    if (ramValue) ramValue.textContent = ramInput.value;
  });
  
  // Settings modal
  btnSettings?.addEventListener("click", openSettings);
  btnCloseSettings?.addEventListener("click", closeSettings);
  btnSaveSettings?.addEventListener("click", saveSettings);
  
  // Game actions
  btnPlay?.addEventListener("click", launchGame);
  btnInstall?.addEventListener("click", installGame);
  btnSync?.addEventListener("click", syncMods);
}

function openSettings() {
  if (settingsModal) settingsModal.classList.add("active");
}

function closeSettings() {
  if (settingsModal) settingsModal.classList.remove("active");
}

async function launchGame() {
  log("Launching Minecraft...");
  try {
    const result = await invoke("launch_game_simple", {
      nickname: currentConfig.nickname || "Player",
      ramMb: currentConfig.ram_mb || 4096,
      version: currentConfig.last_version || "neoforge-21.1.227",
      gameDir: currentConfig.game_dir || ""
    });
    log(result as string);
  } catch (e: any) {
    log(`Launch failed: ${e}`);
  }
}

async function installGame() {
  log("Installing Minecraft...");
  try {
    const result = await invoke("install_game_simple", {
      gameDir: currentConfig.game_dir || ""
    });
    log(result as string);
  } catch (e: any) {
    log(`Install failed: ${e}`);
  }
}

async function syncMods() {
  log("Syncing mods...");
  try {
    const result = await invoke("sync_mods_simple", {
      gameDir: currentConfig.game_dir || ""
    });
    log(result as string);
  } catch (e: any) {
    log(`Sync failed: ${e}`);
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
