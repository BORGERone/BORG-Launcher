// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::{Deserialize, Serialize};
use std::process::{Command, Stdio};
use std::sync::Mutex;
use tauri::{Manager, State, SystemTray, SystemTrayEvent, SystemTrayMenu, SystemTrayMenuItem, CustomMenuItem};
use std::io::{BufRead, BufReader, Read};
use std::thread;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use sha1::{Sha1, Digest};
#[cfg(target_os = "windows")]
use std::os::windows::process::ExitStatusExt;

// Get the base directory where the launcher is located
fn get_launcher_dir() -> String {
    // In dev mode, use project root; in release, use exe directory
    #[cfg(debug_assertions)]
    {
        String::from("E:/Project/BORGLauncher")
    }
    
    #[cfg(not(debug_assertions))]
    {
        let exe_path = env::current_exe().unwrap_or_else(|_| PathBuf::from("."));
        exe_path.parent()
            .and_then(|p| p.to_str())
            .unwrap_or(".")
            .to_string()
    }
}

// Get the config directory (AppData for config storage)
fn get_config_dir() -> String {
    #[cfg(debug_assertions)]
    {
        String::from("E:/Project/BORGLauncher")
    }
    
    #[cfg(not(debug_assertions))]
    {
        // Use %APPDATA%/BORG Launcher for config
        let appdata = env::var("APPDATA").unwrap_or_else(|_| String::from("."));
        let config_dir = Path::new(&appdata).join("BORG Launcher");
        
        // Create directory if it doesn't exist
        fs::create_dir_all(&config_dir).unwrap_or_else(|_| ());
        
        config_dir.to_str().unwrap_or(".").to_string()
    }
}

// Configuration structure - matches Python config.json
#[derive(Serialize, Deserialize, Clone, Debug)]
struct LauncherConfig {
    nickname: String,
    #[serde(rename = "ram_mb")]
    ram_mb: i32,
    #[serde(rename = "java_path")]
    java_path: String,
    #[serde(rename = "game_dir")]
    game_dir: String,
    #[serde(rename = "last_version")]
    last_version: String,
    #[serde(rename = "window_width")]
    window_width: i32,
    #[serde(rename = "window_height")]
    window_height: i32,
}

// GitHub API response structure
#[derive(Serialize, Deserialize, Debug)]
struct GitHubContent {
    name: String,
    path: String,
    #[serde(rename = "type")]
    content_type: String,
    download_url: Option<String>,
}

// Modrinth MRpack structures
#[derive(Serialize, Deserialize, Debug)]
struct ModrinthIndex {
    #[serde(rename = "formatVersion")]
    format_version: i32,
    game: String,
    #[serde(rename = "versionId")]
    version_id: String,
    name: String,
    summary: Option<String>,
    files: Vec<ModrinthFile>,
    dependencies: Option<serde_json::Value>,
}

#[derive(Serialize, Deserialize, Debug)]
struct ModrinthFile {
    path: String,
    hashes: ModrinthHashes,
    env: Option<serde_json::Value>,
    downloads: Vec<String>,
    #[serde(rename = "fileSize")]
    file_size: Option<i64>,
}

#[derive(Serialize, Deserialize, Debug)]
struct ModrinthHashes {
    sha1: Option<String>,
    sha512: Option<String>,
    murmur2: Option<String>,
}

impl Default for LauncherConfig {
    fn default() -> Self {
        Self {
            nickname: String::from("Player"),
            ram_mb: 4096,
            java_path: String::from("java"),
            game_dir: String::from("E:/Games/test"),
            last_version: String::from("neoforge-21.1.227"),
            window_width: 1200,
            window_height: 700,
        }
    }
}

// State
struct LauncherState {
    config: Mutex<LauncherConfig>,
}

// Load configuration from Python config module
#[tauri::command]
fn load_config_from_file() -> Result<LauncherConfig, String> {
    let launcher_dir = get_launcher_dir();
    
    let output = Command::new("python")
        .env("PYTHONPATH", &launcher_dir)
        .args(&["-m", "launcher.config", "--load"])
        .output()
        .map_err(|e| format!("Failed to load config: {}", e))?;
    
    if output.status.success() {
        let stdout = String::from_utf8_lossy(&output.stdout);
        let config: LauncherConfig = serde_json::from_str(&stdout)
            .map_err(|e| format!("Failed to parse config: {}", e))?;
        Ok(config)
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr);
        Err(format!("Config load error: {}", stderr))
    }
}

