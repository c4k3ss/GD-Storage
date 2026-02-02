"""
GD Save Manager - Fixed version of PyCCManager

Handles reading/writing Geometry Dash save files on Windows and macOS.

Fixes self reference error
"""
import os
import zlib
import base64
import struct
import platform
from Cryptodome.Cipher import AES


class GDData:
    def __init__(self, path):
        self.path = path
        self.ccll_path = f"{path}/CCLocalLevels.dat"
        self.ccgm_path = f"{path}/CCGameManager.dat"
        self.ccll = self.decode(open(self.ccll_path, "rb").read())
        self.ccgm = self.decode(open(self.ccgm_path, "rb").read())

    def injectLevel(self, levelData, levelName="Injected", levelDesc="Injected level"):
        levels = self.ccll.split(b">k_")
        header = levels[0]
        payload = (
            header + b">k_0</k><d><k>kCEK</k><i>4</i><k>k18</k><i>2</i><k>k2</k><s>"
            + levelName.encode() + b"</s><k>k4</k><s>"
            + levelData.encode() + b"</s><k>k5</k><s>"
            + levelDesc.encode() + b"</s><k>k13</k><t /><k>k21</k><i>2</i><k>k16</k><i>1</i>"
            + b"<k>k80</k><i>338</i><k>k81</k><i>23</i><k>k83</k><i>109</i><k>k50</k><i>35</i>"
            + b"<k>k48</k><i>23</i><k>kI1</k><r>-1118.36</r><k>kI2</k><r>-366.449</r>"
            + b"<k>kI3</k><r>0.7</r><k>kI4</k><i>2</i><k>kI5</k><i>11</i><k>kI7</k><i>1</i>"
            + b"<k>kI6</k><d><k>0</k><s>0</s><k>1</k><s>0</s><k>2</k><s>0</s><k>3</k><s>0</s>"
            + b"<k>4</k><s>0</s><k>5</k><s>0</s><k>6</k><s>0</s><k>7</k><s>0</s><k>8</k><s>0</s>"
            + b"<k>9</k><s>0</s><k>10</k><s>0</s><k>11</k><s>2</s><k>12</k><s>0</s></d></d><k"
        )
        for i in range(1, len(levels)):
            payload += b">k_" + str(i).encode() + b"<" + b"<".join(levels[i].split(b"<")[1:])
        self.ccll = payload

    def save(self, ccll=True, ccgm=True):
        if ccll:
            open(self.ccll_path, "wb").write(self.encode(self.ccll))
        if ccgm:
            open(self.ccgm_path, "wb").write(self.encode(self.ccgm))

    def encode(self, data):
        raise NotImplementedError

    def decode(self, data):
        raise NotImplementedError


class GDWinData(GDData):
    """Windows GD save format (XOR + zlib)"""

    def __init__(self, path=None):
        if path is None:
            path = os.path.join(os.getenv("LOCALAPPDATA", ""), "GeometryDash")
        super().__init__(path)

    def encode(self, data):
        compressed = zlib.compress(data)
        crc32 = struct.pack('I', zlib.crc32(data))
        size = struct.pack('I', len(data))
        encrypted = base64.b64encode(
            b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x0b' + compressed[2:-4] + crc32 + size,
            b'-_'
        )
        return bytes([a ^ 11 for a in encrypted])

    def decode(self, data):
        decrypted = bytes([a ^ 11 for a in data])
        return zlib.decompress(base64.b64decode(decrypted, b'-_')[10:], -zlib.MAX_WBITS)


class GDMacData(GDData):
    """macOS GD save format (AES encryption)"""

    MAC_KEY = b"\x69\x70\x75\x39\x54\x55\x76\x35\x34\x79\x76\x5d\x69\x73\x46\x4d\x68\x35\x40\x3b\x74\x2e\x35\x77\x33\x34\x45\x32\x52\x79\x40\x7b"

    def __init__(self, path=None):
        if path is None:
            path = os.path.join(os.path.expanduser("~"), "Library/Application Support/GeometryDash")
        self.cipher = AES.new(GDMacData.MAC_KEY, AES.MODE_ECB)
        super().__init__(path)

    def encode(self, data):
        extra = len(data) % 16
        if extra > 0:
            data += (b'\x0b' * (16 - extra))
        return self.cipher.encrypt(data)

    def decode(self, data):
        return self.cipher.decrypt(data)


def new_manager(path=None, format="auto"):
    """
    Create a GD save manager.

    Args:
        path: Custom GD save folder path. If None, uses platform default.
        format: "auto", "windows", or "mac"
    """
    if format == "auto":
        format = "mac" if platform.system() == "Darwin" else "windows"

    if format == "mac":
        return GDMacData(path)
    else:
        return GDWinData(path)
