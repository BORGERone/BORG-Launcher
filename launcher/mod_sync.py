"""
Mod synchronization module - TCP client for syncing mods with server
Ported from MainWindow.xaml.cs C# code
"""

import os
import sys
import socket
import json
from pathlib import Path
from typing import List, Tuple, Optional

# Server configuration (from MainWindow.xaml.cs)
SERVER_HOST = "91.210.149.24"
SERVER_PORT = 25564
DEFAULT_MODS_DIR = Path("E:/Project/BORGLauncher/.minecraft/mods")


class ModSyncClient:
    """TCP client for mod synchronization"""
    
    def __init__(self, host: str = SERVER_HOST, port: int = SERVER_PORT, mods_dir=None):
        self.host = host
        self.port = port
        self.socket = None
        self.mods_dir = Path(mods_dir) if mods_dir else DEFAULT_MODS_DIR
    
    def connect(self, timeout: float = 5.0) -> bool:
        """Connect to server with timeout"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(timeout)
            self.socket.connect((self.host, self.port))
            return True
        except socket.timeout:
            print(f"Connection timeout to {self.host}:{self.port}")
            return False
        except socket.error as e:
            print(f"Connection error: {e}")
            return False
    
    def disconnect(self):
        """Close connection"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
    
    def _send_line(self, data: str):
        """Send line ending with newline"""
        self.socket.sendall((data + "\n").encode('utf-8'))
    
    def _read_line(self) -> str:
        """Read line until newline"""
        buffer = b""
        while True:
            byte = self.socket.recv(1)
            if not byte:
                return ""
            if byte == b"\n":
                break
            buffer += byte
        return buffer.decode('utf-8').strip()
    
    def _read_exact(self, size: int) -> bytes:
        """Read exact number of bytes"""
        data = b""
        while len(data) < size:
            chunk = self.socket.recv(size - len(data))
            if not chunk:
                raise ConnectionError("Server disconnected unexpectedly")
            data += chunk
        return data
    
    def check_server_status(self) -> bool:
        """Check if server is online"""
        try:
            if self.connect(timeout=5.0):
                self.disconnect()
                return True
            return False
        except:
            return False
    
    def get_local_mods(self) -> List[str]:
        """Get list of local mod filenames"""
        self.mods_dir.mkdir(parents=True, exist_ok=True)
        mods = []
        for file in self.mods_dir.iterdir():
            if file.is_file():
                mods.append(file.name)
        return mods
    
    def sync_mods(self, auto_download: bool = True, progress_callback=None) -> Tuple[bool, str]:
        """
        Synchronize mods with server
        
        Args:
            auto_download: If True, download missing mods without asking
            progress_callback: Function(filename, current, total) to report progress
            
        Returns:
            (success: bool, message: str)
        """
        if not self.connect():
            return False, "Failed to connect to server"
        
        try:
            # 1. Send list of local mods
            local_mods = self.get_local_mods()
            mods_list = ",".join(local_mods) if local_mods else ""
            
            print(f"Sending local mods list: {mods_list}")
            self._send_line(mods_list)
            
            # 2. Read server response
            response = self._read_line()
            print(f"Server response: {response}")
            
            if response == "All mods are up to date.":
                return True, "All mods are up to date"
            
            if not response.startswith("Missing mods:"):
                return False, f"Unknown server response: {response}"
            
            # Parse missing mods
            missing_mods_str = response.replace("Missing mods:", "").strip()
            missing_mods = [m.strip() for m in missing_mods_str.split(",") if m.strip()]
            
            if not missing_mods:
                return True, "All mods are up to date"
            
            print(f"Missing mods: {missing_mods}")
            
            # Ask for download (or auto-download if enabled)
            if not auto_download:
                # In GUI mode, this should show a dialog
                # For now, we auto-download
                pass
            
            # 3. Send YES to start download
            self._send_line("YES")
            
            # 4. Receive and save files
            total_files = len(missing_mods)
            downloaded_count = 0
            
            while True:
                # Read file size
                size_str = self._read_line()
                
                if not size_str or size_str == "END_OF_FILES":
                    print("Download complete marker received")
                    break
                
                try:
                    file_size = int(size_str)
                except ValueError:
                    return False, f"Invalid file size: {size_str}"
                
                # Read filename
                mod_name = self._read_line()
                if not mod_name:
                    return False, "Empty filename received"
                
                downloaded_count += 1
                print(f"Receiving: {mod_name} ({file_size} bytes) [{downloaded_count}/{total_files}]")
                
                if progress_callback:
                    progress_callback(mod_name, downloaded_count, total_files)
                
                # Read file data
                try:
                    file_data = self._read_exact(file_size)
                except ConnectionError as e:
                    return False, str(e)
                
                # Save file
                file_path = self.mods_dir / mod_name
                try:
                    with open(file_path, 'wb') as f:
                        f.write(file_data)
                    print(f"Saved: {file_path}")
                except Exception as e:
                    return False, f"Error saving file {mod_name}: {e}"
            
            return True, f"Downloaded {downloaded_count} mod(s) successfully"
            
        except socket.error as e:
            return False, f"Socket error: {e}"
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"Error: {e}"
        finally:
            self.disconnect()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


