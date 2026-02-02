"""
Method 4: Base64 Groups

Encodes data as base64 and stores in the groups property.

Objects inside levels can have non-numeric groups but Geometry Dash doesn't load them when playing
But that's not really relevant - we just want the level data to be preserved

T̶h̶i̶s̶ ̶c̶o̶u̶l̶d̶ ̶w̶o̶r̶k̶ ̶b̶u̶t̶ ̶I̶'̶m̶ ̶u̶n̶s̶u̶r̶e̶ ̶t̶h̶e̶ ̶l̶e̶v̶e̶l̶ ̶i̶s̶ ̶a̶c̶t̶u̶a̶l̶l̶y̶ ̶p̶r̶e̶s̶e̶r̶v̶e̶d̶
It is not preserved - it strips any non-numeric groups
"""
from gdparse import GDLevel, LevelObject
from pathlib import Path
import base64
from .compression import compress_data, decompress_data

BLOCK_ID = 211
CHUNK_SIZE = 9999


def encode(filepath: str | Path, skip_compression: bool = False) -> str:
    # Objects inside levels can have non-numeric groups but Geometry Dash doesn't load them when playing
    # But that's not really relevant - we just want the level data to be preserved
    filepath = Path(filepath)
    data = filepath.read_bytes()
    if not skip_compression:
        data=compress_data(data)
    b64_data=base64.b64encode(data).decode('ascii')
    chunks = [b64_data[i:i+CHUNK_SIZE] for i in range (0, len(b64_data), CHUNK_SIZE)]
    level = GDLevel.create_empty()
    for i, chunk in enumerate(chunks):
        obj = LevelObject.create_block(block_id=BLOCK_ID, x=i*10, y=0)
        obj.properties[57]= chunk
        level.add_object(obj)
    return level.serialize()

# This could work but I'm unsure the level is actually preserved
# It is not preserved - it strips any non-numeric groups


def decode(level_string: str, skip_decompression: bool = False) -> bytes:
    level = GDLevel(level_string)

    # Concatenate all chunks
    b64_string = ''.join(obj.properties.get(57) for obj in level.objects)
    data = base64.b64decode(b64_string)
    if not skip_decompression:
        data = decompress_data(data)

    return data

# ^ This is for the group method using Base64
