"""
GD Storage - Encode files into Geometry Dash levels

Usage:
  Encode: python encoder.py <filepath> [--method N]
  Decode: python encoder.py --decode <levelname> [--method N]
  Fetch:  python encoder.py --fetch <level_id> [--method N]
  Upload: python encoder.py --upload <filepath> [--method N]

Methods:
  1 - X/Y Coordinates (unoptimized)
  2 - Raw Groups (1GB levels, crashes on close)
  3 - Base 10000 (slow)
  4 - Base64 Groups (stripped by GD)
  5 - Property 31 (doesn't work)
  6 - Optimized Base 9999 (default, best)
"""
from pathlib import Path
from methods import METHODS, DEFAULT_METHOD

if __name__ == "__main__":
    import sys
    import os
    from CCManager import newManager

    # Parse arguments
    method_num = DEFAULT_METHOD
    args = sys.argv[1:]

    # Extract --method argument
    if "--method" in args:
        idx = args.index("--method")
        if idx + 1 < len(args):
            method_num = int(args[idx + 1])
            args = args[:idx] + args[idx+2:]

    if len(args) < 1:
        print("Usage:")
        print("  Encode: python encoder.py <filepath> [--method N]")
        print("  Decode: python encoder.py --decode <levelname> [--method N]")
        print("  Fetch:  python encoder.py --fetch <level_id> [--method N]")
        print("  Upload: python encoder.py --upload <filepath> [--method N]")
        print()
        print("Methods:")
        for num, (_, _, desc) in METHODS.items():
            default = " (default)" if num == DEFAULT_METHOD else ""
            print(f"  {num} - {desc}{default}")
        sys.exit(1)

    if method_num not in METHODS:
        print(f"Invalid method {method_num}. Valid methods: {list(METHODS.keys())}")
        sys.exit(1)

    encode_func, decode_func, method_desc = METHODS[method_num]
    print(f"Using method {method_num}: {method_desc}")

    if args[0] == "--fetch":
        # Download and decode a level from GD servers
        if len(args) < 2:
            print("Usage: python encoder.py --fetch <level_id> [--method N]")
            sys.exit(1)

        from gd_api import download_level

        level_id = int(args[1])
        print(f"Fetching level {level_id} from GD servers...")

        try:
            level_data = download_level(level_id)
        except Exception as e:
            print(f"Failed to fetch level: {e}")
            sys.exit(1)

        level_name = level_data.get("name", "Unknown")
        description = level_data.get("description", "")
        level_str = level_data.get("level_string", "")

        print(f"Level: {level_name}")
        print(f"Description: {description}")
        print(f"Level string: {len(level_str):,} chars")

        print("Decoding...")
        try:
            filename, data = decode_func(level_str)
            # Sanitize filename - prevent path traversal
            safe_filename = Path(filename).name
            if not safe_filename:
                safe_filename = "decoded_file"
            downloads = Path(os.path.expanduser("~")) / "Downloads" / safe_filename
            downloads.write_bytes(data)
            print(f"Saved to {downloads} ({len(data):,} bytes)")
        except Exception as e:
            print(f"Failed to decode (might not be an encoded file): {e}")
            sys.exit(1)

    elif args[0] == "--upload":
        # Encode and upload a file to GD servers
        if len(args) < 2:
            print("Usage: python encoder.py --upload <filepath> [--method N]")
            sys.exit(1)

        import dashlib
        import base64
        import gzip
        from gd_api import get_account_id
        import getpass

        filepath = Path(args[1])
        if not filepath.exists():
            print(f"File not found: {filepath}")
            sys.exit(1)

        print(f"Encoding {filepath} ({filepath.stat().st_size:,} bytes)...")
        level_str = encode_func(filepath)
        print(f"Encoded level string: {len(level_str):,} chars")

        # Decompress to get raw level for object count
        if level_str.startswith('H4sI'):
            compressed = base64.urlsafe_b64decode(level_str + '==')
            raw_level = gzip.decompress(compressed).decode('utf-8')
        else:
            raw_level = level_str

        obj_count = raw_level.count(';')
        print(f"Object count: {obj_count}")

        level_name = filepath.stem[:20]  # GD has name length limits
        description = f"Encoded: {filepath.name}"
        # Base64 encode description for dashlib
        desc_encoded = base64.urlsafe_b64encode(description.encode()).decode()

        # Create a level object for dashlib
        class UploadLevel:
            def __init__(self):
                self.levelString = level_str
                self.levelName = level_name
                self.description = desc_encoded
                self.password = 1  # No copy
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

        # Try to get credentials from save file first
        import re
        manager_gm = newManager()
        ccgm = manager_gm.ccgm.decode('utf-8', errors='ignore')

        saved_user = re.search(r'<k>GJA_001</k><s>([^<]+)</s>', ccgm)
        saved_id = re.search(r'<k>GJA_003</k><i>(\d+)</i>', ccgm)
        saved_gjp2 = re.search(r'<k>GJA_005</k><s>([^<]+)</s>', ccgm)

        if saved_user and saved_id and saved_gjp2:
            print(f"Found saved GD credentials for: {saved_user.group(1)}")
            use_saved = input("Use saved credentials? (Y/n): ").strip().lower()
            if use_saved != 'n':
                username = saved_user.group(1)
                account_id = int(saved_id.group(1))
                gjp2 = saved_gjp2.group(1)
                print(f"Using: {username} (ID: {account_id})")
            else:
                print()
                print("Enter your GD account credentials:")
                username = input("Username: ")
                password = getpass.getpass("Password: ")
                print("Logging in...")
                try:
                    account_id, gjp2 = get_account_id(username, password)
                    print(f"Logged in as {username} (Account ID: {account_id})")
                except Exception as e:
                    print(f"Login failed: {e}")
                    sys.exit(1)
        else:
            print("No saved credentials found.")
            print()
            print("Enter your GD account credentials:")
            username = input("Username: ")
            password = getpass.getpass("Password: ")
            print("Logging in...")
            try:
                account_id, gjp2 = get_account_id(username, password)
                print(f"Logged in as {username} (Account ID: {account_id})")
            except Exception as e:
                print(f"Login failed: {e}")
                sys.exit(1)

        print(f"Uploading '{level_name}' to GD servers using dashlib...")
        try:
            result = dashlib.uploadLevel(
                level=level,
                username=username,
                accountID=account_id,
                gjp2=gjp2,
            )
            if result == "-1" or result.startswith("-"):
                raise ValueError(f"Upload failed with error: {result}")
            new_level_id = int(result)
            print(f"Uploaded! Level ID: {new_level_id}")
            print(f"Anyone can fetch with: python encoder.py --fetch {new_level_id}")
        except Exception as e:
            print(f"Upload failed: {e}")
            sys.exit(1)

    elif args[0] == "--decode":
        # Decode from local GD save
        if len(args) < 2:
            print("Usage: python encoder.py --decode <levelname> [--method N]")
            sys.exit(1)

        level_name = args[1]
        print(f"Extracting level '{level_name}'...")

        manager = newManager()
        ccll = manager.ccll.decode('utf-8', errors='ignore')

        start = ccll.find(f'<s>{level_name}</s>')
        if start == -1:
            print(f"Level '{level_name}' not found!")
            sys.exit(1)

        k4_start = ccll.find('<k>k4</k><s>', start) + len('<k>k4</k><s>')
        k4_end = ccll.find('</s>', k4_start)
        level_str = ccll[k4_start:k4_end]

        print(f"Level string: {len(level_str):,} chars")
        print("Decoding...")

        filename, data = decode_func(level_str)
        # Sanitize filename - prevent path traversal
        safe_filename = Path(filename).name
        if not safe_filename:
            safe_filename = "decoded_file"
        downloads = Path(os.path.expanduser("~")) / "Downloads" / safe_filename
        downloads.write_bytes(data)
        print(f"Saved to {downloads} ({len(data):,} bytes)")

    else:
        # Encode and save to local GD save
        filepath = Path(args[0])
        if not filepath.exists():
            print(f"File not found: {filepath}")
            sys.exit(1)

        print(f"Encoding {filepath} ({filepath.stat().st_size:,} bytes)...")

        level_str = encode_func(filepath)
        print(f"Level string: {len(level_str):,} chars")

        manager = newManager()
        manager.injectLevel(level_str, filepath.stem, f"Encoded: {filepath.name}")
        manager.save(ccll=True, ccgm=False)
        print(f"Injected as '{filepath.stem}'")