def check_server_online() -> bool:
    """Quick check if mod server is online"""
    client = ModSyncClient()
    return client.check_server_status()


def sync_mods_auto(auto_download: bool = True, progress_callback=None, mods_dir=None) -> Tuple[bool, str]:
    """
    Main function to sync mods - downloads missing mods automatically
    
    Args:
        auto_download: If True, download missing mods without asking
        progress_callback: Function to report progress
        mods_dir: Directory for mods (default: DEFAULT_MODS_DIR)
    
    Returns:
        (success: bool, message: str)
    """
    print("=" * 50)
    print("Mod Synchronization")
    print("=" * 50)
    
    # Use provided mods_dir or default
    if mods_dir is None:
        mods_dir = DEFAULT_MODS_DIR
    else:
        mods_dir = Path(mods_dir)
    
    # Ensure mods directory exists
    mods_dir.mkdir(parents=True, exist_ok=True)
    
    # Check server status
    print(f"Checking server {SERVER_HOST}:{SERVER_PORT}...")
    if not check_server_online():
        return False, f"Server {SERVER_HOST}:{SERVER_PORT} is offline"
    
    print("Server is online, starting sync...")
    
    # Sync mods
    with ModSyncClient(mods_dir=mods_dir) as client:
        success, message = client.sync_mods(auto_download=auto_download, progress_callback=progress_callback)
    
    print(f"\nSync result: {message}")
    return success, message


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Sync mods with server")
    parser.add_argument("--check", action="store_true", help="Check server status only")
    parser.add_argument("--list", action="store_true", help="List local mods")
    parser.add_argument("--sync", action="store_true", help="Sync mods with server")
    parser.add_argument("--game-dir", type=str, default=None, help="Game directory path")
    
    args = parser.parse_args()
    
    if args.check:
        if check_server_online():
            print(f"Server {SERVER_HOST}:{SERVER_PORT} is ONLINE")
            sys.exit(0)
        else:
            print(f"Server {SERVER_HOST}:{SERVER_PORT} is OFFLINE")
            sys.exit(1)
    elif args.sync:
        # Determine mods directory
        if args.game_dir:
            mods_dir = Path(args.game_dir) / "mods"
        else:
            mods_dir = DEFAULT_MODS_DIR
        
        success, message = sync_mods_auto(mods_dir=mods_dir)
        print(message)
        sys.exit(0 if success else 1)
    elif args.list:
        # List local mods
        if args.game_dir:
            mods_dir = Path(args.game_dir) / "mods"
        else:
            mods_dir = DEFAULT_MODS_DIR
        
        local_mods = scan_local_mods(mods_dir)
        print(f"Local mods in {mods_dir}:")
        for mod_file in local_mods:
            print(f"  - {mod_file}")
        sys.exit(0)
    else:
        # Default: sync
        if args.game_dir:
            mods_dir = Path(args.game_dir) / "mods"
        else:
            mods_dir = DEFAULT_MODS_DIR
        
        success, message = sync_mods_auto(mods_dir=mods_dir)
        print(message)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