// Get configuration from state
#[tauri::command]
fn get_config(state: State<LauncherState>) -> LauncherConfig {
    state.config.lock().unwrap().clone()
}

// Save configuration to file via Python
#[tauri::command]
fn save_config_to_file(config: LauncherConfig) -> Result<(), String> {
    let launcher_dir = get_launcher_dir();
    let config_json = serde_json::to_string(&config)
        .map_err(|e| format!("Failed to serialize config: {}", e))?;
    
    let output = Command::new("python")
        .env("PYTHONPATH", &launcher_dir)
        .args(&["-m", "launcher.config", "--save-json", &config_json])
        .output()
        .map_err(|e| format!("Failed to save config: {}", e))?;
    
    if output.status.success() {
        Ok(())
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr);
        Err(format!("Config save error: {}", stderr))
    }
}

// Save configuration to state
#[tauri::command]
fn save_config(
    nickname: String,
    ram: i32,
    version: String,
    game_dir: String,
    window_width: i32,
    window_height: i32,
    state: State<LauncherState>,
) -> Result<(), String> {
    let mut config = state.config.lock().unwrap();
    config.nickname = nickname;
    config.ram_mb = ram;
    config.last_version = version;
    config.game_dir = game_dir;
    config.window_width = window_width;
    config.window_height = window_height;
    
    // Also save to file
    drop(config);
    let config_to_save = state.config.lock().unwrap().clone();
    save_config_to_file(config_to_save)
}

// Check server status
#[tauri::command]
async fn check_server_status() -> bool {
    // Try to connect to mod server
    match tokio::net::TcpStream::connect("91.210.149.24:25564").await {
        Ok(_) => true,
        Err(_) => false,
    }
}

