// BORG Launcher with auto-save
import { invoke } from "@tauri-apps/api/tauri";
import { listen } from "@tauri-apps/api/event";
import { open } from "@tauri-apps/api/dialog";
import { appWindow } from "@tauri-apps/api/window";
import { Command } from "@tauri-apps/api/shell";

// Elements
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
let btnCopy: HTMLElement;
let logContent: HTMLElement;
let settingsModal: HTMLElement;
let btnCloseSettings: HTMLElement;
let btnSaveSettings: HTMLElement;
let btnCancelSettings: HTMLElement;
let btnBrowse: HTMLElement;
let btnOpenMods: HTMLElement;
let btnOpenScreenshots: HTMLElement;
let btnFixBuild: HTMLElement;
let fixBuildProgress: HTMLElement;
let fixBuildProgressBar: HTMLElement;
let syncProgress: HTMLElement;
let syncProgressBar: HTMLElement;
let installProgress: HTMLElement;
let installProgressBar: HTMLElement;
let statusDot: HTMLElement;
let serverStatus: HTMLElement;
let lastProgressLine: HTMLElement | null = null;
let installProgressLine: HTMLElement | null = null;
let autosyncToggle: HTMLInputElement;
let newsContent: HTMLElement;

// Game monitoring
let gameMonitoringInterval: number | null = null;

// Config keys
const CONFIG_KEYS = {
  nickname: "nickname",
  ram_mb: "ram_mb",
  last_version: "last_version",
  game_dir: "game_dir",
  window_width: "window_width",
  window_height: "window_height",
  autosync_mods: "autosync_mods",
  news_url: "news_url"
};

// GitHub news URL
const DEFAULT_NEWS_URL = "https://raw.githubusercontent.com/BORGERone/BORG-Launcher/main/news.md";

// Store original values for cancel
let originalConfig: any = {};

// Build config from current field values
function buildConfig() {
  // RAM: convert GB to MB, but protect against double conversion
  const rawValue = ramInput?.value || "4";
  let ramGB = parseInt(rawValue);
  console.log(`RAM raw value: "${rawValue}" -> parsed: ${ramGB}`);
  
  if (ramGB > 1000) {
    // Value is already in MB (from old bug), convert to GB first
    ramGB = Math.floor(ramGB / 1024);
    console.log(`RAM converted from MB to GB: ${ramGB}`);
  }
  const ramMB = ramGB * 1024;
  console.log(`RAM final: ${ramMB} MB (${ramGB} GB)`);
  
  return {
    [CONFIG_KEYS.nickname]: nicknameInput?.value?.trim() || "Player",
    [CONFIG_KEYS.ram_mb]: ramMB,
    [CONFIG_KEYS.last_version]: versionSelect?.value || "neoforge-21.1.227",
    [CONFIG_KEYS.game_dir]: gameDirInput?.value || "E:/Games/test",
    [CONFIG_KEYS.window_width]: 1200,
    [CONFIG_KEYS.window_height]: 700,
    [CONFIG_KEYS.autosync_mods]: autosyncToggle?.checked !== undefined ? autosyncToggle.checked : true, // Default to true
  };
}

// Save config to file
async function saveConfig() {
  const config = buildConfig();
  try {
    await invoke("save_config_simple", { configJson: JSON.stringify(config) });
    log("Auto-saved");
  } catch (e: any) {
    log(`Save error: ${e}`);
  }
}

// Init
async function init() {
  getElements();
  setupEvents();
  await loadConfig();
  await loadNews();
  assignRandomAnimations();
  setupImageModal();
  checkServerStatus();
  log("Launcher ready");
}

