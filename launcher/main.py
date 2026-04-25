"""
BORG Minecraft Launcher v2 - Main module
Integrates download, mod sync, and game launch
"""

import os
import sys
import json
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pathlib import Path
from threading import Thread
import minecraft_launcher_lib as mll

# Import our modules
from launcher.download import install_all, download_vanilla_minecraft, install_neoforge, find_java, GAME_DIR
from launcher.mod_sync import sync_mods_auto, check_server_online, ModSyncClient

# Launcher configuration
CONFIG_FILE = Path(__file__).parent.parent / "config.json"
DEFAULT_CONFIG = {
    "nickname": "Player",
    "ram_mb": 4096,
    "java_path": "java",
    "game_dir": str(GAME_DIR),
    "last_version": "neoforge-21.1.227"
}


def load_config():
    """Load launcher configuration"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config):
    """Save launcher configuration"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Error saving config: {e}")


def get_installed_versions(game_dir=None):
    """Get list of installed Minecraft versions"""
    if game_dir is None:
        game_dir = GAME_DIR
    try:
        versions = mll.utils.get_installed_versions(str(game_dir))
        result = []
        for v in versions:
            version_type = "vanilla"
            if "forge" in v["id"].lower() or "neoforge" in v["id"].lower():
                version_type = "modded"
            elif "fabric" in v["id"].lower():
                version_type = "fabric"
            result.append({
                "id": v["id"],
                "type": version_type
            })
        return result
    except Exception as e:
        print(f"Error getting versions: {e}")
        return []


