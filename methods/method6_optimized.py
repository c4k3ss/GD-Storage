"""
Method 6: Optimized Base 9999 (THE BEST ONE)

Uses base 9999 encoding with 8-byte chunks for fast processing.
- Processes 8 bytes at a time (avoids O(n^2) big int division)
- Uses groups 1-9999
- Stores original data length to handle padding
- Each 8 bytes becomes exactly 5 groups

8 byte processing is way faster
Faster rendering & smaller (~13%)
Also, I forgot group 0 doesn't exist. I don't really use the GD Editor...

Results:
- Level string overhead: ~2.95x
- On-disk overhead: ~1.73x (GD compresses the save file)

What else was fixed in this version:
- Objects can have at most 10 groups
- Repeating groups was removed
- If an object can have at most two groups, only make it have one and add the other one to the next object
- This is because if it only has two groups it is interpreted as a float and ultimately corrupts the image
- Added compression directly inside here for uploading - instead of relying on Geometry Dash to compress it
"""
from gdparse import GDLevel, LevelObject
from pathlib import Path
from .compression import compress_data, decompress_data
import gzip
import base64

BLOCK_ID = 211
GROUPS_PER_OBJECT = 10  # GD truncates groups beyond 10 when saving in the editor!


def encode(filepath: str | Path, skip_compression: bool = False) -> str:
    # Let's instead process 8 bytes at a time
    filepath = Path(filepath)
    file_data = filepath.read_bytes()

    # Prepend filename (1 byte length + filename bytes) before compression
    filename = filepath.name.encode('utf-8')
    if len(filename) > 255:
        filename = filename[:255]
    data = bytes([len(filename)]) + filename + file_data

    if not skip_compression:
        data = compress_data(data)
    all_groups = []
    # Process 8 bytes at a time
    for i in range(0, len(data), 8):
        chunk = data[i:i+8]

        if len(chunk) < 8:
            chunk = chunk.ljust(8, b'\x00')

        num = int.from_bytes(chunk, 'big')
        chunk_groups = []
        while num > 0:
            chunk_groups.append((num % 9999) + 1)  # 1-9999 instead of 0-9999
            num //= 9999
        # Pad to exactly 5 groups (8 bytes = max 5 base-9999 digits)
        while len(chunk_groups) < 5:
            chunk_groups.append(1)  # Use 1 as padding (represents 0)
        all_groups.extend(reversed(chunk_groups))

    # Store original length as first 2 groups (base 9999, supports up to ~99MB)
    # This keeps all group values within 1-9999
    length = len(data)
    len_high = (length // 9999) + 1  # High part (1-9999)
    len_low = (length % 9999) + 1    # Low part (1-9999)
    all_groups = [len_high, len_low] + all_groups

    level = GDLevel.create_empty()
    obj_index = 0
    current_obj_groups = []
    current_obj_set = set()  # Track groups in current object to avoid duplicates

    for group in all_groups:
        # If this group already exists in current object, or we hit the limit, start new object
        if group in current_obj_set or len(current_obj_groups) >= GROUPS_PER_OBJECT:
            # Would this create a 2-group object? (GD parses "X.Y" as float and corrupts it)
            if len(current_obj_groups) == 2:
                # Only save first group, push second to next object
                first_group = current_obj_groups[0]
                second_group = current_obj_groups[1]

                groups_str = str(first_group)
                obj = LevelObject.create_block(block_id=BLOCK_ID, x=obj_index * 30, y=0)
                obj.properties[57] = groups_str
                level.add_object(obj)
                obj_index += 1

                # Start new object with the pushed second group
                current_obj_groups = [second_group]
                current_obj_set = {second_group}
            else:
                # Save current object normally
                if current_obj_groups:
                    groups_str = '.'.join(str(g) for g in current_obj_groups)
                    obj = LevelObject.create_block(block_id=BLOCK_ID, x=obj_index * 30, y=0)
                    obj.properties[57] = groups_str
                    level.add_object(obj)
                    obj_index += 1
                # Start new object
                current_obj_groups = []
                current_obj_set = set()

        # Check again - the pushed group might conflict with the new group
        if group in current_obj_set:
            # Save the single pushed group and start fresh
            if current_obj_groups:
                groups_str = '.'.join(str(g) for g in current_obj_groups)
                obj = LevelObject.create_block(block_id=BLOCK_ID, x=obj_index * 30, y=0)
                obj.properties[57] = groups_str
                level.add_object(obj)
                obj_index += 1
            current_obj_groups = []
            current_obj_set = set()

        current_obj_groups.append(group)
        current_obj_set.add(group)

    # Don't forget the last object
    if current_obj_groups:
        groups_str = '.'.join(str(g) for g in current_obj_groups)
        obj = LevelObject.create_block(block_id=BLOCK_ID, x=obj_index * 30, y=0)
        obj.properties[57] = groups_str
        level.add_object(obj)

    # Serialize and compress to GD's expected format (gzip + base64)
    raw_level = level.serialize()
    compressed = gzip.compress(raw_level.encode('utf-8'))
    return base64.urlsafe_b64encode(compressed).decode('ascii').rstrip('=')

# 8 byte processing is way faster
# Faster rendering & smaller (~13%)
# Also, group 0 doesn't exist. I don't really use the GD Editor...


def decode(level_string: str, skip_decompression: bool = False) -> tuple[str, bytes]:
    """Decode a level string back to (filename, data)."""
    # Handle both compressed (H4sI...) and raw (kS38...) formats
    if level_string.startswith('H4sI'):
        # Gzip + base64 compressed format
        compressed = base64.urlsafe_b64decode(level_string + '==')
        level_string = gzip.decompress(compressed).decode('utf-8')

    level = GDLevel(level_string)

    # Collect all groups from all objects
    all_groups = []
    for obj in level.objects:
        groups_val = obj.properties.get(57)
        if groups_val is None:
            continue
        # Handle both string and numeric values
        groups_str = str(groups_val)
        all_groups.extend(int(g) for g in groups_str.split('.'))

    # Validate minimum data
    if len(all_groups) < 2:
        raise ValueError("Invalid level: not enough data to decode")

    # First 2 groups are the original data length (base 9999)
    len_high = all_groups[0]
    len_low = all_groups[1]
    original_len = (len_high - 1) * 9999 + (len_low - 1)
    all_groups = all_groups[2:]

    # Process 5 groups at a time (each 8 bytes = ~5 groups)
    result = bytearray()
    for i in range(0, len(all_groups), 5):
        chunk_groups = all_groups[i:i+5]

        # Convert base 9999 back to integer (groups are 1-9999, subtract 1)
        num = 0
        for g in chunk_groups:
            num = num * 9999 + (g - 1)

        result.extend(num.to_bytes(8, 'big'))

    # Trim to original length (remove padding)
    result = bytes(result[:original_len])

    if not skip_decompression:
        result = decompress_data(result)

    # Validate minimum data for filename extraction
    if len(result) < 1:
        raise ValueError("Invalid data: empty result after decompression")

    # Extract filename (1 byte length + filename bytes)
    filename_len = result[0]
    if len(result) < 1 + filename_len:
        raise ValueError("Invalid data: truncated filename")

    filename = result[1:1 + filename_len].decode('utf-8', errors='replace')
    file_data = result[1 + filename_len:]

    return filename, file_data

# ^ This is for the group method using Base9999 and 8 byte processing