// Assign random animations to pylons 3 and 4
function assignRandomAnimations() {
  const bgR3 = document.querySelector('.bg-r-3') as HTMLElement;
  const bgR4 = document.querySelector('.bg-r-4') as HTMLElement;

  if (bgR3) {
    const horizontalAnimations = ['floatHorizontal1', 'floatHorizontal2', 'floatHorizontal3', 'floatHorizontal4'];
    const verticalAnimations = ['floatVertical3', 'floatVertical4'];
    const allAnimations = [...horizontalAnimations, ...verticalAnimations];

    const randomAnimation = allAnimations[Math.floor(Math.random() * allAnimations.length)];
    const randomDuration = (31 + Math.random() * 16).toFixed(1); // 31-47 seconds (slowed by 50% + 30%)

    bgR3.style.animation = `${randomAnimation} ${randomDuration}s ease-in-out infinite`;
  }

  if (bgR4) {
    const horizontalAnimations = ['floatHorizontal1', 'floatHorizontal2', 'floatHorizontal3', 'floatHorizontal4'];
    const verticalAnimations = ['floatVertical3', 'floatVertical4'];
    const allAnimations = [...horizontalAnimations, ...verticalAnimations];

    const randomAnimation = allAnimations[Math.floor(Math.random() * allAnimations.length)];
    const randomDuration = (23 + Math.random() * 11).toFixed(1); // 23-34 seconds (slowed by 30%)

    bgR4.style.animation = `${randomAnimation} ${randomDuration}s ease-in-out infinite`;
  }
}

// Simple markdown parser
function parseMarkdown(markdown: string): string {
  let html = markdown;

  // Images and videos (must be before links to avoid conflict)
  html = html.replace(/!\[([^\]]*)\]\(([^)]+\.mp4)\)/g, '<video src="$2" controls style="max-width: 100%; border-radius: 8px; margin: 12px 0;"></video>');
  html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" style="max-width: 100%; border-radius: 8px; margin: 12px 0; cursor: pointer;" class="news-image">');

  // Headers
  html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
  html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

  // Bold
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

  // Italic
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');

  // Code blocks
  html = html.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');

  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Links
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');

  // Unordered lists
  html = html.replace(/^\* (.*$)/gim, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

  // Ordered lists
  html = html.replace(/^\d+\. (.*$)/gim, '<li>$1</li>');

  // Horizontal rule
  html = html.replace(/^---$/gim, '<hr style="border: none; border-top: 1px solid rgba(128, 232, 191, 0.3); margin: 20px 0;">');

  // Paragraphs
  html = html.replace(/\n\n/g, '</p><p>');
  html = '<p>' + html + '</p>';

  return html;
}

// Load news from GitHub or local file
async function loadNews() {
  try {
    const newsUrl = DEFAULT_NEWS_URL;
    log(`Loading news from: ${newsUrl}`);
    
    // Try to fetch from GitHub URL
    try {
      const response = await fetch(newsUrl);
      log(`GitHub response status: ${response.status}`);
      
      if (response.ok) {
        const newsText = await response.text();
        if (newsText && typeof newsText === "string") {
          const htmlContent = parseMarkdown(newsText);
          if (newsContent) {
            newsContent.innerHTML = htmlContent;
          }
          log("News loaded from GitHub");
          return;
        }
      } else {
        log(`GitHub returned status: ${response.status}`);
      }
    } catch (e) {
      log(`Failed to load news from GitHub: ${e}`);
    }
    
    // Fallback to local file
    log("Falling back to local file");
    const newsText = await invoke("read_news") as string;
    if (newsText && typeof newsText === "string") {
      const htmlContent = parseMarkdown(newsText);
      if (newsContent) {
        newsContent.innerHTML = htmlContent;
      }
      log("News loaded from local file");
    }
  } catch (e) {
    // If news file doesn't exist, show default message
    log(`News load error: ${e}`);
    if (newsContent) {
      newsContent.innerHTML = '<p>Новости не найдены. Создайте файл news.md в папке игры или настройте URL GitHub.</p>';
    }
  }
}

// Image modal functions
function openImageModal(src: string) {
  const modal = document.getElementById('image-modal') as HTMLElement;
  const modalImg = document.getElementById('image-modal-content') as HTMLImageElement;
  if (modal && modalImg) {
    modalImg.src = src;
    modal.classList.add('active');
  }
}

function closeImageModal() {
  const modal = document.getElementById('image-modal') as HTMLElement;
  if (modal) {
    modal.classList.remove('active');
  }
}

