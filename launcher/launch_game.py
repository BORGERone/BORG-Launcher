#!/usr/bin/env python3
"""
Headless game launcher - launches Minecraft without GUI
Called from Tauri backend
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from launcher.main import launch_minecraft, load_config


def main():
    parser = argparse.ArgumentParser(description="Launch Minecraft (headless)")
    parser.add_argument("--nickname", required=True, help="Player nickname")
    parser.add_argument("--ram", type=int, default=4096, help="RAM in MB")
    parser.add_argument("--version", default="neoforge-21.1.227", help="Game version")
    parser.add_argument("--game-dir", type=str, default=None, help="Game directory")
    
    args = parser.parse_args()
    
    # Load config and update if game-dir provided
    config = load_config()
    if args.game_dir:
        config["game_dir"] = args.game_dir
    
    # Validate game directory exists
    game_path = Path(config["game_dir"])
    if not game_path.exists():
        print(f"Error: Game directory does not exist: {game_path}")
        sys.exit(1)
    
    # Check for Minecraft installation markers
    versions_dir = game_path / "versions"
    if not versions_dir.exists():
        print(f"Error: No Minecraft installation found in: {game_path}")
        print(f"Missing versions directory. Run Install first.")
        sys.exit(1)
    
    # Launch the game
    try:
        result = launch_minecraft(
            version_id=args.version,
            username=args.nickname,
            ram_mb=args.ram,  # Already in MB
            game_dir=Path(config["game_dir"])
        )
        
        if result:
            print(f"Minecraft launched successfully!")
            sys.exit(0)
        else:
            print("Failed to launch Minecraft")
            sys.exit(1)
    except Exception as e:
        print(f"Error launching game: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
