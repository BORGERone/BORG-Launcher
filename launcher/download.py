"""
Minecraft download module using minecraft-launcher-lib
Downloads vanilla 1.21.1 and NeoForge 21.1.227
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path
from urllib.request import urlopen, urlretrieve
from urllib.error import URLError
import minecraft_launcher_lib as mll

# Configuration
GAME_DIR = Path("E:/Project/BORGLauncher/.minecraft")
NEOFORGE_VERSION = "21.1.227"
MINECRAFT_VERSION = "1.21.1"

# Progress throttling
_last_progress_time = 0
_last_progress_percent = -1
_PROGRESS_UPDATE_INTERVAL = 0.2  # Update every 200ms
_PROGRESS_PERCENT_THRESHOLD = 5  # Or every 5%


def download_vanilla_minecraft(version: str = MINECRAFT_VERSION, progress_callback=None) -> bool:
    """Download vanilla Minecraft version with retry logic"""
    import time
    
    game_dir = str(GAME_DIR)
    max_attempts = 5
    
    for attempt in range(1, max_attempts + 1):
        print(f"\n{'='*50}", flush=True)
        print(f"Minecraft download attempt {attempt}/{max_attempts}", flush=True)
        print(f"{'='*50}", flush=True)
        print(f"Downloading Minecraft {version}...", flush=True)
        
        try:
            # Check if already installed
            installed_versions = mll.utils.get_installed_versions(game_dir)
            if any(v["id"] == version for v in installed_versions):
                print(f"Minecraft {version} already installed", flush=True)
                return True
            
            # Create callback dict for minecraft-launcher-lib
            if progress_callback:
                def _progress_wrapper(*args):
                    # Handle both setProgress(current, total) and setProgress(value)
                    if len(args) >= 2:
                        progress_callback(args[0], args[1])
                    elif len(args) == 1 and isinstance(args[0], (int, float)):
                        progress_callback(args[0], 100)
                
                callback = {
                    "setProgress": _progress_wrapper,
                    "setMax": lambda *args: None,
                    "setStatus": lambda *args: None
                }
            else:
                callback = None
            
            # Download the version
            mll.install.install_minecraft_version(version, game_dir, callback=callback)
            print(f"Minecraft {version} downloaded successfully!", flush=True)
            return True
            
        except Exception as e:
            error_str = str(e)
            is_connection_error = any(err in error_str.lower() for err in [
                "connection", "timeout", "reset", "aborted", "10054", "10053"
            ])
            
            if is_connection_error and attempt < max_attempts:
                # Connection error - will retry, don't show scary error message
                wait_time = attempt * 3  # 3, 6, 9, 12 seconds
                print(f"Network hiccup, retrying in {wait_time}s... (attempt {attempt}/{max_attempts})", flush=True)
                time.sleep(wait_time)
            else:
                # Last attempt or non-connection error - show full error
                if attempt == max_attempts:
                    print(f"\nFailed to download Minecraft after {max_attempts} attempts", flush=True)
                    print(f"Final error: {e}", flush=True)
                    import traceback
                    traceback.print_exc()
                    return False
                else:
                    # Non-connection error on non-last attempt
                    print(f"Error: {e}", flush=True)
                    import traceback
                    traceback.print_exc()
                    return False
    
    return False


def download_neoforge_installer(version: str = NEOFORGE_VERSION) -> Path:
    """Download NeoForge installer jar"""
    print(f"Downloading NeoForge {version} installer...", flush=True)
    
    installer_url = f"https://maven.neoforged.net/releases/net/neoforged/neoforge/{version}/neoforge-{version}-installer.jar"
    installer_path = GAME_DIR / "installers" / f"neoforge-{version}-installer.jar"
    
    # Create installers directory
    installer_path.parent.mkdir(parents=True, exist_ok=True)
    
    if installer_path.exists():
        print(f"NeoForge installer already exists: {installer_path}", flush=True)
        return installer_path
    
    try:
        print(f"Downloading from: {installer_url}", flush=True)
        urlretrieve(installer_url, installer_path)
        print(f"NeoForge installer downloaded to: {installer_path}", flush=True)
        return installer_path
    except URLError as e:
        print(f"Error downloading NeoForge installer: {e}", flush=True)
        return None
    except Exception as e:
        print(f"Unexpected error: {e}", flush=True)
        return None


def create_launcher_profiles(game_dir: Path):
    """Create minimal launcher_profiles.json required by Forge/NeoForge installer"""
    profiles_file = game_dir / "launcher_profiles.json"
    
    if profiles_file.exists():
        return  # Already exists
    
    # Minimal profile that satisfies NeoForge installer
    profiles = {
        "profiles": {
            "(Default)": {
                "name": "(Default)",
                "lastVersionId": MINECRAFT_VERSION,
                "type": "latest-release"
            }
        },
        "settings": {
            "crashAssistance": True,
            "enableAdvanced": False,
            "enableAnalytics": True,
            "enableHistorical": False,
            "enableReleases": True,
            "enableSnapshots": False,
            "keepLauncherOpen": False,
            "profileSorting": "byLastPlayed",
            "showGameLog": False,
            "useNativeLauncher": True
        },
        "version": 3
    }
    
    try:
        with open(profiles_file, 'w', encoding='utf-8') as f:
            json.dump(profiles, f, indent=2)
        print(f"Created launcher_profiles.json", flush=True)
    except Exception as e:
        print(f"Warning: could not create launcher_profiles.json: {e}", flush=True)


def install_neoforge(version: str = NEOFORGE_VERSION) -> bool:
    """Install NeoForge using its installer"""
    print(f"Installing NeoForge {version}...", flush=True)
    
    # First check if already installed
    installed_versions = mll.utils.get_installed_versions(str(GAME_DIR))
    version_id = f"neoforge-{version}"
    if any(v["id"] == version_id for v in installed_versions):
        print(f"NeoForge {version} already installed", flush=True)
        return True
    
    # Create launcher profiles (required by NeoForge installer)
    create_launcher_profiles(GAME_DIR)
    
    # Download installer
    installer_path = download_neoforge_installer(version)
    if not installer_path:
        return False
    
    # Run installer
    game_dir = str(GAME_DIR)
    java_path = find_java()
    
    print(f"Using Java path: {java_path}", flush=True)
    print(f"Java exists: {Path(java_path).exists()}", flush=True)
    
    # Try installation up to 3 times (installer can resume failed downloads)
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            print(f"\n{'='*50}", flush=True)
            print(f"NeoForge installation attempt {attempt}/{max_attempts}", flush=True)
            print(f"{'='*50}", flush=True)
            
            cmd = [
                java_path,
                "-Dsun.net.client.defaultConnectTimeout=60000",  # 60 seconds
                "-Dsun.net.client.defaultReadTimeout=300000",    # 5 minutes
                "-Dhttp.connection.timeout=60000",
                "-Dhttp.socket.timeout=300000",
                "-jar",
                str(installer_path),
                "--installClient",
                game_dir
            ]
            
            print(f"Command: {' '.join(cmd)}", flush=True)
            
            # Set working directory to game dir to avoid log file in src-tauri
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=900,  # 15 minutes timeout per attempt
                cwd=str(GAME_DIR)  # Run in game directory
            )
            
            if result.returncode == 0:
                print(f"NeoForge {version} installed successfully!", flush=True)
                return True
            else:
                print(f"Attempt {attempt} failed with code {result.returncode}", flush=True)
                # Check if it was just a download timeout (installer can resume)
                if "SocketTimeoutException" in result.stdout and attempt < max_attempts:
                    print("Network timeout detected, will retry...", flush=True)
                    continue
                # Print full output on final failure
                if attempt == max_attempts:
                    print(f"STDOUT: {result.stdout}", flush=True)
                    print(f"STDERR: {result.stderr}", flush=True)
                    return False
                    
        except subprocess.TimeoutExpired:
            print(f"Attempt {attempt} timed out", flush=True)
            if attempt < max_attempts:
                print("Will retry...", flush=True)
            continue
        except Exception as e:
            print(f"Error in attempt {attempt}: {e}", flush=True)
            if attempt == max_attempts:
                import traceback
                traceback.print_exc()
                return False
            continue
    
    return False


def find_java(game_dir=None) -> str:
    """Find Java executable"""
    if game_dir is None:
        game_dir = GAME_DIR
    
    print(f"Searching for Java in game_dir: {game_dir}", flush=True)
    
    # Also check runtime folder in game_dir first (Minecraft bundled Java)
    game_path = Path(game_dir)
    runtime_dirs = list(game_path.glob("runtime/*/bin/java.exe"))
    runtime_dirs.extend(game_path.glob("runtime/*/*/bin/java.exe"))
    
    for p in runtime_dirs:
        if p.exists():
            print(f"Found Java in runtime: {p}", flush=True)
            return str(p)
    
    # Try to find Java in common locations
    java_paths = [
        "java",
        "C:/Program Files/Java/jdk-17/bin/java.exe",
        "C:/Program Files/Java/jdk-21/bin/java.exe",
        "C:/Program Files/Java/jdk-*/bin/java.exe",
        "C:/Program Files (x86)/Java/jre1.8.0_361/bin/java.exe",
        "C:/Program Files (x86)/Java/jre*/bin/java.exe",
        "C:/Program Files/Eclipse Adoptium/jdk-17*/bin/java.exe",
        "C:/Program Files/Eclipse Adoptium/jdk-21*/bin/java.exe",
        "C:/Program Files/Microsoft/jdk-17*/bin/java.exe",
        "C:/Program Files/Microsoft/jdk-21*/bin/java.exe",
        "C:/Program Files/Java/*/bin/java.exe",
        "C:/Program Files (x86)/Java/*/bin/java.exe",
    ]
    
    # Try 'where java' command on Windows
    try:
        import subprocess
        result = subprocess.run(["where", "java"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            first_java = result.stdout.strip().split('\n')[0]
            if Path(first_java).exists():
                print(f"Found Java via 'where' command: {first_java}", flush=True)
                return first_java
    except Exception as e:
        print(f"'where java' failed: {e}", flush=True)
    
    for java in java_paths:
        if '*' in java:
            # Handle glob patterns
            import glob
            matches = glob.glob(java)
            if matches:
                java = matches[0]
        
        if Path(java).exists():
            print(f"Found Java at: {java}", flush=True)
            return java
    
    # Fallback to 'java' in PATH
    print(f"Using fallback 'java' in PATH", flush=True)
    return "java"


def download_progress_callback(current, total):
    """Print download progress - receives two integers from setProgress"""
    global _last_progress_time, _last_progress_percent
    
    if total > 0:
        percent = (current / total) * 100
        current_time = time.time()
        
        # Throttle: only update if enough time passed or percent changed significantly
        time_elapsed = current_time - _last_progress_time
        percent_changed = abs(percent - _last_progress_percent)
        
        if time_elapsed >= _PROGRESS_UPDATE_INTERVAL or percent_changed >= _PROGRESS_PERCENT_THRESHOLD:
            print(f"Downloading: {current}/{total} ({percent:.1f}%)", flush=True)
            _last_progress_time = current_time
            _last_progress_percent = percent


def install_all():
    """Install Minecraft 1.21.1 and NeoForge 21.1.227"""
    global _last_progress_time, _last_progress_percent
    
    # Reset throttling state
    _last_progress_time = 0
    _last_progress_percent = -1
    
    print("=" * 50, flush=True)
    print("Installing Minecraft 1.21.1 + NeoForge 21.1.227", flush=True)
    print("=" * 50, flush=True)
    
    # Create game directory
    GAME_DIR.mkdir(parents=True, exist_ok=True)
    
    # Step 1: Download vanilla Minecraft
    print("\n[Step 1/2] Downloading Minecraft 1.21.1...", flush=True)
    if not download_vanilla_minecraft(progress_callback=download_progress_callback):
        print("Failed to download Minecraft", flush=True)
        sys.exit(1)
    print()
    
    # Step 2: Install NeoForge
    print("\n[Step 2/2] Installing NeoForge 21.1.227...", flush=True)
    if not install_neoforge():
        print("Failed to install NeoForge", flush=True)
        sys.exit(1)
    
    print("\n" + "=" * 50, flush=True)
    print("Installation complete!", flush=True)
    print("=" * 50, flush=True)
    return True


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Download Minecraft and NeoForge")
    parser.add_argument("--vanilla", action="store_true", help="Download only vanilla")
    parser.add_argument("--neoforge", action="store_true", help="Download only NeoForge")
    parser.add_argument("--install", action="store_true", help="Install both Minecraft and NeoForge")
    parser.add_argument("--version", default=MINECRAFT_VERSION, help="Minecraft version")
    parser.add_argument("--neoforge-version", default=NEOFORGE_VERSION, help="NeoForge version")
    parser.add_argument("--game-dir", type=str, default=None, help="Game directory path")
    
    args = parser.parse_args()
    
    # Update GAME_DIR if provided
    if args.game_dir:
        global GAME_DIR
        GAME_DIR = Path(args.game_dir)
    
    if args.vanilla:
        success = download_vanilla_minecraft(args.version)
    elif args.neoforge:
        success = install_neoforge(args.neoforge_version)
    elif args.install:
        success = install_all()
    else:
        success = install_all()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