// Setup image modal event listeners
function setupImageModal() {
  const modal = document.getElementById('image-modal') as HTMLElement;
  const closeBtn = document.getElementById('image-modal-close') as HTMLElement;

  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        closeImageModal();
      }
    });
  }

  if (closeBtn) {
    closeBtn.addEventListener('click', closeImageModal);
  }

  // Close on Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeImageModal();
    }
  });

  // Add click handlers to news images
  document.addEventListener('click', (e) => {
    const target = e.target as HTMLElement;
    if (target.classList.contains('news-image')) {
      const img = target as HTMLImageElement;
      openImageModal(img.src);
    }
  });
}

function getElements() {
  nicknameInput = document.getElementById("nickname") as HTMLInputElement;
  ramInput = document.getElementById("ram") as HTMLInputElement;
  ramValue = document.getElementById("ram-value") as HTMLElement;
  versionSelect = document.getElementById("version-select") as HTMLSelectElement;
  gameDirInput = document.getElementById("game-dir") as HTMLInputElement;
  btnSettings = document.getElementById("btn-settings") as HTMLElement;
  btnPlay = document.getElementById("btn-play") as HTMLElement;
  btnInstall = document.getElementById("btn-install") as HTMLElement;
  btnSync = document.getElementById("btn-sync") as HTMLElement;
  btnClear = document.getElementById("btn-clear") as HTMLElement;
  btnCopy = document.getElementById("btn-copy") as HTMLElement;
  logContent = document.getElementById("log-content") as HTMLElement;
  settingsModal = document.getElementById("settings-modal") as HTMLElement;
  btnCloseSettings = document.getElementById("btn-close-settings") as HTMLElement;
  btnSaveSettings = document.getElementById("btn-save-settings") as HTMLElement;
  btnCancelSettings = document.getElementById("btn-cancel-settings") as HTMLElement;
  btnBrowse = document.getElementById("btn-browse") as HTMLElement;
  btnOpenMods = document.getElementById("btn-open-mods") as HTMLElement;
  btnOpenScreenshots = document.getElementById("btn-open-screenshots") as HTMLElement;
  btnFixBuild = document.getElementById("btn-fix-build") as HTMLElement;
  fixBuildProgress = document.getElementById("fix-build-progress") as HTMLElement;
  fixBuildProgressBar = document.getElementById("fix-build-progress-bar") as HTMLElement;
  syncProgress = document.getElementById("sync-progress") as HTMLElement;
  syncProgressBar = document.getElementById("sync-progress-bar") as HTMLElement;
  installProgress = document.getElementById("install-progress") as HTMLElement;
  installProgressBar = document.getElementById("install-progress-bar") as HTMLElement;
  statusDot = document.getElementById("status-dot") as HTMLElement;
  serverStatus = document.getElementById("server-status") as HTMLElement;
  autosyncToggle = document.getElementById("autosync-toggle") as HTMLInputElement;
  newsContent = document.getElementById("news-content") as HTMLElement;
}

