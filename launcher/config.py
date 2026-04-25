"""
Configuration management for BORG Launcher
Settings stored in %LOCALAPPDATA%\BORGLauncher\config.json
"""

import json
import os
from pathlib import Path
from typing import Dict, Any


def get_config_dir() -> Path:
    """Get configuration directory in AppData/Local"""
    local_appdata = os.environ.get('LOCALAPPDATA')
    if not local_appdata:
        local_appdata = os.path.expanduser('~/.local/share')
    
    config_dir = Path(local_appdata) / 'BORGLauncher'
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_file() -> Path:
    """Get path to config.json"""
    return get_config_dir() / 'config.json'


DEFAULT_CONFIG = {
    "nickname": "Player",
    "ram_mb": 4096,
    "java_path": "java",
    "game_dir": "E:/Games/test",
    "last_version": "neoforge-21.1.227",
    "window_width": 1200,
    "window_height": 700
}


def load_config() -> Dict[str, Any]:
    """Load configuration from JSON file"""
    config_file = get_config_file()
    
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Remove old deprecated keys and resave if needed
                old_keys = ["ram", "version"]
                needs_resave = False
                for key in old_keys:
                    if key in config:
                        del config[key]
                        needs_resave = True
                # Merge with defaults to ensure all keys exist
                merged = DEFAULT_CONFIG.copy()
                merged.update(config)
                # Resave if we cleaned old keys
                if needs_resave:
                    save_config(merged)
                return merged
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading config: {e}, using defaults")
            return DEFAULT_CONFIG.copy()
    else:
        # First run - create default config
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any]) -> bool:
    """Save configuration to JSON file"""
    config_file = get_config_file()
    
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        print(f"Error saving config: {e}")
        return False


def update_config(updates: Dict[str, Any]) -> bool:
    """Update specific config values"""
    config = load_config()
    config.update(updates)
    return save_config(config)


def get_setting(key: str, default=None):
    """Get a single setting value"""
    config = load_config()
    return config.get(key, default)


def set_setting(key: str, value: Any) -> bool:
    """Set a single setting value"""
    return update_config({key: value})


# CLI interface for Tauri backend
if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="Config management CLI")
    parser.add_argument("--get", type=str, help="Get a setting value")
    parser.add_argument("--set", type=str, help="Set a setting (format: key=value)")
    parser.add_argument("--load", action="store_true", help="Load all config as JSON")
    parser.add_argument("--save-json", type=str, help="Save JSON string to config")
    
    args = parser.parse_args()
    
    if args.load:
        config = load_config()
        print(json.dumps(config, ensure_ascii=False))
        sys.exit(0)
    elif args.save_json:
        try:
            config = json.loads(args.save_json)
            # Remove old deprecated keys to prevent merge issues
            old_keys = ["ram", "version"]
            for key in old_keys:
                if key in config:
                    del config[key]
            success = save_config(config)
            sys.exit(0 if success else 1)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON: {e}")
            sys.exit(1)
    elif args.get:
        value = get_setting(args.get)
        print(json.dumps(value, ensure_ascii=False))
        sys.exit(0)
    elif args.set:
        if '=' not in args.set:
            print("Format: key=value")
            sys.exit(1)
        key, value = args.set.split('=', 1)
        # Try to parse as JSON (for numbers, bools, etc.)
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            pass  # Keep as string
        success = set_setting(key, value)
        sys.exit(0 if success else 1)
    else:
        parser.print_help()
        sys.exit(1)