def launch_minecraft(version_id, username, ram_mb, game_dir=None):
    """Launch Minecraft with specified parameters"""
    if game_dir is None:
        game_dir = GAME_DIR
    game_dir = str(game_dir)
    java_path = find_java(game_dir)
    
    try:
        # Generate launch command
        options = {
            "username": username,
            "uuid": "00000000000000000000000000000000",
            "token": "0",
            "launcherName": "BORGLauncher",
            "launcherVersion": "2.0",
            "gameDirectory": game_dir,
            "jvmArguments": [
                f"-Xmx{ram_mb}M",
                f"-Xms{ram_mb}M",
            ],
            "executablePath": java_path,
        }
        
        minecraft_command = mll.command.get_minecraft_command(
            version=version_id,
            minecraft_directory=game_dir,
            options=options
        )
        
        print(f"Launch command: {' '.join(minecraft_command[:8])}...")
        
        # Launch as detached process
        if sys.platform == "win32":
            # Windows: use creationflags to hide console
            subprocess.Popen(
                minecraft_command,
                cwd=game_dir,
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            # Unix: use start_new_session
            subprocess.Popen(
                minecraft_command,
                cwd=game_dir,
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        
        return True, "Game launched successfully"
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, f"Launch error: {e}"


class StdoutRedirector:
    """Redirects stdout to the log widget"""
    def __init__(self, log_func):
        self.log_func = log_func
        self.original_stdout = sys.stdout
    
    def write(self, message):
        if message.strip():
            self.log_func(message.strip())
    
    def flush(self):
        pass
    
    def restore(self):
        sys.stdout = self.original_stdout


class LauncherGUI:
    """Main launcher GUI using tkinter"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("BORG Minecraft Launcher v2")
        self.root.geometry("650x550")
        self.root.minsize(600, 500)
        self.root.resizable(True, True)
        
        # Load config
        self.config = load_config()
        
        # State
        self.is_installing = False
        self.is_syncing = False
        self.is_launching = False
        
        self._create_ui()
        self._check_installation()
    
    def _create_ui(self):
        """Create user interface"""
        # Configure grid weights for resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Main frame with padding
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)  # Log area expands
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="BORG Minecraft Launcher",
            font=("Helvetica", 16, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Server status
        status_frame = ttk.LabelFrame(main_frame, text="Статус сервера модов", padding="10")
        status_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.server_status_var = tk.StringVar(value="Проверка...")
        self.server_status_label = ttk.Label(
            status_frame,
            textvariable=self.server_status_var,
            foreground="gray"
        )
        self.server_status_label.grid(row=0, column=0)
        
        # Settings frame
        settings_frame = ttk.LabelFrame(main_frame, text="Настройки", padding="10")
        settings_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Nickname
        ttk.Label(settings_frame, text="Никнейм:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.nickname_var = tk.StringVar(value=self.config["nickname"])
        ttk.Entry(settings_frame, textvariable=self.nickname_var, width=30).grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # RAM
        ttk.Label(settings_frame, text="RAM (МБ):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.ram_var = tk.IntVar(value=self.config["ram_mb"])
        ram_combo = ttk.Combobox(settings_frame, textvariable=self.ram_var, values=[2048, 4096, 6144, 8192, 12288, 16384], width=10)
        ram_combo.grid(row=1, column=1, sticky=tk.W, padx=5)
        
        # Version
        ttk.Label(settings_frame, text="Версия:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.version_var = tk.StringVar(value=self.config["last_version"])
        self.version_combo = ttk.Combobox(settings_frame, textvariable=self.version_var, values=[], width=30)
        self.version_combo.grid(row=2, column=1, sticky=tk.W, padx=5)
        self._update_version_list()
        
        # Progress bar
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100, mode='determinate', length=400)
        self.progress_bar.grid(row=3, column=0, columnspan=2, pady=(10, 5))
        
        # Status text
        self.status_var = tk.StringVar(value="Готов")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var)
        self.status_label.grid(row=4, column=0, columnspan=2, pady=(0, 10))
        
        # Log area
        log_frame = ttk.LabelFrame(main_frame, text="Лог", padding="5")
        log_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame, 
            width=60, 
            height=8, 
            wrap=tk.WORD,
            state='normal'  # Allow text selection
        )
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Bind right-click context menu for copy
        self.log_text.bind('<Button-3>', self._show_log_context_menu)
        self.log_text.bind('<Control-c>', lambda e: self._copy_log_selection())
        
        # Create context menu
        self.log_menu = tk.Menu(self.root, tearoff=0)
        self.log_menu.add_command(label="Копировать", command=self._copy_log_selection)
        self.log_menu.add_command(label="Выделить всё", command=self._select_all_log)
        self.log_menu.add_separator()
        self.log_menu.add_command(label="Очистить", command=self._clear_log)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=(5, 10))
        
        self.install_btn = ttk.Button(button_frame, text="Скачать игру", command=self._on_install, width=20)
        self.install_btn.grid(row=0, column=0, padx=5, pady=2)
        
        self.sync_btn = ttk.Button(button_frame, text="Синхронизировать моды", command=self._on_sync, width=25)
        self.sync_btn.grid(row=0, column=1, padx=5, pady=2)
        
        self.play_btn = ttk.Button(button_frame, text="ИГРАТЬ", command=self._on_play, width=15)
        self.play_btn.grid(row=0, column=2, padx=5, pady=2)
        
        # Settings button (smaller, to the right)
        self.settings_btn = ttk.Button(button_frame, text="⚙ Настройки", command=self._open_settings, width=12)
        self.settings_btn.grid(row=0, column=3, padx=(15, 5), pady=2)
        
        # Configure styles
        style = ttk.Style()
        style.configure('Accent.TButton', font=('Helvetica', 10, 'bold'))
        
        # Check server status in background
        Thread(target=self._check_server_status, daemon=True).start()
    
    def _show_log_context_menu(self, event):
        """Show right-click context menu"""
        try:
            self.log_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.log_menu.grab_release()
    
    def _copy_log_selection(self):
        """Copy selected text to clipboard"""
        try:
            selected = self.log_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.root.clipboard_clear()
            self.root.clipboard_append(selected)
        except tk.TclError:
            pass  # No selection
    
    def _select_all_log(self):
        """Select all text in log"""
        self.log_text.tag_add(tk.SEL, "1.0", tk.END)
        self.log_text.mark_set(tk.INSERT, "1.0")
        self.log_text.see(tk.END)
        return 'break'
    
    def _clear_log(self):
        """Clear log text"""
        self.log_text.delete("1.0", tk.END)
    
    def _log(self, message):
        """Add message to log"""
        import datetime
        timestamp = datetime.datetime.now().strftime("[%H:%M:%S]")
        try:
            self.log_text.insert(tk.END, f"{timestamp} {message}\n")
            self.log_text.see(tk.END)
        except:
            pass  # Widget might not be ready
        # Don't print in windowed mode - it can cause errors
        # print(f"{timestamp} {message}")
    
    def _set_status(self, message):
        """Update status label"""
        self.status_var.set(message)
        self.root.update_idletasks()
    
    def _update_version_list(self):
        """Update version dropdown"""
        # Use game_dir from config
        game_dir = Path(self.config.get("game_dir", GAME_DIR))
        versions = get_installed_versions(game_dir)
        version_ids = [v["id"] for v in versions]
        self.version_combo['values'] = version_ids
        
        # Select last version if available
        if self.config["last_version"] in version_ids:
            self.version_var.set(self.config["last_version"])
        elif version_ids:
            # Prefer neoforge versions
            neoforge_versions = [v for v in version_ids if "neoforge" in v.lower()]
            if neoforge_versions:
                self.version_var.set(neoforge_versions[0])
            else:
                self.version_var.set(version_ids[0])
    
    def _check_server_status(self):
        """Check mod server status in background"""
        try:
            is_online = check_server_online()
            self.root.after(0, self._update_server_status, is_online)
        except:
            self.root.after(0, self._update_server_status, False)
    
    def _update_server_status(self, is_online):
        """Update server status UI"""
        if is_online:
            self.server_status_var.set("Онлайн")
            self.server_status_label.configure(foreground="green")
        else:
            self.server_status_var.set("Офлайн")
            self.server_status_label.configure(foreground="red")
    
    def _check_installation(self):
        """Check if Minecraft is installed"""
        # Use game_dir from config
        game_dir = Path(self.config.get("game_dir", GAME_DIR))
        versions = get_installed_versions(game_dir)
        neoforge_installed = any("neoforge" in v["id"].lower() for v in versions)
        
        if not neoforge_installed:
            self._log("Minecraft + NeoForge не установлены")
            self._set_status("Требуется скачивание игры")
            self.play_btn.configure(state='disabled')
            messagebox.showinfo(
                "Установка",
                "Minecraft 1.21.1 + NeoForge не установлены.\n\n"
                "Нажмите 'Скачать игру' для установки."
            )
        else:
            self._log(f"Найдено {len(versions)} версий")
            self._set_status("Готов к запуску")
    
    def _on_install(self):
        """Handle install button"""
        if self.is_installing:
            return
        
        self.is_installing = True
        self.install_btn.configure(state='disabled')
        self._set_status("Скачивание игры...")
        self._log("Начинаю скачивание Minecraft 1.21.1 + NeoForge...")
        
        def install_thread():
            redirector = None
            try:
                # Redirect stdout to log widget
                redirector = StdoutRedirector(self._log)
                sys.stdout = redirector
                sys.stderr = redirector
                
                # Use install_all from download module with config game_dir
                import launcher.download as download
                game_dir = Path(self.config.get("game_dir", GAME_DIR))
                download.GAME_DIR = game_dir
                
                # Create game directory if needed
                game_dir.mkdir(parents=True, exist_ok=True)
                
                success = download.install_all()
                
                # Restore stdout
                if redirector:
                    redirector.restore()
                
                self.root.after(0, self._on_install_complete, success)
            except Exception as e:
                # Restore stdout
                if redirector:
                    redirector.restore()
                self._log(f"Ошибка установки: {e}")
                import traceback
                self._log(traceback.format_exc())
                self.root.after(0, self._on_install_complete, False)
        
        Thread(target=install_thread, daemon=True).start()
    
    def _on_install_complete(self, success):
        """Called when installation completes"""
        self.is_installing = False
        self.install_btn.configure(state='normal')
        
        if success:
            self._log("Установка завершена успешно!")
            self._set_status("Установка завершена")
            self._update_version_list()
            self.play_btn.configure(state='normal')
            messagebox.showinfo("Успех", "Minecraft 1.21.1 + NeoForge установлены!")
        else:
            self._log("Установка не удалась")
            self._set_status("Ошибка установки")
            messagebox.showerror("Ошибка", "Не удалось установить игру.\nСм. лог для деталей.")
    
    def _on_sync(self):
        """Handle sync button"""
        if self.is_syncing:
            return
        
        self.is_syncing = True
        self.sync_btn.configure(state='disabled')
        self._set_status("Синхронизация модов...")
        self._log("Начинаю синхронизацию модов...")
        
        def sync_thread():
            redirector = None
            try:
                # Redirect stdout to log widget
                redirector = StdoutRedirector(self._log)
                sys.stdout = redirector
                sys.stderr = redirector
                
                def progress_callback(filename, current, total):
                    self._log(f"Скачивание {filename} ({current}/{total})")
                    progress = (current / total) * 100
                    self.root.after(0, lambda: self.progress_var.set(progress))
                
                # Use mods_dir from config game_dir
                game_dir = Path(self.config.get("game_dir", GAME_DIR))
                mods_dir = game_dir / "mods"
                success, message = sync_mods_auto(auto_download=True, progress_callback=progress_callback, mods_dir=mods_dir)
                
                # Restore stdout
                if redirector:
                    redirector.restore()
                
                self.root.after(0, self._on_sync_complete, success, message)
            except Exception as e:
                # Restore stdout
                if redirector:
                    redirector.restore()
                self._log(f"Ошибка синхронизации: {e}")
                import traceback
                self._log(traceback.format_exc())
                self.root.after(0, self._on_sync_complete, False, str(e))
        
        Thread(target=sync_thread, daemon=True).start()
    
    def _on_sync_complete(self, success, message):
        """Called when sync completes"""
        self.is_syncing = False
        self.sync_btn.configure(state='normal')
        self.progress_var.set(0)
        
        if success:
            self._log(f"Синхронизация завершена: {message}")
            self._set_status("Моды синхронизированы")
        else:
            self._log(f"Ошибка синхронизации: {message}")
            self._set_status("Ошибка синхронизации")
            
            # Ask if user wants to continue anyway
            result = messagebox.askyesno(
                "Ошибка синхронизации",
                f"Не удалось синхронизировать моды:\n{message}\n\n"
                "Запустить игру без синхронизации?"
            )
            if result:
                self._log("Пользователь выбрал запуск без синхронизации")
    
    def _on_play(self):
        """Handle play button - Full sequence: sync + launch"""
        if self.is_launching or self.is_syncing:
            return
        
        # Save config
        self.config["nickname"] = self.nickname_var.get()
        self.config["ram_mb"] = self.ram_var.get()
        self.config["last_version"] = self.version_var.get()
        save_config(self.config)
        
        version = self.version_var.get()
        username = self.nickname_var.get()
        ram_mb = self.ram_var.get()
        
        if not version:
            messagebox.showerror("Ошибка", "Выберите версию")
            return
        
        if not username:
            messagebox.showerror("Ошибка", "Введите никнейм")
            return
        
        self.is_launching = True
        self.play_btn.configure(state='disabled')
        
        self._set_status("Проверка модов...")
        self._log(f"Запуск игры: {version}, ник: {username}, RAM: {ram_mb}MB")
        
        def launch_sequence():
            try:
                # Step 1: Check server and sync mods
                self._log("Подключение к серверу модов...")
                is_online = check_server_online()
                
                if is_online:
                    self._log("Сервер онлайн, синхронизация модов...")
                    
                    def progress_callback(filename, current, total):
                        self._log(f"Скачивание {filename} ({current}/{total})")
                        progress = (current / total) * 100
                        self.root.after(0, lambda: self.progress_var.set(progress))
                    
                    # Use mods_dir from config game_dir
                    game_dir = Path(self.config.get("game_dir", GAME_DIR))
                    mods_dir = game_dir / "mods"
                    success, message = sync_mods_auto(auto_download=True, progress_callback=progress_callback, mods_dir=mods_dir)
                    self.root.after(0, lambda: self.progress_var.set(0))
                    
                    if success:
                        self._log(f"Синхронизация успешна: {message}")
                    else:
                        self._log(f"Ошибка синхронизации: {message}")
                        # Ask user
                        self.root.after(0, lambda: self._ask_continue_after_sync_error(message, version, username, ram_mb))
                        return
                else:
                    self._log("Сервер модов офлайн, пропускаю синхронизацию")
                    # Ask user
                    result = messagebox.askyesno(
                        "Сервер недоступен",
                        "Сервер модов офлайн.\n\nЗапустить игру без синхронизации модов?"
                    )
                    if not result:
                        self.root.after(0, self._on_launch_complete)
                        return
                
                # Step 2: Launch game
                self.root.after(0, lambda: self._do_launch(version, username, ram_mb))
                
            except Exception as e:
                self._log(f"Ошибка запуска: {e}")
                import traceback
                self._log(traceback.format_exc())
                self.root.after(0, self._on_launch_complete)
        
        Thread(target=launch_sequence, daemon=True).start()
    
    def _ask_continue_after_sync_error(self, error_message, version, username, ram_mb):
        """Ask user if continue after sync error"""
        result = messagebox.askyesno(
            "Ошибка синхронизации",
            f"Не удалось синхронизировать моды:\n{error_message}\n\n"
            "Запустить игру без синхронизации?"
        )
        if result:
            self._do_launch(version, username, ram_mb)
        else:
            self._on_launch_complete()
    
    def _do_launch(self, version, username, ram_mb):
        """Actually launch the game"""
        self._set_status("Запуск игры...")
        self._log("Запуск Minecraft...")
        
        # Use game_dir from config
        game_dir = Path(self.config.get("game_dir", GAME_DIR))
        success, message = launch_minecraft(version, username, ram_mb, game_dir)
        
        if success:
            self._log("Игра запущена!")
            self._set_status("Игра запущена")
        else:
            self._log(f"Ошибка запуска: {message}")
            self._set_status("Ошибка запуска")
            messagebox.showerror("Ошибка", f"Не удалось запустить игру:\n{message}")
        
        self._on_launch_complete()
    
    def _on_launch_complete(self):
        """Reset UI after launch"""
        self.is_launching = False
        self.progress_var.set(0)
        self.play_btn.configure(state='normal')
    
    def _open_settings(self):
        """Open settings dialog"""
        dialog = SettingsDialog(self.root, self.config)
        if dialog.result:
            # Update config with new values
            self.config.update(dialog.result)
            save_config(self.config)
            
            # Update UI
            self.ram_var.set(self.config["ram_mb"])
            self._log(f"Настройки сохранены: RAM={self.config['ram_mb']}MB, папка={self.config['game_dir']}")
            messagebox.showinfo("Настройки", "Настройки сохранены успешно!")


class SettingsDialog:
    """Settings dialog with RAM slider and game folder selection"""
    
    def __init__(self, parent, config):
        self.result = None
        self.config = config.copy()
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Настройки")
        self.dialog.geometry("450x420")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f'+{x}+{y}')
        
        self._create_ui()
        
        # Wait for dialog to close
        parent.wait_window(self.dialog)
    
    def _create_ui(self):
        """Create settings dialog UI"""
        frame = ttk.Frame(self.dialog, padding="15")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(
            frame,
            text="Настройки лаунчера",
            font=("Helvetica", 12, "bold")
        ).pack(pady=(0, 15))
        
        # RAM Slider
        ram_frame = ttk.LabelFrame(frame, text="Выделение ОЗУ (RAM)", padding="8")
        ram_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.ram_var = tk.IntVar(value=self.config.get("ram_mb", 4096))
        
        # RAM value label
        self.ram_label = ttk.Label(ram_frame, text=f"{self.ram_var.get()} MB", font=("Helvetica", 10, "bold"))
        self.ram_label.pack()
        
        # RAM slider
        ram_slider = ttk.Scale(
            ram_frame,
            from_=1024,
            to=32768,
            orient=tk.HORIZONTAL,
            variable=self.ram_var,
            command=self._on_ram_change
        )
        ram_slider.pack(fill=tk.X, pady=5)
        
        # RAM markers
        markers_frame = ttk.Frame(ram_frame)
        markers_frame.pack(fill=tk.X)
        ttk.Label(markers_frame, text="1GB").pack(side=tk.LEFT)
        ttk.Label(markers_frame, text="16GB").pack(side=tk.RIGHT)
        
        # Quick RAM buttons
        quick_ram_frame = ttk.Frame(ram_frame)
        quick_ram_frame.pack(fill=tk.X, pady=(5, 0))
        
        for ram in [2048, 4096, 6144, 8192, 16384]:
            ttk.Button(
                quick_ram_frame,
                text=f"{ram//1024}GB",
                command=lambda r=ram: self._set_ram(r),
                width=6
            ).pack(side=tk.LEFT, padx=2)
        
        # Game folder selection
        folder_frame = ttk.LabelFrame(frame, text="Папка Minecraft", padding="8")
        folder_frame.pack(fill=tk.X, pady=(0, 10))
        folder_frame.columnconfigure(0, weight=1)
        
        self.folder_var = tk.StringVar(value=self.config.get("game_dir", str(GAME_DIR)))
        
        # Path display with better layout
        folder_entry = ttk.Entry(folder_frame, textvariable=self.folder_var, state='readonly')
        folder_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10), pady=2)
        
        browse_btn = ttk.Button(folder_frame, text="Обзор...", command=self._browse_folder, width=10)
        browse_btn.grid(row=0, column=1, pady=2)
        
        # Buttons - anchored to bottom with margin
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=(20, 5), side=tk.BOTTOM)
        
        save_btn = ttk.Button(button_frame, text="Сохранить", command=self._save, width=14)
        save_btn.pack(side=tk.RIGHT, padx=8, pady=8)
        
        cancel_btn = ttk.Button(button_frame, text="Отмена", command=self._cancel, width=14)
        cancel_btn.pack(side=tk.RIGHT, padx=8, pady=8)
    
    def _on_ram_change(self, value):
        """Handle RAM slider change"""
        ram = int(float(value))
        # Round to nearest 512MB
        ram = (ram // 512) * 512
        self.ram_var.set(ram)
        self.ram_label.configure(text=f"{ram} MB ({ram//1024}GB)")
    
    def _set_ram(self, value):
        """Set RAM from quick button"""
        self.ram_var.set(value)
        self.ram_label.configure(text=f"{value} MB ({value//1024}GB)")
    
    def _browse_folder(self):
        """Open folder browser dialog"""
        from tkinter import filedialog
        folder = filedialog.askdirectory(
            title="Выберите папку для Minecraft",
            initialdir=self.folder_var.get()
        )
        if folder:
            self.folder_var.set(folder)
    
    def _save(self):
        """Save settings and close dialog"""
        self.result = {
            "ram_mb": self.ram_var.get(),
            "game_dir": self.folder_var.get()
        }
        self.dialog.destroy()
    
    def _cancel(self):
        """Cancel and close dialog"""
        self.dialog.destroy()


def main():
    """Main entry point"""
    # Create root window
    root = tk.Tk()
    
    # Set icon if available
    # root.iconbitmap("icon.ico")
    
    # Create and run app
    app = LauncherGUI(root)
    
    # Center window
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (600 // 2)
    y = (root.winfo_screenheight() // 2) - (500 // 2)
    root.geometry(f'+{x}+{y}')
    
    root.mainloop()


if __name__ == "__main__":
    main()