function setupEvents() {
  // Auto-save on any change
  nicknameInput?.addEventListener("change", saveConfig);
  ramInput?.addEventListener("change", saveConfig);
  ramInput?.addEventListener("input", () => {
    if (ramValue) ramValue.textContent = ramInput.value;
  });
  versionSelect?.addEventListener("change", saveConfig);
  gameDirInput?.addEventListener("change", saveConfig);
  autosyncToggle?.addEventListener("change", saveConfig);

  // Modal
  btnSettings?.addEventListener("click", () => {
    // Store original values before opening
    originalConfig = {
      nickname: nicknameInput?.value,
      ram: ramInput?.value,
      version: versionSelect?.value,
      gameDir: gameDirInput?.value,
      autosync: autosyncToggle?.checked
    };
    settingsModal?.classList.add("active");
  });
  btnCloseSettings?.addEventListener("click", () => settingsModal?.classList.remove("active"));
  btnSaveSettings?.addEventListener("click", () => {
    saveConfig();
    settingsModal?.classList.remove("active");
  });
  btnCancelSettings?.addEventListener("click", () => {
    // Restore original values
    if (nicknameInput) nicknameInput.value = originalConfig.nickname || "Player";
    if (ramInput) ramInput.value = originalConfig.ram || "4";
    if (ramValue) ramValue.textContent = originalConfig.ram || "4";
    if (versionSelect) versionSelect.value = originalConfig.version || "neoforge-21.1.227";
    if (gameDirInput) gameDirInput.value = originalConfig.gameDir || "E:/Games/test";
    if (autosyncToggle) autosyncToggle.checked = originalConfig.autosync || false;
    settingsModal?.classList.remove("active");
  });

  // Browse button
  btnBrowse?.addEventListener("click", async () => {
    const selected = await open({ directory: true });
    if (selected && typeof selected === "string") {
      gameDirInput.value = selected.replace(/\\/g, "/");
      saveConfig();
    }
  });

  // Open mods folder
  btnOpenMods?.addEventListener("click", async () => {
    const gameDir = gameDirInput?.value || "E:/Games/test";
    const modsPath = `${gameDir}\\mods`.replace(/\//g, '\\');
    try {
      const command = new Command('cmd', ['/c', 'explorer', modsPath]);
      await command.execute();
      log(`Opened mods folder: ${modsPath}`);
    } catch (e) {
      log(`Error opening mods folder: ${e}`);
    }
  });

  // Open screenshots folder
  btnOpenScreenshots?.addEventListener("click", async () => {
    const gameDir = gameDirInput?.value || "E:/Games/test";
    const screenshotsPath = `${gameDir}\\screenshots`.replace(/\//g, '\\');
    try {
      const command = new Command('cmd', ['/c', 'explorer', screenshotsPath]);
      await command.execute();
      log(`Opened screenshots folder: ${screenshotsPath}`);
    } catch (e) {
      log(`Error opening screenshots folder: ${e}`);
    }
  });

  // Game actions
  btnPlay?.addEventListener("click", playGame);
  btnInstall?.addEventListener("click", installGame);
  btnSync?.addEventListener("click", syncMods);
  btnFixBuild?.addEventListener("click", fixBuild);
  btnClear?.addEventListener("click", () => {
    if (logContent) logContent.innerHTML = "";
  });
  btnCopy?.addEventListener("click", () => {
    if (logContent) {
      const logText = logContent.innerText;
      navigator.clipboard.writeText(logText).then(() => {
        log("Log copied to clipboard");
      }).catch((e) => {
        log(`Failed to copy log: ${e}`);
      });
    }
  });
}

// Load config from file
async function loadConfig() {
  try {
    const result = await invoke("load_config_simple") as string;
    const config = JSON.parse(result);

    // Convert MB to GB for display (ram is stored in MB in config)
    const ramGB = Math.floor((config.ram_mb || 4096) / 1024);
    
    // Apply to fields
    if (nicknameInput) nicknameInput.value = config.nickname || "Player";
    if (ramInput) ramInput.value = String(ramGB);
    if (ramValue) ramValue.textContent = String(ramGB);
    if (versionSelect) versionSelect.value = config.last_version || "neoforge-21.1.227";
    if (gameDirInput) gameDirInput.value = config.game_dir || "E:/Games/test";
    if (autosyncToggle) autosyncToggle.checked = config.autosync_mods !== undefined ? config.autosync_mods : true; // Default to true if not set

    log(`Config loaded: ${ramGB}GB RAM`);
  } catch (e) {
    log("Using defaults");
    // Set default values when config doesn't exist
    if (nicknameInput) nicknameInput.value = "Player";
    if (ramInput) ramInput.value = "4";
    if (ramValue) ramValue.textContent = "4";
    if (versionSelect) versionSelect.value = "neoforge-21.1.227";
    if (gameDirInput) gameDirInput.value = "E:/Games/test";
    if (autosyncToggle) autosyncToggle.checked = true; // Default to true
  }
}

// Play game - save first, then launch
async function playGame() {
  if (!nicknameInput?.value?.trim()) {
    log("Enter nickname!");
    return;
  }

  // Save current values
  await saveConfig();

  // Check if autosync is enabled
  if (autosyncToggle?.checked) {
    log("Auto-syncing mods before launch...");
    await syncMods();
  }

  log("Launching...");
  const config = buildConfig();

  try {
    const result = await invoke("launch_game_simple", {
      nickname: config.nickname,
      ramMb: config.ram_mb,
      version: config.last_version,
      gameDir: config.game_dir,
    });
    log(String(result));

    // Hide window to tray after launching game
    await invoke("hide_window");

    // Start monitoring for game closure
    startGameMonitoring();
  } catch (e: any) {
    log(`Launch error: ${e}`);
  }
}

// Start monitoring Minecraft process
function startGameMonitoring() {
  // Clear existing interval if any
  if (gameMonitoringInterval !== null) {
    clearInterval(gameMonitoringInterval);
  }

  // Check every 3 seconds if Minecraft is still running
  gameMonitoringInterval = window.setInterval(async () => {
    try {
      const isRunning = await invoke("is_minecraft_running") as boolean;
      if (!isRunning) {
        // Minecraft closed, restore window
        stopGameMonitoring();
        await invoke("show_window");
        log("Minecraft closed - launcher restored");
      }
    } catch (e) {
      console.error("Error checking Minecraft status:", e);
    }
  }, 3000);
}

// Stop monitoring Minecraft process
function stopGameMonitoring() {
  if (gameMonitoringInterval !== null) {
    clearInterval(gameMonitoringInterval);
    gameMonitoringInterval = null;
  }
}

async function installGame() {
  await saveConfig();
  log("Installing...");
  
  const gameDir = gameDirInput?.value || "E:/Games/test";
  
  // Show progress bar
  if (installProgress) installProgress.style.display = "block";
  if (installProgressBar) installProgressBar.style.width = "0%";
  
  // Immediate progress: 0% -> 2%
  setProgressSafely(2);
  
  // Start smooth fake progress
  startSmoothProgress();
  
  // After 5 seconds: 2% -> 8%
  setTimeout(() => {
    setProgressSafely(8);
  }, 5000);
  
  // After 15 seconds: 8% -> 15% and start file counting
  setTimeout(() => {
    setProgressSafely(15);
    startFileCountingProgress(gameDir);
  }, 15000);
  
  try {
    const result = await invoke("install_game_simple", { gameDir });
    log(String(result));
    
    // Stop all progress on completion
    stopAllProgress();
    
    // Set to 100% on completion
    setProgressSafely(100);
    
    // Hide progress bar after delay
    setTimeout(() => {
      if (installProgress) installProgress.style.display = "none";
      if (installProgressBar) installProgressBar.style.width = "0%";
      
      // Flash green after progress bar is hidden
      if (btnInstall) {
        btnInstall.classList.add("btn-success-flash");
        setTimeout(() => {
          btnInstall.classList.remove("btn-success-flash");
        }, 1000);
      }
    }, 2000);
  } catch (e: any) {
    log(`Install error: ${e}`);
    
    // Stop all progress on error
    stopAllProgress();
    
    // Hide progress bar on error
    if (installProgress) installProgress.style.display = "none";
    if (installProgressBar) installProgressBar.style.width = "0%";
  }
}

let smoothProgressInterval: number | null = null;
let fileCountingInterval: number | null = null;

function startSmoothProgress() {
  smoothProgressInterval = window.setInterval(() => {
    const currentWidth = parseInt(installProgressBar?.style.width || "0");
    if (currentWidth < 95) {
      const newWidth = Math.min(95, currentWidth + 1); // Add 1% every second
      if (installProgressBar) installProgressBar.style.width = `${newWidth}%`;
      updateProgressLog(newWidth);
    }
  }, 1000);
}

function updateProgressLog(percent: number) {
  const barWidth = 50;
  const filled = Math.round((percent / 100) * barWidth);
  const empty = barWidth - filled;
  const progressBar = `[${"I".repeat(filled)}${" ".repeat(empty)}](${percent.toFixed(0)}%)`;
  
  // Change text based on progress
  let statusText = "Installing...";
  if (percent >= 100) {
    statusText = "Complete!";
  }
  
  const message = `${progressBar}   ${statusText}`;
  
  // Update existing progress line or create new one
  if (installProgressLine) {
    installProgressLine.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
  } else {
    installProgressLine = document.createElement("div");
    installProgressLine.className = "log-line";
    installProgressLine.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    logContent?.appendChild(installProgressLine);
  }
  
  logContent?.scrollTo(0, logContent.scrollHeight);
}

function setProgressSafely(percent: number) {
  const currentWidth = parseInt(installProgressBar?.style.width || "0");
  const newWidth = Math.max(currentWidth, percent); // Never decrease
  if (installProgressBar) installProgressBar.style.width = `${newWidth}%`;
}

function stopAllProgress() {
  if (smoothProgressInterval) {
    clearInterval(smoothProgressInterval);
    smoothProgressInterval = null;
  }
  if (fileCountingInterval) {
    clearInterval(fileCountingInterval);
    fileCountingInterval = null;
  }
  
  // Reset progress line reference
  installProgressLine = null;
}

async function startFileCountingProgress(gameDir: string) {
  let lastCount = 0;
  
  fileCountingInterval = window.setInterval(async () => {
    try {
      const count = await invoke("count_directory_items", { path: gameDir }) as number;
      
      // Only update if count changed
      if (count > lastCount) {
        const newItems = count - lastCount;
        const progressIncrease = newItems * 2.5; // 2.5% per item (half of 5%)
        
        const currentWidth = parseInt(installProgressBar?.style.width || "0");
        const newWidth = Math.min(95, currentWidth + progressIncrease);
        
        setProgressSafely(newWidth);
        updateProgressLog(newWidth);
        lastCount = count;
        
        // Stop if reached 95%
        if (newWidth >= 95 && fileCountingInterval) {
          clearInterval(fileCountingInterval);
          fileCountingInterval = null;
        }
      }
    } catch (e) {
      console.error("Error counting files:", e);
    }
  }, 1000); // Check every second
}

async function syncMods() {
  await saveConfig();
  log("Syncing...");
  
  // Show progress bar
  if (syncProgress) syncProgress.style.display = "block";
  if (syncProgressBar) syncProgressBar.style.width = "0%";
  
  try {
    const result = await invoke("sync_mods_simple", {
      gameDir: gameDirInput?.value || "E:/Games/test"
    });
    log(String(result));
    
    if (syncProgressBar) syncProgressBar.style.width = "100%";
    
    // Hide progress bar after delay
    setTimeout(() => {
      if (syncProgress) syncProgress.style.display = "none";
      if (syncProgressBar) syncProgressBar.style.width = "0%";
      
      // Flash green after progress bar is hidden
      if (btnSync) {
        btnSync.classList.add("btn-success-flash");
        setTimeout(() => {
          btnSync.classList.remove("btn-success-flash");
        }, 1000);
      }
    }, 2000);
  } catch (e: any) {
    log(`Sync error: ${e}`);
    // Hide progress bar on error
    if (syncProgress) syncProgress.style.display = "none";
    if (syncProgressBar) syncProgressBar.style.width = "0%";
  }
}

async function fixBuild() {
  await saveConfig();
  log("Fixing build...");
  
  // Show progress bar
  if (fixBuildProgress) fixBuildProgress.style.display = "block";
  if (fixBuildProgressBar) fixBuildProgressBar.style.width = "0%";
  
  try {
    const gameDir = gameDirInput?.value || "E:/Games/test";
    
    // Clear mods folder (30% progress)
    log("Clearing mods folder...");
    const clearResult = await invoke("clear_mods_folder", { gameDir });
    log(String(clearResult));
    if (fixBuildProgressBar) fixBuildProgressBar.style.width = "30%";
    
    // Sync mods (30-100% progress via events)
    log("Syncing mods...");
    const syncResult = await invoke("sync_mods_simple", { gameDir });
    log(String(syncResult));
    
    if (fixBuildProgressBar) fixBuildProgressBar.style.width = "100%";
    log("Build fixed successfully!");
    
    // Hide progress bar after delay
    setTimeout(() => {
      if (fixBuildProgress) fixBuildProgress.style.display = "none";
      if (fixBuildProgressBar) fixBuildProgressBar.style.width = "0%";
      
      // Flash green after progress bar is hidden
      if (btnFixBuild) {
        btnFixBuild.classList.add("btn-success-flash");
        setTimeout(() => {
          btnFixBuild.classList.remove("btn-success-flash");
        }, 1000);
      }
    }, 2000);
  } catch (e: any) {
    log(`Fix build error: ${e}`);
    // Hide progress bar on error
    if (fixBuildProgress) fixBuildProgress.style.display = "none";
    if (fixBuildProgressBar) fixBuildProgressBar.style.width = "0%";
  }
}

// Listen for sync progress events
listen("sync-progress", (event: any) => {
  log(event.payload as string);
  lastProgressLine = null; // Reset progress line on new log message
});

// Listen for sync progress update events (updates same line)
listen("sync-progress-update", (event: any) => {
  const message = event.payload as string;
  
  // Extract percentage and format with symbolic progress bar
  const match = message.match(/\((\d+)%\)/);
  if (match) {
    const percentage = parseInt(match[1]);
    const barWidth = 50;
    const filled = Math.round((percentage / 100) * barWidth);
    const empty = barWidth - filled;
    const progressBar = `[${"I".repeat(filled)}${" ".repeat(empty)}](${percentage}%)`;
    
    let statusText = "Syncing...";
    if (percentage >= 100) {
      statusText = "Complete!";
    }
    
    const formattedMessage = `${progressBar}   ${statusText}`;
    
    if (lastProgressLine) {
      lastProgressLine.textContent = `[${new Date().toLocaleTimeString()}] ${formattedMessage}`;
    } else {
      lastProgressLine = document.createElement("div");
      lastProgressLine.className = "log-line";
      lastProgressLine.textContent = `[${new Date().toLocaleTimeString()}] ${formattedMessage}`;
      logContent?.appendChild(lastProgressLine);
    }
    
    logContent?.scrollTo(0, logContent.scrollHeight);
  } else if (lastProgressLine) {
    lastProgressLine.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
  }
  
  // Update sync progress bar if active
  if (syncProgress && syncProgress.style.display !== "none") {
    // Extract percentage from message if available
    const match = message.match(/\((\d+)%\)/);
    if (match) {
      const percentage = parseInt(match[1]);
      if (syncProgressBar) syncProgressBar.style.width = `${percentage}%`;
    }
  }
  
  // Update fix build progress bar if active
  if (fixBuildProgress && fixBuildProgress.style.display !== "none") {
    // Extract percentage from message if available
    const match = message.match(/\((\d+)%\)/);
    if (match) {
      const percentage = parseInt(match[1]);
      // Map 0-100% to 30-100% range (after clearing mods)
      const mappedPercentage = 30 + (percentage * 0.7);
      if (fixBuildProgressBar) fixBuildProgressBar.style.width = `${mappedPercentage}%`;
    }
  }
});

// Listen for install progress events
listen("install-progress", (event: any) => {
  const data = event.payload as any;
  const message = data.message;
  log(message);
  
  // Update install progress bar if active
  if (installProgress && installProgress.style.display !== "none") {
    // Extract percentage from message if available
    const match = message.match(/\((\d+(?:\.\d+)?)%\)/);
    if (match) {
      const percentage = parseFloat(match[1]);
      if (installProgressBar) installProgressBar.style.width = `${percentage}%`;
    }
  }
});

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

function log(message: string) {
  const line = document.createElement("div");
  line.className = "log-line";
  
  // Check if message contains percentage and add visual progress bar
  const match = message.match(/\((\d+(?:\.\d+)?)%\)/);
  if (match) {
    const percentage = parseFloat(match[1]);
    const barWidth = 20;
    const filled = Math.round((percentage / 100) * barWidth);
    const empty = barWidth - filled;
    const progressBar = `[${"=".repeat(filled)}${" ".repeat(empty)}] ${percentage.toFixed(1)}%`;
    const messageWithBar = message.replace(/\((\d+(?:\.\d+)?)%\)/, progressBar);
    line.textContent = `[${new Date().toLocaleTimeString()}] ${messageWithBar}`;
  } else {
    line.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
  }
  
  logContent?.appendChild(line);
  logContent?.scrollTo(0, logContent.scrollHeight);
}

// Titlebar button handlers
document.getElementById("btn-minimize")?.addEventListener("click", () => {
  appWindow.minimize();
});

document.getElementById("btn-maximize")?.addEventListener("click", async () => {
  const isMaximized = await appWindow.isMaximized();
  if (isMaximized) {
    appWindow.unmaximize();
  } else {
    appWindow.maximize();
  }
});

document.getElementById("btn-close")?.addEventListener("click", () => {
  appWindow.close();
});

// Disable context menu
document.addEventListener("contextmenu", (e) => {
  e.preventDefault();
});

document.addEventListener("DOMContentLoaded", init);
