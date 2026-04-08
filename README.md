# SC Performance Tool

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Support-orange?style=flat&logo=buy-me-a-coffee)](https://buymeacoffee.com/Mallachi)
[![Latest Release](https://img.shields.io/github/v/release/Diftic/StarCitizenShaderDeletion?label=download&color=blue)](https://github.com/Diftic/StarCitizenShaderDeletion/releases/latest)

A guided performance maintenance tool for Star Citizen. Scans your system, walks you through manual optimisation steps, then automatically clears shader caches and GPU driver caches — all in a clean 4-step wizard.

**Version:** 3.2.0  
**Author:** Mallachi

---

## Features

- 🔍 **System Analysis** — Scans shader caches, GPU caches, temp files, running processes, HAGS status, and power plan in one pass
- 🧙 **Guided Wizard** — 4-step flow: Analysis → Manual Actions → Automated Cleaning → Done
- 🎯 **Star Citizen Caches** — Detects all SC shader folders across all drives and channels (LIVE, PTU, EPTU, TECH-PREVIEW)
- 🟢 **NVIDIA Support** — DXCache, GLCache, ComputeCache, NV_Cache (registry-detected path)
- 🔴 **AMD Support** — DxCache, GLCache, VkCache, Dx9Cache
- 🔷 **DirectX Support** — D3DSCache
- ⚙️ **System Checks** — HAGS, power plan, conflicting processes (RivaTuner, MSI Afterburner, Xbox Game Bar)
- 🧹 **Selective Cleaning** — Checkboxes with size display; Select All / Deselect All
- 🔒 **Locked File Handling** — Files in use are scheduled for deletion at next boot via `MoveFileExW`
- 🧠 **Standby Memory Clear** — Purges the Windows standby list (admin only)
- 🌙 **Light / Dark theme** — WCAG AA-compliant palettes; toggle in one click with no restart
- 🔄 **Auto-Update Check** — Notifies when a new release is available on GitHub

---

## Requirements

- **Windows 10 / 11**
- **Administrator privileges** (the tool requests elevation automatically)
- **Python 3.10+** only required if running from source

---

## Quick Start

### Executable (recommended)

1. Download **ShaderCacheNuke.exe** from the [latest release](https://github.com/Diftic/StarCitizenShaderDeletion/releases/latest)
2. Run it — Windows will prompt for administrator access
3. Follow the 4-step wizard

### From Source

```bash
git clone https://github.com/Diftic/StarCitizenShaderDeletion.git
cd StarCitizenShaderDeletion
python nuke_shaders_gui.py
```

---

## Screenshots

<table>
  <tr>
    <td align="center"><b>Step 1 — Analysis</b><br><img src="images/Screenshot%202026-04-08%20235321.png" width="380"></td>
    <td align="center"><b>Step 2 — Manual Actions</b><br><img src="images/Screenshot%202026-04-08%20235331.png" width="380"></td>
  </tr>
  <tr>
    <td align="center"><b>Step 3 — Cleaning</b><br><img src="images/Screenshot%202026-04-08%20235344.png" width="380"></td>
    <td align="center"><b>Step 4 — Done</b><br><img src="images/Screenshot%202026-04-08%20235405.png" width="380"></td>
  </tr>
</table>

---

## How It Works

### Step 1 — Analysis
The tool scans your system and produces a full report: shader cache sizes, GPU cache sizes, temp file sizes, running processes, HAGS status, power plan, and available RAM. Nothing is changed at this step.

### Step 2 — Manual Actions
Flagged items that require manual intervention are listed with status indicators and direct-open buttons:
- **HAGS** — opens Graphics Settings if disabled
- **Power Plan** — opens Power Options if not set to High Performance / Ultimate Performance
- **Conflicting Processes** — RivaTuner, MSI Afterburner, Xbox Game Bar

### Step 3 — Automated Cleaning
A checklist of everything that can be cleared automatically, pre-ticked based on what was found. Review, adjust, and click **Run Cleaning**.

### Step 4 — Done
Full per-operation summary with ✔/✘ results. If any locked files were scheduled for reboot deletion, a **REBOOT REQUIRED** banner is shown. A **Restart Computer** button is available.

---

## When to Use

- After Star Citizen patches or updates
- When experiencing graphical glitches, stuttering, or shader-related issues
- After GPU driver updates
- Before a play session if performance has degraded

---

## Notes

- The first SC launch after clearing shader caches will take longer as shaders recompile — this is normal
- Standby memory clear requires administrator privileges and `SeProfileSingleProcessPrivilege`
- The tool will not modify files outside of known cache locations

---

## Building from Source

```bash
python build.py
```

Output: `dist/ShaderCacheNuke.exe` (~10 MB, UAC manifest embedded)

---

## License

For personal use with Star Citizen. Not affiliated with Cloud Imperium Games or Roberts Space Industries.
