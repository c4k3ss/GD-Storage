"""
Method 1: X/Y Coordinates

Encodes each byte pair as X and Y coordinates of objects.
- First byte = X position
- Second byte = Y position
- If odd number of bytes, last object has Y = -1

While this did technically work - I didn't bother actually testing it as it was too unoptimized
"""
from gdparse import GDLevel, LevelObject
from pathlib import Path
from .compression import compress_data, decompress_data

BLOCK_ID = 211


def encode(filepath: str | Path, skip_compression: bool = False) -> str:
    filepath = Path(filepath)
    raw_data = filepath.read_bytes()

    compressed = compress_data(raw_data) if not skip_compression else raw_data

    print(f"Original: {len(raw_data)} bytes")
    print(f"Compressed: {len(compressed)} bytes ({len(compressed)/len(raw_data)*100:.1f}%)")

    # Create empty level
    level = GDLevel.create_empty()

    # Encode each byte as an object
    # Go through the bytes two by two - X being the first byte and y being the second
    for i in range(0, len(compressed) - len(compressed) % 2, 2):
        byte1 = compressed[i]
        byte2 = compressed[i+1]
        obj = LevelObject.create_block(
            block_id=BLOCK_ID,
            x=byte1,
            y=byte2,
        )
        level.add_object(obj)
    # Check if the last byte doesn't have a pair - in which case it has -1 as the y for the decoder
    if len(compressed) % 2 == 1:
        obj = LevelObject.create_block(
            block_id=BLOCK_ID,
            x=compressed[len(compressed) - 1],
            y=-1
        )
        level.add_object(obj)

    print(f"Objects created: {len(compressed)}")

    return level.serialize()

# While this did technically work - I didn't bother actually testing it as it was too unoptimized


def decode(level_string: str, skip_decompression: bool = False) -> bytes:

    level = GDLevel(level_string)

    compressed_bytes = []

    # Extract byte value from X and Y

    for obj in level.objects:
        x = obj.properties.get(2, 0)
        y = obj.properties.get(3, 0)

        compressed_bytes.append(x)

        if y != -1:
            compressed_bytes.append(y)

    compressed = bytes(compressed_bytes)

    # Decompress
    if not skip_decompression:
        return decompress_data(compressed)
    return compressed

#  ^ This is for the unoptimized version
