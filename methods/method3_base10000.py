"""
Method 3: Base 10000

Uses base 10000 encoding to make better use of the 9999 available groups.
Processes 256 bytes at a time and converts to base 10000.

So this helps - not by a lot but it does make the level smaller - but not small enough
Also - the time to process this is insanely long - simply not worth it

Python big int division is O(n^2), so smaller chunks = faster
"""
from gdparse import GDLevel, LevelObject
from pathlib import Path
from .compression import compress_data, decompress_data

BLOCK_ID = 211
BASE10000_CHUNK = 256  # bytes per chunk


def encode(filepath: str | Path, skip_compression: bool = False) -> str:
    # Let's try using Base 10000
    # There are 9999 groups - we only used the first 255
    filepath = Path(filepath)
    data = filepath.read_bytes()
    if not skip_compression:
        data=compress_data(data)
    level = GDLevel.create_empty()
    for i in range(0, len(data), BASE10000_CHUNK):
        chunk = data[i:i + BASE10000_CHUNK]

        # Convert Bytes to Base 10000
        big_int = int.from_bytes(chunk, 'big')
        groups=[]
        while big_int > 0:
            groups.append(big_int % 10000)
            big_int //= 10000
        groups = list(reversed(groups)) or [0]

        #Store chunk length as first group
        groups = [len(chunk)] + groups

        groups_str = '.'.join(str(g) for g in groups)
        obj = LevelObject.create_block(block_id=BLOCK_ID, x=i*30, y=0)
        obj.properties[57] = groups_str
        level.add_object(obj)

    return level.serialize()


# So this helps - not by a lot but it does make the level smaller - but not small enough
# Also - the time to process this is insanely long - simply not worth it


def decode(level_string: str, skip_decompression: bool = False) -> bytes:
    level = GDLevel(level_string)
    result = b''

    for obj in level.objects:
        groups = [int(g) for g in obj.properties.get(57).split('.')]
        chunk_len = groups[0]
        groups = groups[1:]

        big_int = 0
        for g in groups:
            big_int = big_int * 10000 + g

        result += big_int.to_bytes(chunk_len, 'big')

    if not skip_decompression:
        result = decompress_data(result)

    return result

# ^ This is for the group method using Base10000 for storing
