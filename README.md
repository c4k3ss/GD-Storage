# GD Storage



## What is this?

GD Storage lets you hide any file inside a Geometry Dash level by encoding the file's binary data into level object properties. The encoded level can be:
- Saved to your local GD save file
- Uploaded to GD servers and shared via level ID
- Downloaded and decoded back to the original file

## Features

- **Upload to GD Servers** - Store files on RobTop's servers, get a level ID to share
- **Fetch from GD Servers** - Download and decode files using just a level ID
- **Local Save Support** - Inject encoded levels directly into your GD save file
- **Cross-Platform** - Works on Windows, macOS, and Linux (via Proton)
- **Configurable** - Custom GD save paths for non-standard installations
- **Secure** - Path traversal protection, input validation, overwrite confirmation

## Installation

Requires Python 3.10+

```bash
pip install gd-storage
```

Or install in development mode:

```bash
git clone https://github.com/c4k3ss/GD-Storage
cd GD-Storage
pip install -e .
```

## Usage

```bash
# Upload a file to GD servers
gd-storage --upload photo.png

# Download and decode from GD servers
gd-storage --fetch 123456789

# Encode and inject into local GD save
gd-storage --encode document.pdf

# Decode from local GD save
gd-storage --decode "LevelName"

# Configure GD save path (for non-standard installations)
gd-storage --config
```

## How It Works

Files are encoded using a base-9999 group encoding method:

1. **Compression** - The file is gzip compressed with the filename prepended
2. **Chunking** - Binary data is split into 8-byte chunks
3. **Base Conversion** - Each chunk is converted to 5 base-9999 numbers (1-9999)
4. **Object Encoding** - Numbers are stored in GD object group properties (property 57)
5. **Level String** - Objects are serialized into a valid GD level string


### Why Base-9999?

GD supports up to 9999 groups per object. By treating group numbers as digits in a base-9999 number system, we can efficiently pack 8 bytes into just 5 group values, achieving ~62.5% space efficiency.

## Configuration

On first run, GD Storage auto-detects your save path:
- **Windows**: `%LOCALAPPDATA%\GeometryDash`
- **macOS**: `~/Library/Application Support/GeometryDash`

For custom paths (Linux/Proton, custom installs), run:

```bash
gd-storage --config
```

Config is saved to `~/.config/gd-storage/config.json`

## Platform Support

| Platform | Local Save | Upload/Fetch |
|----------|------------|--------------|
| Windows  | Yes        | Yes          |
| macOS    | Yes        | Yes          |
| Linux    | Yes*       | Yes          |

*Linux requires configuring the Proton GD save path manually


## Dependencies

- [dashlib](https://pypi.org/project/dashlib/) - GD server API
- [gdparse](https://pypi.org/project/gdparse/) - GD level string parsing
- [pycryptodomex](https://pypi.org/project/pycryptodomex/) - AES encryption for macOS saves
- [zstandard](https://pypi.org/project/zstandard/) - Zstandard compression

## Acknowledgments

Save file handling is based on a modified version of [PyCCGameManager](https://github.com/camila314/PyCCGameManager).

## License

GD Storage is licensed under the MIT License

## Disclaimer

This project is for educational purposes. Use responsibly and don't abuse GD's servers.

> GitHub [@c4k3ss](https://github.com/c4k3ss) &nbsp;&middot;&nbsp;
> Twitter [@_c4k3ss](https://x.com/_c4k3ss)