// Launch game
#[tauri::command]
async fn launch_game(
    nickname: String,
    ram: i32,
    version: String,
    state: State<'_, LauncherState>,
) -> Result<String, String> {
    let config = state.config.lock().unwrap();
    let game_dir = config.game_dir.clone();
    drop(config);

    let launcher_dir = get_launcher_dir();

    // Call Python launcher with correct PYTHONPATH
    let output = Command::new("python")
        .env("PYTHONPATH", &launcher_dir)
        .args(&[
            "-m", "launcher.launch_game",
            "--nickname", &nickname,
            "--ram", &ram.to_string(),
            "--version", &version,
            "--game-dir", &game_dir,
        ])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .map_err(|e| format!("Failed to start launcher: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);

    if output.status.success() {
        Ok(format!("Game launched! {}", stdout))
    } else {
        Err(format!("Launch failed: {}", stderr))
    }
}

// Install game
#[tauri::command]
async fn install_game(
    window: tauri::Window,
    state: State<'_, LauncherState>,
) -> Result<(), String> {
    let config = state.config.lock().unwrap();
    let game_dir = config.game_dir.clone();
    drop(config);

    let launcher_dir = get_launcher_dir();

    // Spawn Python installer process
    let mut child = Command::new("python")
        .env("PYTHONPATH", &launcher_dir)
        .env("PYTHONUNBUFFERED", "1")  // Disable Python stdout buffering
        .args(&[
            "-u",  // Unbuffered stdout/stderr
            "-m", "launcher.download",
            "--install",
            "--game-dir", &game_dir,
        ])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Failed to start installer: {}", e))?;

    // Read output in separate thread
    let stdout = child.stdout.take().ok_or("Failed to capture stdout")?;
    let window_clone = window.clone();

    thread::spawn(move || {
        let reader = BufReader::with_capacity(1, stdout);  // Small buffer for real-time
        for line in reader.lines() {
            if let Ok(line) = line {
                let _ = window_clone.emit("install-progress", serde_json::json!({
                    "message": line,
                    "type": "info",
                }));
            }
        }
    });

    let stderr = child.stderr.take().ok_or("Failed to capture stderr")?;
    let window_clone2 = window.clone();
    thread::spawn(move || {
        let reader = BufReader::with_capacity(1, stderr);  // Small buffer for real-time
        for line in reader.lines() {
            if let Ok(line) = line {
                let _ = window_clone2.emit("install-progress", serde_json::json!({
                    "message": line,
                    "type": "error",
                }));
            }
        }
    });

    // Wait for completion
    let status = child.wait().map_err(|e| {
        let _ = window.emit("install-progress", serde_json::json!({
            "message": format!("Failed to wait for installer: {}", e),
            "type": "error",
        }));
        format!("Installer error: {}", e)
    })?;

    if status.success() {
        Ok(())
    } else {
        let error_msg = format!("Installation failed with exit code: {}", status.code().unwrap_or(-1));
        let _ = window.emit("install-progress", serde_json::json!({
            "message": error_msg.clone(),
            "type": "error",
        }));
        Err(error_msg)
    }
}

// Sync mods
#[tauri::command]
async fn sync_mods(state: State<'_, LauncherState>) -> Result<String, String> {
    let config = state.config.lock().unwrap();
    let game_dir = config.game_dir.clone();
    drop(config);

    let launcher_dir = get_launcher_dir();

    let output = Command::new("python")
        .env("PYTHONPATH", &launcher_dir)
        .args(&[
            "-m", "launcher.mod_sync",
            "--sync",
            "--game-dir", &game_dir,
        ])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .map_err(|e| format!("Failed to start sync: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout);

    if output.status.success() {
        Ok(format!("Mods synced! {}", stdout))
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr);
        Err(format!("Sync failed: {}", stderr))
    }
}

// Count files and folders in directory
#[tauri::command]
fn count_directory_items(path: String) -> Result<i32, String> {
    let dir_path = Path::new(&path);
    if !dir_path.exists() {
        return Ok(0);
    }
    
    let mut count = 0;
    if let Ok(entries) = fs::read_dir(dir_path) {
        for entry in entries {
            if entry.is_ok() {
                count += 1;
            }
        }
    }
    Ok(count)
}

// Simple commands for straightforward operation

#[tauri::command]
fn load_config_simple() -> Result<String, String> {
    let config_dir = get_config_dir();
    let config_path = format!("{}/config.json", config_dir);
    
    let content = fs::read_to_string(&config_path)
        .map_err(|e| format!("Failed to load config: {}", e))?;
    
    Ok(content)
}

#[tauri::command]
fn save_config_simple(config_json: String) -> Result<(), String> {
    let config_dir = get_config_dir();
    let config_path = format!("{}/config.json", config_dir);
    
    fs::write(&config_path, config_json)
        .map_err(|e| format!("Failed to save config: {}", e))?;
    
    Ok(())
}

#[tauri::command]
fn clear_mods_folder(game_dir: String) -> Result<String, String> {
    let mods_dir = Path::new(&game_dir).join("mods");
    
    if mods_dir.exists() {
        fs::remove_dir_all(&mods_dir)
            .map_err(|e| format!("Failed to clear mods folder: {}", e))?;
        fs::create_dir_all(&mods_dir)
            .map_err(|e| format!("Failed to recreate mods folder: {}", e))?;
    }
    
    Ok("Mods folder cleared".to_string())
}

#[tauri::command]
async fn launch_game_simple(nickname: String, ram_mb: i32, version: String, game_dir: String) -> Result<String, String> {
    let launcher_dir = get_launcher_dir();
    let output = Command::new("python")
        .current_dir(&launcher_dir)
        .env("PYTHONPATH", &launcher_dir)
        .args(&[
            "-m", "launcher.launch_game",
            "--nickname", &nickname,
            "--ram", &ram_mb.to_string(),
            "--version", &version,
            "--game-dir", &game_dir,
        ])
        .output()
        .map_err(|e| format!("Failed to launch: {}", e))?;
    
    if output.status.success() {
        Ok(String::from_utf8_lossy(&output.stdout).to_string())
    } else {
        Err(String::from_utf8_lossy(&output.stderr).to_string())
    }
}

#[tauri::command]
async fn install_game_simple(game_dir: String) -> Result<String, String> {
    let launcher_dir = get_launcher_dir();
    let output = Command::new("python")
        .env("PYTHONPATH", &launcher_dir)
        .args(&["-m", "launcher.download", "--install", "--game-dir", &game_dir])
        .output()
        .map_err(|e| format!("Failed to install: {}", e))?;
    
    if output.status.success() {
        Ok(String::from_utf8_lossy(&output.stdout).to_string())
    } else {
        Err(String::from_utf8_lossy(&output.stderr).to_string())
    }
}

#[tauri::command]
async fn sync_mods_simple(game_dir: String, window: tauri::Window) -> Result<String, String> {
    // Use MRpack sync instead of Python sync
    let result = sync_mods_from_mrpack(game_dir.clone(), window).await?;
    
    // Still sync fancymenu from GitHub after mods sync
    let _ = sync_fancymenu_from_github(game_dir).await;
    
    Ok(result)
}

// Sync fancymenu config from GitHub
#[tauri::command]
async fn sync_fancymenu_from_github(game_dir: String) -> Result<String, String> {
    let client = reqwest::Client::new();
    let api_url = "https://api.github.com/repos/BORGERone/BORG-Launcher/contents/config/fancymenu";
    
    // Get file list from GitHub API
    let response = client
        .get(api_url)
        .header("User-Agent", "BORG-Launcher")
        .send()
        .await
        .map_err(|e| format!("Failed to fetch from GitHub: {}", e))?;
    
    if !response.status().is_success() {
        return Err(format!("GitHub API returned status: {}", response.status()));
    }
    
    let contents: Vec<GitHubContent> = response
        .json()
        .await
        .map_err(|e| format!("Failed to parse GitHub response: {}", e))?;
    
    // Create target directory
    let target_dir = Path::new(&game_dir).join("config").join("fancymenu");
    fs::create_dir_all(&target_dir)
        .map_err(|e| format!("Failed to create directory: {}", e))?;
    
    // Download each file
    let mut downloaded = 0;
    for item in contents {
        if item.content_type == "file" {
            if let Some(download_url) = item.download_url {
                let file_response = client
                    .get(&download_url)
                    .header("User-Agent", "BORG-Launcher")
                    .send()
                    .await
                    .map_err(|e| format!("Failed to download {}: {}", item.name, e))?;
                
                if file_response.status().is_success() {
                    let file_content = file_response
                        .bytes()
                        .await
                        .map_err(|e| format!("Failed to read content: {}", e))?;
                    
                    let file_path = target_dir.join(&item.name);
                    fs::write(&file_path, file_content)
                        .map_err(|e| format!("Failed to write file {}: {}", item.name, e))?;
                    
                    downloaded += 1;
                }
            }
        }
    }
    
    Ok(format!("Downloaded {} files from config/fancymenu", downloaded))
}

// Download and install mods from MRpack
#[tauri::command]
async fn sync_mods_from_mrpack(game_dir: String, window: tauri::Window) -> Result<String, String> {
    let client = reqwest::Client::new();
    let mrpack_url = "https://github.com/BORGERone/BORG-Launcher/releases/download/Alpha/123.1.0.0.mrpack";

    // Function to calculate SHA1 hash of a file
    fn calculate_sha1(file_path: &Path) -> Result<String, std::io::Error> {
        let mut file = fs::File::open(file_path)?;
        let mut hasher = Sha1::new();
        let mut buffer = [0u8; 8192];
        
        loop {
            let n = file.read(&mut buffer)?;
            if n == 0 {
                break;
            }
            hasher.update(&buffer[..n]);
        }
        
        Ok(hex::encode(hasher.finalize()))
    }

    // Function to create progress bar string
    fn create_progress_bar(current: usize, total: usize) -> String {
        let percentage = if total > 0 {
            (current as f64 / total as f64 * 100.0) as usize
        } else {
            0
        };
        let filled = (percentage / 2) as usize; // 50 characters total, so percentage/2
        
        // Add extra I characters to compensate for character width difference
        // Add 1 extra I for every 9 filled characters
        let extra_filled = filled / 13;
        let total_filled = filled + extra_filled;
        
        // Increase bar width to accommodate extra characters
        let bar_width = 50 + extra_filled;
        let mut bar: Vec<char> = " ".repeat(bar_width).chars().collect();
        for i in 0..total_filled.min(bar_width) {
            if i < bar.len() {
                bar[i] = 'I';
            }
        }
        format!("[{}]({}%)", bar.iter().collect::<String>(), percentage)
    }

    // Function to emit progress event
    fn emit_progress(window: &tauri::Window, message: String) {
        let _ = window.emit("sync-progress", message);
    }

    // Function to emit progress update (for updating same line)
    fn emit_progress_update(window: &tauri::Window, message: String) {
        let _ = window.emit("sync-progress-update", message);
    }

    // Function to pad filename to fixed width
    fn pad_filename(filename: &str, width: usize) -> String {
        if filename.len() >= width {
            // Truncate if too long
            filename.chars().take(width).collect()
        } else {
            // Pad with spaces if too short
            format!("{}{}", filename, " ".repeat(width - filename.len()))
        }
    }

    // Download MRpack file
    let response = client
        .get(mrpack_url)
        .header("User-Agent", "BORG-Launcher")
        .send()
        .await
        .map_err(|e| format!("Failed to download MRpack: {}", e))?;
    
    if !response.status().is_success() {
        return Err(format!("Failed to download MRpack: status {}", response.status()));
    }
    
    let mrpack_bytes = response
        .bytes()
        .await
        .map_err(|e| format!("Failed to read MRpack: {}", e))?;
    
    // Extract ZIP archive
    let cursor = std::io::Cursor::new(mrpack_bytes);
    let mut archive = zip::ZipArchive::new(cursor)
        .map_err(|e| format!("Failed to open MRpack as ZIP: {}", e))?;
    
    // Find and read modrinth.index.json
    let mut index_content = String::new();
    {
        let mut index_file = archive.by_name("modrinth.index.json")
            .map_err(|e| format!("modrinth.index.json not found in MRpack: {}", e))?;
        
        index_file.read_to_string(&mut index_content)
            .map_err(|e| format!("Failed to read index.json: {}", e))?;
    }
    
    // Parse index with more flexible structure
    let index: ModrinthIndex = serde_json::from_str(&index_content)
        .map_err(|e| format!("Failed to parse modrinth.index.json: {}. JSON was: {}", e, index_content))?;
    
    // Create mods directory
    let mods_dir = Path::new(&game_dir).join("mods");
    fs::create_dir_all(&mods_dir)
        .map_err(|e| format!("Failed to create mods directory: {}", e))?;

    // Extract overrides folder
    for i in 0..archive.len() {
        let mut file = archive.by_index(i).map_err(|e| format!("Failed to access file in archive: {}", e))?;
        let file_path = file.name();
        
        // Check if file is in overrides folder
        if file_path.starts_with("overrides/") {
            // Remove "overrides/" prefix to get relative path
            let relative_path = file_path.strip_prefix("overrides/")
                .ok_or("Failed to strip overrides prefix")?;
            
            // Skip directories
            if file.name().ends_with('/') {
                continue;
            }
            
            // Create target path in game directory
            let target_path = Path::new(&game_dir).join(relative_path);
            
            // Create parent directories if needed
            if let Some(parent) = target_path.parent() {
                fs::create_dir_all(parent)
                    .map_err(|e| format!("Failed to create directory {}: {}", parent.display(), e))?;
            }
            
            // Extract file
            let mut output_file = fs::File::create(&target_path)
                .map_err(|e| format!("Failed to create file {}: {}", target_path.display(), e))?;
            
            std::io::copy(&mut file, &mut output_file)
                .map_err(|e| format!("Failed to write file {}: {}", target_path.display(), e))?;
        }
    }
    
    // Download each mod
    let mut downloaded = 0;
    let mut skipped = 0;
    let total_mods = index.files.iter().filter(|f| f.path.starts_with("mods/")).count();
    
    emit_progress(&window, format!("Starting download of {} mods...", total_mods));
    
    for (_index, file) in index.files.iter().enumerate() {
        // Only process files in mods directory
        if !file.path.starts_with("mods/") {
            continue;
        }
        
        // Get download URL (prefer first one)
        if let Some(download_url) = file.downloads.first() {
            // Extract filename from path
            let filename = file.path.split('/').last().unwrap_or(&file.path);
            let mod_path = mods_dir.join(filename);
            
            // Check if file already exists and hash matches
            if mod_path.exists() {
                if let Some(expected_hash) = &file.hashes.sha1 {
                    match calculate_sha1(&mod_path) {
                        Ok(actual_hash) => {
                            if actual_hash == *expected_hash {
                                skipped += 1;
                                let progress = create_progress_bar(downloaded + skipped, total_mods);
                                let padded_filename = pad_filename(filename, 50);
                                emit_progress_update(&window, format!("{}   Skipping: {}", progress, padded_filename));
                                continue;
                            }
                        }
                        Err(_) => {
                            // If hash calculation fails, re-download
                        }
                    }
                }
            }
            
            let progress = create_progress_bar(downloaded + skipped, total_mods);
            let padded_filename = pad_filename(filename, 50);
            emit_progress_update(&window, format!("{}   Downloading: {}", progress, padded_filename));
            
            let mod_response = client
                .get(download_url)
                .header("User-Agent", "BORG-Launcher")
                .send()
                .await
                .map_err(|e| format!("Failed to download mod {}: {}", file.path, e))?;

            if mod_response.status().is_success() {
                let mod_content = mod_response
                    .bytes()
                    .await
                    .map_err(|e| format!("Failed to read mod content: {}", e))?;

                fs::write(&mod_path, mod_content)
                    .map_err(|e| format!("Failed to write mod {}: {}", filename, e))?;

                downloaded += 1;
            }
        }
    }

    let final_progress = create_progress_bar(downloaded + skipped, total_mods);
    emit_progress_update(&window, format!("{}   Complete!", final_progress));
    
    Ok(format!("Downloaded {} mods, skipped {} existing mods from MRpack", downloaded, skipped))
}

#[tauri::command]
fn read_news(game_dir: String) -> Result<String, String> {
    let news_path = format!("{}/news.md", game_dir.replace('/', "\\"));
    match fs::read_to_string(&news_path) {
        Ok(content) => Ok(content),
        Err(e) => Err(format!("Failed to read news.md: {}", e)),
    }
}

#[tauri::command]
fn hide_window(window: tauri::Window) {
    let _ = window.hide();
}

#[tauri::command]
fn show_window(window: tauri::Window) {
    let _ = window.show();
    let _ = window.set_focus();
}

#[tauri::command]
fn is_minecraft_running() -> bool {
    // Check if Minecraft process is running
    #[cfg(target_os = "windows")]
    {
        use std::process::Command;
        let output = Command::new("tasklist")
            .args(&["/FI", "IMAGENAME eq java.exe", "/FO", "CSV"])
            .output()
            .unwrap_or_else(|_| std::process::Output {
                status: std::process::ExitStatus::from_raw(1),
                stdout: vec![],
                stderr: vec![],
            });

        let stdout = String::from_utf8_lossy(&output.stdout);
        stdout.contains("java.exe")
    }

    #[cfg(not(target_os = "windows"))]
    {
        false
    }
}

fn main() {
    // Create system tray menu
    let tray_menu = SystemTrayMenu::new()
        .add_item(CustomMenuItem::new("show".to_string(), "Show"))
        .add_item(CustomMenuItem::new("hide".to_string(), "Hide"))
        .add_native_item(SystemTrayMenuItem::Separator)
        .add_item(CustomMenuItem::new("quit".to_string(), "Quit"));

    let system_tray = SystemTray::new().with_menu(tray_menu);

    tauri::Builder::default()
        .system_tray(system_tray)
        .on_system_tray_event(|app, event| match event {
            SystemTrayEvent::LeftClick {
                position: _,
                size: _,
                ..
            } => {
                let window = app.get_window("main").unwrap();
                let _ = window.show();
                let _ = window.set_focus();
            }
            SystemTrayEvent::MenuItemClick { id, .. } => {
                let window = app.get_window("main").unwrap();
                match id.as_str() {
                    "show" => {
                        let _ = window.show();
                        let _ = window.set_focus();
                    }
                    "hide" => {
                        let _ = window.hide();
                    }
                    "quit" => {
                        std::process::exit(0);
                    }
                    _ => {}
                }
            }
            _ => {}
        })
        .manage(LauncherState {
            config: Mutex::new(LauncherConfig::default()),
        })
        .setup(|app| {
            let state: State<LauncherState> = app.state();
            let mut config_guard = state.config.lock().unwrap();
            let config_dir = get_config_dir();
            let config_path = format!("{}/config.json", config_dir);
            
            // Load config from file on startup
            match fs::read_to_string(&config_path) {
                Ok(content) => {
                    match serde_json::from_str::<LauncherConfig>(&content) {
                        Ok(config) => {
                            *config_guard = config;
                        }
                        Err(_) => {
                            // Use defaults if parsing fails
                        }
                    }
                }
                Err(_) => {
                    // Use defaults if file doesn't exist
                }
            }
            Ok(())
        })
        .on_window_event(|event| {
            if let tauri::WindowEvent::Resized(size) = event.event() {
                // Save window size when resized
                let width = size.width as i32;
                let height = size.height as i32;
                
                // Only save if reasonable size (not minimized)
                if width > 100 && height > 100 {
                    if let Ok(config) = load_config_from_file() {
                        let new_config = LauncherConfig {
                            window_width: width,
                            window_height: height,
                            ..config
                        };
                        let _ = save_config_to_file(new_config);
                    }
                }
            }
        })
        .invoke_handler(tauri::generate_handler![
            load_config_from_file,
            get_config,
            save_config,
            save_config_to_file,
            check_server_status,
            launch_game,
            install_game,
            sync_mods,
            load_config_simple,
            save_config_simple,
            clear_mods_folder,
            launch_game_simple,
            install_game_simple,
            sync_mods_simple,
            sync_mods_from_mrpack,
            sync_fancymenu_from_github,
            read_news,
            hide_window,
            show_window,
            is_minecraft_running,
            count_directory_items,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
