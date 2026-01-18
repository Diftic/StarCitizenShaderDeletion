# Shader Cache Nuke

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Support-orange?style=flat&logo=buy-me-a-coffee)](https://buymeacoffee.com/Mallachi)

One-click shader cache cleaner for Star Citizen and GPU drivers. Clears Star Citizen shader caches, NVIDIA, AMD, and DirectX caches to fix graphical glitches, stuttering, and shader-related issues.

**Version:** 1.2.0  
**Author:** Mallachi

## Features

- 🎯 **Star Citizen Caches** — Detects and lists all SC shader folders with sizes
- 🟢 **NVIDIA Support** — DXCache, GLCache, ComputeCache, NV_Cache
- 🔴 **AMD Support** — DxCache, GLCache, VkCache, Dx9Cache
- 🔷 **DirectX Support** — D3DSCache
- 📊 **Size Display** — Shows cache sizes before deletion
- 🔄 **Auto-Update Check** — Notifies when new versions are available
- ✅ **Selective Deletion** — Choose exactly which caches to clear

## Requirements

- **Windows 10/11**
- **Python 3.10+** (for running from source)

## Quick Start

### Executable

1. Download the latest release
2. Run `ShaderCacheNuke.exe`
3. Select caches to clear
4. Click "NUKE SELECTED"

### From Source

```bash
git clone https://github.com/Diftic/StarCitizenShaderDeletion.git
cd StarCitizenShaderDeletion
python nuke_shaders_gui.py
```

## Usage

1. **Close all games and GPU-intensive applications** before running
2. Select which caches to clear (shader folders are pre-selected by default)
3. Click "NUKE SELECTED"
4. Restart your computer when prompted for full effect

Green dots (●) indicate caches that exist on your system. Gray circles (○) indicate caches not found.

## When to Use

- After Star Citizen patches or updates
- When experiencing graphical glitches or artifacts
- When the game stutters during shader compilation
- After GPU driver updates
- When troubleshooting performance issues

## Notes

- First game launch after nuking will have longer load times as shaders recompile
- This is normal and expected behavior
- Subsequent launches will return to normal speed

## Building

```bash
python build.py
```

Output executable will be in `dist/`.

## License

For personal use with Star Citizen. Not affiliated with CIG or RSI.
