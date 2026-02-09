import argparse
import sys
import os
import base64
import gzip
import getpass
import re
import json
import platform
from pathlib import Path

from methods import METHODS


# Config file location
CONFIG_DIR = Path.home() / ".config" / "gd-storage"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config() -> dict:
    """Load config from file or return defaults."""
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_config(config: dict):
    """Save config to file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def get_default_gd_path() -> str | None:
    """Get default GD save path for current platform."""
    system = platform.system()
    if system == "Windows":
        local_app_data = os.getenv("LOCALAPPDATA")
        if local_app_data:
            return os.path.join(local_app_data, "GeometryDash")
    elif system == "Darwin":  # macOS
        return os.path.expanduser("~/Library/Application Support/GeometryDash")
    return None


def get_manager(config: dict):
    """Get GD save manager based on config."""
    from save_manager import new_manager

    gd_path = config.get("gd_path")
    gd_format = config.get("format", "auto")

    # Auto-detect path if not configured
    if not gd_path:
        gd_path = get_default_gd_path()
        if not gd_path:
            raise ValueError("GD path not configured. Run: gd-storage --config")

    # Check path exists
    if not os.path.exists(gd_path):
        raise ValueError(f"GD save folder not found: {gd_path}\nRun: gd-storage --config")

    return new_manager(path=gd_path, format=gd_format)


def cmd_config():
    """Configure GD storage settings."""
    config = load_config()

    print("GD Storage Configuration")
    print("=" * 40)

    # Show current settings
    current_path = config.get("gd_path", get_default_gd_path() or "Not set")
    current_format = config.get("format", "auto")
    print(f"Current path: {current_path}")
    print(f"Current format: {current_format}")
    print()

    # Get new path
    print("Enter GD save folder path (or press Enter to keep current):")
    print("  Windows: %LOCALAPPDATA%\\GeometryDash")
    print("  macOS: ~/Library/Application Support/GeometryDash")
    print("  Linux/Proton: ~/.steam/steam/steamapps/compatdata/.../GeometryDash")
    new_path = input("> ").strip()

    if new_path:
        new_path = os.path.expanduser(os.path.expandvars(new_path))
        if not os.path.exists(new_path):
            print(f"Warning: Path does not exist: {new_path}")
            confirm = input("Save anyway? (y/N): ").strip().lower()
            if confirm != 'y':
                return 1
        config["gd_path"] = new_path

    # Get format
    print()
    print("Save format:")
    print("  1. auto (detect from platform)")
    print("  2. windows (XOR encryption - Windows/Linux/Proton)")
    print("  3. mac (AES encryption - macOS)")
    choice = input("Choice [1]: ").strip() or "1"

    if choice == "2":
        config["format"] = "windows"
    elif choice == "3":
        config["format"] = "mac"
    else:
        config["format"] = "auto"

    save_config(config)
    print()
    print(f"Config saved to {CONFIG_FILE}")
    return 0


def save_decoded_file(filename: str, data: bytes) -> Path | None:
    """Save decoded file to Downloads, checking for overwrites."""
    # Sanitize filename - prevent path traversal
    safe_filename = Path(filename).name
    if not safe_filename:
        safe_filename = "decoded_file"

    downloads = Path(os.path.expanduser("~")) / "Downloads" / safe_filename

    if downloads.exists():
        print(f"File already exists: {downloads}")
        choice = input("Overwrite? (y/N): ").strip().lower()
        if choice != 'y':
            # Try adding a number suffix
            stem = downloads.stem
            suffix = downloads.suffix
            for i in range(1, 100):
                alt = downloads.parent / f"{stem}_{i}{suffix}"
                if not alt.exists():
                    downloads = alt
                    break
            else:
                print("Could not find available filename")
                return None

    downloads.write_bytes(data)
    return downloads


def make_description(filename: str, file_size: int, max_len: int = 180) -> str:
    """Build level description, truncating filename if needed to fit limit."""
    prefix = "github.com/c4k3ss/GD-Storage | "
    suffix = f" ({file_size:,} bytes)"

    # Calculate max filename length
    max_name_len = max_len - len(prefix) - len(suffix)

    if len(filename) > max_name_len:
        # Truncate filename, keep extension visible
        name_part = filename[:max_name_len - 3] + "..."
    else:
        name_part = filename

    return f"{prefix}{name_part}{suffix}"


def show_help():
    print("GD Storage - Encode files into Geometry Dash levels")
    print()
    print("Usage:")
    print("  gd-storage --upload <filepath>    Encode and upload to GD servers")
    print("  gd-storage --fetch <level_id>     Download and decode from GD servers")
    print("  gd-storage --encode <filepath>    Encode and inject into local GD save")
    print("  gd-storage --decode <levelname>   Decode from local GD save")
    print("  gd-storage --config               Configure GD save path")


def cmd_upload(filepath: Path, encode_func):
    """Encode and upload a file to GD servers."""
    import dashlib

    if not filepath.exists():
        print(f"File not found: {filepath}")
        return 1

    print(f"Encoding {filepath.name} ({filepath.stat().st_size:,} bytes)...")
    level_str = encode_func(filepath)

    # Decompress to get raw level for object count
    if level_str.startswith('H4sI'):
        compressed = base64.urlsafe_b64decode(level_str + '==')
        raw_level = gzip.decompress(compressed).decode('utf-8')
    else:
        raw_level = level_str

    obj_count = raw_level.count(';')
    level_name = filepath.stem[:20]
    description = make_description(filepath.name, filepath.stat().st_size)
    desc_encoded = base64.urlsafe_b64encode(description.encode()).decode()

    class UploadLevel:
        def __init__(self):
            self.levelString = level_str
            self.levelName = level_name
            self.description = desc_encoded
            self.password = 1
            self.copiedId = 0
            self.version = 1
            self.officialSong = 0
            self.customSongID = 0
            self.coins = 0
            self.lowDetailMode = False
            self.objects = obj_count
            self.isAuto = False
            self.twoPlayer = False
            self.starsRequested = 0
            self.editorTime = 0
            self.editorTimeCopies = 0
            self.length = dashlib.LENGTH_TINY

    level = UploadLevel()

    # Get credentials
    username, account_id, gjp2 = get_credentials()
    if not username:
        return 1

    print(f"Uploading '{level_name}'...")
    try:
        result = dashlib.uploadLevel(
            level=level,
            username=username,
            accountID=account_id,
            gjp2=gjp2,
        )
        if result == "-1" or result.startswith("-"):
            raise ValueError(f"Server returned: {result}")
        new_level_id = int(result)
        print(f"Uploaded! Level ID: {new_level_id}")
        print(f"Fetch with: gd-storage --fetch {new_level_id}")
        return 0
    except Exception as e:
        print(f"Upload failed: {e}")
        return 1


def cmd_fetch(level_id: int, decode_func):
    """Download and decode a level from GD servers."""
    from gd_api import download_level

    print(f"Fetching level {level_id}...")
    try:
        level_data = download_level(level_id)
    except Exception as e:
        print(f"Failed to fetch: {e}")
        return 1

    level_name = level_data.get("name", "Unknown")
    description = level_data.get("description", "")
    level_str = level_data.get("level_string", "")

    print(f"Level: {level_name}")
    if description:
        print(f"Description: {description}")

    try:
        filename, data = decode_func(level_str)
        saved_path = save_decoded_file(filename, data)
        if saved_path:
            print(f"Saved to {saved_path} ({len(data):,} bytes)")
            return 0
        return 1
    except Exception as e:
        print(f"Failed to decode: {e}")
        return 1


def cmd_encode(filepath: Path, encode_func):
    """Encode and inject into local GD save."""
    if not filepath.exists():
        print(f"File not found: {filepath}")
        return 1

    print(f"Encoding {filepath.name} ({filepath.stat().st_size:,} bytes)...")
    level_str = encode_func(filepath)

    config = load_config()
    try:
        manager = get_manager(config)
    except ValueError as e:
        print(f"Error: {e}")
        return 1

    description = make_description(filepath.name, filepath.stat().st_size)
    manager.injectLevel(level_str, filepath.stem, description)
    manager.save(ccll=True, ccgm=False)
    print(f"Injected as '{filepath.stem}'")
    return 0


def cmd_decode(level_name: str, decode_func):
    """Decode from local GD save."""
    print(f"Extracting '{level_name}'...")

    config = load_config()
    try:
        manager = get_manager(config)
    except ValueError as e:
        print(f"Error: {e}")
        return 1

    ccll = manager.ccll.decode('utf-8', errors='ignore')

    start = ccll.find(f'<s>{level_name}</s>')
    if start == -1:
        print(f"Level '{level_name}' not found!")
        return 1

    k4_start = ccll.find('<k>k4</k><s>', start) + len('<k>k4</k><s>')
    k4_end = ccll.find('</s>', k4_start)
    level_str = ccll[k4_start:k4_end]

    try:
        filename, data = decode_func(level_str)
        saved_path = save_decoded_file(filename, data)
        if saved_path:
            print(f"Saved to {saved_path} ({len(data):,} bytes)")
            return 0
        return 1
    except Exception as e:
        print(f"Failed to decode: {e}")
        return 1


def get_credentials():
    """Get GD credentials from save file or prompt user."""
    from gd_api import get_account_id

    config = load_config()
    try:
        manager = get_manager(config)
        ccgm = manager.ccgm.decode('utf-8', errors='ignore')

        saved_user = re.search(r'<k>GJA_001</k><s>([^<]+)</s>', ccgm)
        saved_id = re.search(r'<k>GJA_003</k><i>(\d+)</i>', ccgm)
        saved_gjp2 = re.search(r'<k>GJA_005</k><s>([^<]+)</s>', ccgm)

        if saved_user and saved_id and saved_gjp2:
            print(f"Using saved credentials: {saved_user.group(1)}")
            return saved_user.group(1), int(saved_id.group(1)), saved_gjp2.group(1)
    except (ValueError, FileNotFoundError, OSError):
        pass  # No local save, prompt for credentials

    print("Enter GD credentials:")
    username = input("Username: ")
    password = getpass.getpass("Password: ")

    try:
        account_id, gjp2 = get_account_id(username, password)
        print(f"Logged in as {username}")
        return username, account_id, gjp2
    except Exception as e:
        print(f"Login failed: {e}")
        return None, None, None


def main():
    parser = argparse.ArgumentParser(
        description="GD Storage - Encode files into Geometry Dash levels",
        add_help=False
    )
    parser.add_argument('--upload', metavar='FILE', help='Encode and upload to GD servers')
    parser.add_argument('--fetch', metavar='ID', type=int, help='Download and decode from GD servers')
    parser.add_argument('--encode', metavar='FILE', help='Encode and inject into local GD save')
    parser.add_argument('--decode', metavar='NAME', help='Decode from local GD save')
    parser.add_argument('--config', action='store_true', help='Configure GD save path')
    parser.add_argument('--help', '-h', action='store_true', help='Show help')

    args = parser.parse_args()

    # Handle config
    if args.config:
        return cmd_config()

    # Show help if no args or --help
    if args.help or (not args.upload and not args.fetch and not args.encode and not args.decode):
        show_help()
        return 0

    encode_func, decode_func, _ = METHODS[6]

    # Run command
    if args.upload:
        return cmd_upload(Path(args.upload), encode_func)
    elif args.fetch:
        return cmd_fetch(args.fetch, decode_func)
    elif args.encode:
        return cmd_encode(Path(args.encode), encode_func)
    elif args.decode:
        return cmd_decode(args.decode, decode_func)

    return 0


if __name__ == "__main__":
    sys.exit(main())
