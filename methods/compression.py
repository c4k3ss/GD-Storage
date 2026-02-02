import zstandard as zstd

def compress_data(data: bytes) -> bytes:
    compressor = zstd.ZstdCompressor(level=19)
    return compressor.compress(data)


def decompress_data(data: bytes) -> bytes:
    decompressor = zstd.ZstdDecompressor()
    return decompressor.decompress(data)
