"""
Method 5: Property 31 (Text Property)

Stores base64 encoded data in property 31 (text property) of a single object.

Now I didn't know why I thought this would work but - it didn't...
"""
from gdparse import GDLevel, LevelObject
from pathlib import Path
import base64
from .compression import compress_data, decompress_data

BLOCK_ID = 211


def encode(filepath: str | Path, skip_compression: bool = False) -> str:
    filepath = Path(filepath)
    data = filepath.read_bytes()
    if not skip_compression:
        data = compress_data(data)

    # Encode file in Base64
    b64_string = base64.b64encode(data).decode('ascii')
    level = GDLevel.create_empty()

    # Create a single object
    obj = LevelObject.create_block(block_id=BLOCK_ID, x=0, y=0)

    # Add the whole data inside a single objects string
    obj.properties[31] = b64_string
    level.add_object(obj)

    return level.serialize()

# Now I didn't know why I thought this would work but - it didn't...


def decode(level_string: str, skip_decompression: bool = False) -> bytes:
    level = GDLevel(level_string)

    b64_string = level.objects[0].properties.get(31)
    data = base64.b64decode(b64_string)

    if not skip_decompression:
        data = decompress_data(data)

    return data

# ^ This is for the (stupid) text property version
