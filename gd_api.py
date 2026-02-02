"""
Geometry Dash Server API

Raw HTTP implementation for downloading and uploading levels.
"""
import urllib.request
import urllib.parse
import base64
import hashlib
import zlib

GD_URL = "https://www.boomlings.com/database"
SECRET = "Wmfd2893gb7"  # Public secret used by GD


def download_level(level_id: int) -> dict:
    """
    Download a level from GD servers by ID.
    Returns dict with 'level_string', 'name', 'description', etc.
    """
    data = urllib.parse.urlencode({
        "levelID": level_id,
        "secret": SECRET,
        "gameVersion": 22,
        "binaryVersion": 42,
        "gdw": 0,
        "inc": 1,
        "extras": 0,
    }).encode()

    req = urllib.request.Request(f"{GD_URL}/downloadGJLevel22.php", data=data)
    req.add_header("User-Agent", "")

    with urllib.request.urlopen(req, timeout=30) as response:
        result = response.read().decode('utf-8', errors='ignore')


    if result == "-1":
        raise ValueError(f"Level {level_id} not found")

    # Parse the response (key:value:key:value format)
    parts = result.split("#")[0]  # Remove hash/creator info
    fields = parts.split(":")
    level_data = {}
    for i in range(0, len(fields) - 1, 2):
        level_data[fields[i]] = fields[i + 1]

    # Decode the level string (base64 + gzip)
    level_string_encoded = level_data.get("4", "")
    if level_string_encoded:
        try:
            # URL-safe base64 decode
            decoded = base64.urlsafe_b64decode(level_string_encoded + "==")
            # Gzip decompress
            level_string = zlib.decompress(decoded, 15 + 32).decode('utf-8', errors='ignore')
        except (ValueError, zlib.error):
            # Some levels might not be compressed
            level_string = level_string_encoded
        level_data["level_string"] = level_string

    # Decode description (base64)
    desc_encoded = level_data.get("3", "")
    if desc_encoded:
        try:
            level_data["description"] = base64.urlsafe_b64decode(desc_encoded + "==").decode('utf-8', errors='ignore')
        except (ValueError, UnicodeDecodeError):
            level_data["description"] = desc_encoded

    # Key mappings for convenience
    level_data["name"] = level_data.get("2", "Unknown")
    level_data["id"] = level_data.get("1", level_id)

    return level_data


def gjp_encode(password: str) -> str:
    """
    Encode password for GD API (old GJP format).
    XOR with key then base64.
    """
    key = "37526"
    xored = ''.join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(password))
    return base64.urlsafe_b64encode(xored.encode('latin-1')).decode()


def gjp2_encode(password: str) -> str:
    """
    Encode password for GD API (GJP2 format).
    SHA1 hash + salt.
    """
    salted = password + "mI29fmAnxgTs"
    hashed = hashlib.sha1(salted.encode()).hexdigest()
    return hashed


def upload_level(
    username: str,
    gjp2: str,
    account_id: int,
    level_name: str,
    level_string: str,
    description: str = "",
    unlisted: bool = True,
) -> int:
    """
    Upload a level to GD servers.
    Returns the new level ID.

    Note: This function is kept for reference but dashlib.uploadLevel is preferred.
    """

    # Decompress to get raw level string for obj count
    if level_string.startswith('H4sI'):
        compressed_bytes = base64.urlsafe_b64decode(level_string + '==')
        raw_level = zlib.decompress(compressed_bytes, 15 + 32).decode('utf-8')
    else:
        raw_level = level_string

    level_encoded = level_string
    obj_count = raw_level.count(';')

    # Encode description
    desc_encoded = base64.urlsafe_b64encode(description.encode()).decode()

    # Level length based on object count (0=Tiny, 1=Short, 2=Medium, 3=Long, 4=XL)
    if obj_count > 10000:
        level_length = 4  # XL
    elif obj_count > 5000:
        level_length = 3  # Long
    elif obj_count > 1000:
        level_length = 2  # Medium
    elif obj_count > 200:
        level_length = 1  # Short
    else:
        level_length = 0  # Tiny

    # Level upload data
    data = urllib.parse.urlencode({
        "accountID": account_id,
        "gjp2": gjp2,
        "userName": username,
        "levelName": level_name,
        "levelDesc": desc_encoded,
        "levelVersion": 1,
        "levelLength": level_length,
        "audioTrack": 0,
        "auto": 0,
        "password": 1,  # No copy
        "original": 0,
        "twoPlayer": 0,
        "songID": 0,
        "objects": obj_count,
        "coins": 0,
        "requestedStars": 0,
        "unlisted": 1 if unlisted else 0,
        "wt": 0,
        "wt2": 0,
        "ldm": 0,
        "levelString": level_encoded,
        "seed": "abc123",
        "seed2": generate_seed2(level_encoded),
        "secret": SECRET,
        "gameVersion": 22,
        "binaryVersion": 44,
        "gdw": 0,
    }).encode()

    req = urllib.request.Request(f"{GD_URL}/uploadGJLevel21.php", data=data)
    req.add_header("User-Agent", "")

    with urllib.request.urlopen(req, timeout=60) as response:
        result = response.read().decode()

    if result == "-1":
        raise ValueError("Upload failed - invalid credentials or verification")
    elif result.startswith("-"):
        raise ValueError(f"Upload failed with error code: {result}")

    return int(result)


def xor_cipher(inp: str, key: str) -> str:
    """XOR cipher with cyclic key."""
    result = ""
    for i, char in enumerate(inp):
        result += chr(ord(char) ^ ord(key[i % len(key)]))
    return result


def generate_upload_seed(data: str, chars: int = 50) -> str:
    """Generate upload seed from level string - take every Nth char to get 50 chars."""
    if len(data) < chars:
        return data
    step = len(data) // chars
    return data[::step][:chars]


def generate_seed2(level_string: str) -> str:
    """Generate seed2 for level upload verification (CHK format)."""
    # Get 50 evenly-spaced characters from level string
    seed_chars = generate_upload_seed(level_string)
    # Add salt and hash
    salt = "xI25fpAapCQg"
    to_hash = seed_chars + salt
    hashed = hashlib.sha1(to_hash.encode()).hexdigest()
    # XOR with key and base64 encode
    xored = xor_cipher(hashed, "41274")
    return base64.urlsafe_b64encode(xored.encode()).decode()


def get_account_id(username: str, password: str) -> tuple[int, str]:
    """
    Login and get account ID.
    Returns (account_id, gjp2) for use in subsequent requests.
    """
    # Login uses a different secret than other endpoints
    login_secret = "Wmfv3899gc9"

    data = urllib.parse.urlencode({
        "userName": username,
        "password": password,  # Raw password for login
        "secret": login_secret,
        "udid": "S15232137420643451451521515121125115195140311",
        "gameVersion": 22,
        "binaryVersion": 42,
    }).encode()

    req = urllib.request.Request(f"{GD_URL}/accounts/loginGJAccount.php", data=data)
    req.add_header("User-Agent", "")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    with urllib.request.urlopen(req, timeout=30) as response:
        result = response.read().decode()

    if result == "-1" or result.startswith("-"):
        raise ValueError(f"Login failed (error: {result})")

    # Returns accountID,userID
    parts = result.split(",")
    account_id = int(parts[0])

    # Generate GJP2 for subsequent requests
    gjp2 = gjp2_encode(password)

    return account_id, gjp2
