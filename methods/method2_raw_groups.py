"""
Method 2: Raw Groups

Stores raw byte values (0-255) directly as group numbers.
Each object can have up to 9999 groups, so we chunk the data.

This worked! YAY - But the level was ~1GB, and while it did load
Geometry Dash took longer to load in general and the game crashed when you tried to close it
But the level preserved! So technically it worked...?
Obviously storing raw data wasn't gonna be space or time efficient
"""
from gdparse import GDLevel, LevelObject
from pathlib import Path
from .compression import compress_data, decompress_data

BLOCK_ID = 211
CHUNK_SIZE = 9999


def encode(filepath: str | Path, skip_compression: bool = False) -> str:
    # This one might work... Geometry Dash doesn't check
    # for repeating groups inside objects when loading the level
    filepath = Path(filepath)
    data = filepath.read_bytes()
    if not skip_compression:
        data=compress_data(data)
    chunks = [data[i:i+CHUNK_SIZE] for i in range (0, len(data), CHUNK_SIZE)]
    level = GDLevel.create_empty()
    for i, chunk in enumerate(chunks):
        #Convert chunk bytes to groups string
        groups_str = '.'.join(str(b) for b in chunk)
        obj = LevelObject.create_block(block_id=BLOCK_ID, x=i*10, y=0)
        obj.properties[57]=groups_str
        level.add_object(obj)

    return level.serialize()

# ^ This worked! YAY - But the level was ~1GB, and while it did load
# Geometry Dash took longer to load in general and the game crashed when you tried to close it
# But the level preserved! So technically it worked...?
# Obviously storing raw data wasn't gonna be space or time efficient


def decode(level_string: str, skip_decompression: bool = False) -> bytes:
    level = GDLevel(level_string)

    group_data=[]

    for obj in level.objects:
        object_groups=obj.properties.get(57).split('.')
        byte_values= [int(x) for x in object_groups]
        group_data.extend(byte_values)
    data = bytes(group_data)
    if not skip_decompression:
        data = decompress_data(data)

    return data

# ^ This is for the group method
