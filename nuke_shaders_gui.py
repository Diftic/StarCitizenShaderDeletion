#!/usr/bin/env python3
"""
Star Citizen Performance Tool v3.0.0
4-step wizard: Analysis -> Manual Actions -> Automated Cleaning -> Done
"""

import collections.abc
import csv
import ctypes
import ctypes.wintypes
import io
import json
import logging
import os
import re
import string
import subprocess
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
import winreg
from datetime import datetime
from pathlib import Path


import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk


VERSION = "3.0.0"
GITHUB_REPO = "Diftic/StarCitizenShaderDeletion"

STEP_ANALYSIS = 0
STEP_MANUAL = 1
STEP_CLEANING = 2
STEP_DONE = 3
STEP_LABELS = ["1  Analysis", "2  Manual", "3  Cleaning", "4  Done"]

POWER_PLANS = {
    "381b4222-f694-41f0-9685-ff5bb260df2e": "Balanced",
    "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c": "High Performance",
    "a1841308-3541-4fab-bc81-f71556f20b4a": "Power Saver",
    "e9a42b02-d5df-448d-aa00-03f14749eb61": "Ultimate Performance",
}
RECOMMENDED_POWER_GUIDS = {
    "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
    "e9a42b02-d5df-448d-aa00-03f14749eb61",
}

# Processes that must be closed before cleaning
SC_PROCESSES = {
    "StarCitizen.exe": "Star Citizen",
    "RSILauncher.exe": "RSI Launcher",
    "EasyAntiCheat.exe": "Easy Anti-Cheat",
}

# Processes known to conflict with Star Citizen
CONFLICT_PROCESSES = {
    "RTSS.exe": "RivaTuner Statistics Server",
    "MSIAfterburner.exe": "MSI Afterburner",
    "GameBar.exe": "Xbox Game Bar",
    "GameBarFTServer.exe": "Xbox Game Bar Service",
}
CONFLICT_INSTRUCTIONS = {
    "RTSS.exe": "Close RivaTuner via the system tray before launching SC.",
    "MSIAfterburner.exe": "Disable the in-game overlay in MSI Afterburner settings.",
    "GameBar.exe": "Press Win + I → Gaming → Xbox Game Bar → Turn off.",
    "GameBarFTServer.exe": "Press Win + I → Gaming → Xbox Game Bar → Turn off.",
}

# ms-settings URI or callable for processes that have a direct settings page
CONFLICT_SETTINGS: dict[str, tuple[str, str]] = {
    "GameBar.exe": ("Open Game Bar Settings", "ms-settings:gaming-gamebar"),
    "GameBarFTServer.exe": ("Open Game Bar Settings", "ms-settings:gaming-gamebar"),
}

THEMES: dict[str, dict[str, str]] = {
    "Light": {
        "bg": "#f0f0f0",
        "fg": "#000000",
        "text_bg": "#f8fafc",          # slate-50 — softer than pure white, less glare
        "text_fg": "#111111",
        "text_insert": "#000000",
        "canvas_bg": "#f0f0f0",
        "bar_bg": "#dbeafe",           # sky-100 — tinted header/footer bars
        "step_active": "#0369a1",      # sky-700
        "step_done": "#475569",        # slate-600
        "step_future": "#767676",      # min WCAG AA on white
        "detail_fg": "#595959",        # 7:1 on white
        "info_fg": "#6b6b6b",          # 5.7:1 on white
        "dim_fg": "#767676",           # 4.5:1 on white (AA threshold)
        "accent": "#0369a1",           # sky-700
        "section_fg": "#0369a1",
        "disabled_fg": "#767676",
        "tag_header": "#0369a1",
        "tag_info": "#6b6b6b",
        "tag_dim": "#767676",
        "labelframe_border": "#93c5fd", # blue-300
        "btn_primary": "#0369a1",      # sky-700 — 5.9:1 vs white text
        "color_good": "#166534",       # green-800 — 7.1:1 on #f8fafc
        "color_warn": "#c2410c",       # orange-700 — 5.2:1 on #f8fafc
        "color_issue": "#b91c1c",      # red-700 — 6.5:1 on #f8fafc
    },
    "Dark": {
        "bg": "#1e1e1e",
        "fg": "#e0e0e0",
        "text_bg": "#1a1a2e",          # dark blue-black for log areas
        "text_fg": "#d4d4d4",
        "text_insert": "#ffffff",
        "canvas_bg": "#1e1e1e",
        "bar_bg": "#0f172a",           # slate-900 — deep navy header/footer bars
        "step_active": "#38bdf8",      # sky-400
        "step_done": "#94a3b8",        # slate-400
        "step_future": "#8a8a8a",      # passes AA on #1e1e1e
        "detail_fg": "#9e9e9e",
        "info_fg": "#9e9e9e",
        "dim_fg": "#8a8a8a",           # passes AA on #1e1e1e
        "accent": "#38bdf8",           # sky-400
        "section_fg": "#67e8f9",       # cyan-300 — distinct pop for section headers
        "disabled_fg": "#6e6e6e",
        "tag_header": "#38bdf8",
        "tag_info": "#9e9e9e",
        "tag_dim": "#8a8a8a",
        "labelframe_border": "#1e3a5f", # deep blue border
        "btn_primary": "#0369a1",      # sky-700 — 5.9:1 vs white text
        "color_good": "#4ade80",       # green-400 — 9.8:1 on #1a1a2e
        "color_warn": "#fb923c",       # orange-400 — 7.5:1 on #1a1a2e
        "color_issue": "#f87171",      # red-400 — 6.2:1 on #1a1a2e
    },
}


# =============================================================================
# Analyzer — all scanning logic, no UI
# =============================================================================

class Analyzer:
    def __init__(
        self,
        local_appdata: Path,
        program_data: Path,
        windir: Path,
        temp_dir: Path,
    ) -> None:
        self.local_appdata = local_appdata
        self.program_data = program_data
        self.windir = windir
        self.temp_dir = temp_dir

    def run(self, progress: collections.abc.Callable[[str], None]) -> dict:
        """Run all scans. Calls progress(str) for status updates. Returns report dict."""
        report: dict = {}

        progress("Scanning Star Citizen shader caches...")
        report["sc_shaders"] = self._scan_sc_shaders()

        progress("Locating Star Citizen installation...")
        report["sc_installs"] = self._scan_sc_installs()

        progress("Scanning GPU driver caches...")
        report["gpu_caches"] = self._scan_gpu_caches()

        progress("Measuring temporary files...")
        report["temp_size"] = self._get_folder_size(self.temp_dir)
        report["wintemp_size"] = self._get_folder_size(self.windir / "Temp")

        progress("Checking running processes...")
        running = self._get_running_processes()
        report["sc_procs"] = {exe: info for exe, info in running.items() if exe in SC_PROCESSES}
        report["conflict_procs"] = {
            exe: info for exe, info in running.items() if exe in CONFLICT_PROCESSES
        }

        progress("Checking HAGS status...")
        report["hags_enabled"] = self._get_hags_status()

        progress("Checking power plan...")
        report["power_plan"] = self._get_power_plan()

        progress("Reading memory status...")
        report["memory"] = self._get_memory_info()

        return report

    # --- Scanners ---

    def _scan_sc_shaders(self) -> list[tuple[str, Path, int]]:
        """Returns [(name, path, size_bytes), ...]."""
        sc_base = self.local_appdata / "star citizen"
        if not sc_base.exists():
            return []

        results = []
        try:
            for entry in sc_base.iterdir():
                if entry.is_dir() and not self._is_reparse_point(entry):
                    results.append((entry.name, entry, self._get_folder_size(entry)))
        except (PermissionError, OSError):
            pass

        def sort_key(item: tuple) -> tuple:
            name = item[0].lower()
            if name.startswith("starcitizen_"):
                return (0, name)
            if name == "crashes":
                return (2, name)
            return (1, name)

        return sorted(results, key=sort_key)

    def _scan_sc_installs(self) -> dict[str, tuple[Path, Path | None, int]]:
        """Returns {channel: (install_path, cache_path_or_None, cache_size)}."""
        channels = ["LIVE", "PTU", "EPTU", "TECH-PREVIEW"]
        result: dict[str, tuple[Path, Path | None, int]] = {}

        for drive in self._get_drive_letters():
            for base_rel in (
                "Program Files/Roberts Space Industries/StarCitizen",
                "Roberts Space Industries/StarCitizen",
                "Games/Roberts Space Industries/StarCitizen",
            ):
                base = Path(drive) / base_rel
                if not base.exists():
                    continue
                for channel in channels:
                    if channel in result:
                        continue
                    channel_path = base / channel
                    if not channel_path.exists():
                        continue
                    cache_path = channel_path / "data" / "cache"
                    exists = cache_path.exists()
                    size = self._get_folder_size(cache_path) if exists else 0
                    result[channel] = (channel_path, cache_path if exists else None, size)

        return result

    def _scan_gpu_caches(self) -> dict[str, list[tuple[str, str, Path, int, bool]]]:
        """Returns {category: [(key, name, path, size, recreate), ...]}."""
        nv_cache = self._get_nvidia_cache_from_registry() or (
            self.program_data / "NVIDIA Corporation" / "NV_Cache"
        )
        nv = self.local_appdata / "NVIDIA"
        amd = self.local_appdata / "AMD"

        definitions: dict[str, list[tuple[str, str, Path, bool]]] = {
            "NVIDIA": [
                ("nv_dxcache", "DXCache", nv / "DXCache", True),
                ("nv_glcache", "GLCache", nv / "GLCache", True),
                ("nv_compute", "ComputeCache", nv / "ComputeCache", True),
                ("nv_cache", "NV_Cache", nv_cache, True),
            ],
            "AMD": [
                ("amd_dxcache", "DxCache", amd / "DxCache", True),
                ("amd_glcache", "GLCache", amd / "GLCache", True),
                ("amd_vkcache", "VkCache", amd / "VkCache", True),
                ("amd_dx9cache", "Dx9Cache", amd / "Dx9Cache", True),
            ],
            "DirectX": [
                ("dx_d3ds", "D3DSCache", self.local_appdata / "D3DSCache", True),
            ],
        }

        result: dict[str, list[tuple[str, str, Path, int, bool]]] = {}
        for category, items in definitions.items():
            built = []
            for key, name, path, recreate in items:
                size = self._get_folder_size(path) if path.exists() else 0
                built.append((key, name, path, size, recreate))
            result[category] = built
        return result

    def _get_running_processes(self) -> dict[str, tuple[str, int]]:
        """Returns {exe_name: (display_name, pid)} for tracked processes only."""
        result: dict[str, tuple[str, int]] = {}
        try:
            out = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                timeout=10,
            ).stdout
            reader = csv.reader(io.StringIO(out))
            for row in reader:
                if len(row) < 2:
                    continue
                exe = row[0]
                try:
                    pid = int(row[1])
                except ValueError:
                    continue
                if exe in SC_PROCESSES:
                    result[exe] = (SC_PROCESSES[exe], pid)
                elif exe in CONFLICT_PROCESSES:
                    result[exe] = (CONFLICT_PROCESSES[exe], pid)
        except (subprocess.TimeoutExpired, OSError):
            pass
        return result

    def _get_hags_status(self) -> bool | None:
        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers",
                access=winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
            )
        except OSError:
            return None  # Key missing entirely — can't determine
        try:
            value, _ = winreg.QueryValueEx(key, "HwSchMode")
            winreg.CloseKey(key)
            return value == 2
        except OSError:
            winreg.CloseKey(key)
            return False  # Value absent = never enabled, treat as disabled

    def _get_power_plan(self) -> tuple[str, str]:
        try:
            out = subprocess.run(
                ["powercfg", "/getactivescheme"],
                capture_output=True,
                text=True,
                timeout=5,
            ).stdout.strip()
            match = re.search(
                r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
                out,
                re.IGNORECASE,
            )
            if match:
                guid = match.group(1).lower()
                name = POWER_PLANS.get(guid)
                if not name:
                    m2 = re.search(r"\((.+?)\)", out)
                    name = m2.group(1) if m2 else "Unknown"
                return name, guid
        except (subprocess.TimeoutExpired, OSError):
            pass
        return "Unknown", ""

    def _get_memory_info(self) -> dict:
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.wintypes.DWORD),
                ("dwMemoryLoad", ctypes.wintypes.DWORD),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        gb = 1024**3
        return {
            "total_gb": stat.ullTotalPhys / gb,
            "available_gb": stat.ullAvailPhys / gb,
        }

    def _get_nvidia_cache_from_registry(self) -> Path | None:
        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\NVIDIA Corporation\Global\NVCache",
            )
            value, _ = winreg.QueryValueEx(key, "NVCachePath")
            winreg.CloseKey(key)
        except OSError:
            return None

        path = Path(value)
        # Reject non-absolute paths and UNC paths (\\server\share) to prevent
        # registry-poisoning attacks that redirect cleaning to arbitrary locations
        if not path.is_absolute() or str(path).startswith("\\\\"):
            return None
        allowed_roots = (self.program_data, self.local_appdata)
        if not any(path == root or path.is_relative_to(root) for root in allowed_roots):
            return None
        return path

    # --- Utilities ---

    def _get_folder_size(self, path: Path) -> int:
        total = 0
        try:
            for entry in path.rglob("*"):
                if entry.is_file():
                    try:
                        total += entry.stat().st_size
                    except (PermissionError, OSError):
                        pass
        except (PermissionError, OSError):
            pass
        return total

    @staticmethod
    def _is_reparse_point(path: Path) -> bool:
        """Return True if path is a symlink or Windows reparse point (junction)."""
        if path.is_symlink():
            return True
        try:
            # FILE_ATTRIBUTE_REPARSE_POINT = 0x400
            st = path.stat()
            return bool(getattr(st, "st_file_attributes", 0) & 0x400)
        except OSError:
            return True  # treat stat failure as suspicious

    def _get_drive_letters(self) -> list[str]:
        drives = []
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for i, letter in enumerate(string.ascii_uppercase):
            if bitmask & (1 << i):
                drives.append(f"{letter}:\\")
        return drives


# =============================================================================
# CleanerEngine — all cleaning operations, no UI
# =============================================================================

class CleanerEngine:
    @staticmethod
    def clear_folder(path: Path, recreate: bool = True) -> tuple[bool, str]:
        if not path.exists():
            return False, "Not found"

        # Refuse to operate on symlinks or reparse points (junction attack mitigation)
        if path.is_symlink():
            return False, "Path is a symlink — skipped for safety"
        try:
            if getattr(path.stat(), "st_file_attributes", 0) & 0x400:
                return False, "Path is a reparse point — skipped for safety"
        except OSError:
            return False, "Stat failed — skipped for safety"

        deleted = skipped = scheduled = bytes_freed = scheduled_bytes = 0
        _REBOOT_DELETE = 0x4  # MOVEFILE_DELAY_UNTIL_REBOOT with NULL dest = delete on boot

        for root, dirs, files in os.walk(path, topdown=False):
            for name in files:
                fp = Path(root) / name
                try:
                    file_size = fp.stat().st_size
                    fp.unlink()
                    bytes_freed += file_size
                    deleted += 1
                except (PermissionError, OSError):
                    # File is locked — schedule it for deletion at next boot
                    try:
                        file_size = fp.stat().st_size
                    except OSError:
                        file_size = 0
                    if ctypes.windll.kernel32.MoveFileExW(str(fp), None, _REBOOT_DELETE):
                        scheduled += 1
                        scheduled_bytes += file_size
                    else:
                        skipped += 1
            for name in dirs:
                try:
                    (Path(root) / name).rmdir()
                except (PermissionError, OSError):
                    pass

        try:
            if path.exists() and not any(path.iterdir()):
                path.rmdir()
        except (PermissionError, OSError):
            pass

        if recreate:
            try:
                path.mkdir(parents=True, exist_ok=True)
            except (PermissionError, OSError):
                pass

        freed_mb = bytes_freed / (1024 * 1024)
        sched_mb = scheduled_bytes / (1024 * 1024)
        parts = []
        if deleted > 0:
            parts.append(f"Cleared {deleted} files ({freed_mb:.1f} MB)")
        if scheduled > 0:
            parts.append(f"{scheduled} scheduled for reboot deletion ({sched_mb:.1f} MB pending)")
        if skipped > 0:
            parts.append(f"{skipped} could not be cleared")

        if not parts:
            return True, "Nothing to clear"
        if deleted == 0 and scheduled == 0:
            return False, f"All {skipped} files locked — could not schedule"
        return True, ", ".join(parts)

    @staticmethod
    def kill_process(exe_name: str, pid: int | None = None) -> tuple[bool, str]:
        # Prefer targeting by PID to avoid killing unrelated processes with the same name
        args = ["taskkill", "/F", "/PID", str(pid)] if pid is not None else ["taskkill", "/F", "/IM", exe_name]
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return True, "Terminated"
            return False, result.stderr.strip() or "Not found or already closed"
        except (subprocess.TimeoutExpired, OSError) as e:
            return False, str(e)

    @staticmethod
    def flush_dns() -> tuple[bool, str]:
        try:
            result = subprocess.run(
                ["ipconfig", "/flushdns"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return True, "DNS cache flushed"
            return False, result.stderr.strip() or "Failed"
        except (subprocess.TimeoutExpired, OSError) as e:
            return False, str(e)

    @staticmethod
    def _enable_privilege(name: str) -> bool:
        """Enable a named privilege in the current process token."""
        TOKEN_ADJUST_PRIVILEGES = 0x0020
        TOKEN_QUERY = 0x0008
        SE_PRIVILEGE_ENABLED = 0x00000002
        # Use the pseudo-handle constant directly — avoids ctypes restype truncation
        CURRENT_PROCESS = ctypes.wintypes.HANDLE(-1)

        class LUID(ctypes.Structure):
            _fields_ = [
                ("LowPart", ctypes.c_ulong),
                ("HighPart", ctypes.c_long),
            ]

        class LUID_AND_ATTRIBUTES(ctypes.Structure):
            _fields_ = [("Luid", LUID), ("Attributes", ctypes.c_ulong)]

        class TOKEN_PRIVILEGES(ctypes.Structure):
            _fields_ = [
                ("PrivilegeCount", ctypes.c_ulong),
                ("Privileges", LUID_AND_ATTRIBUTES * 1),
            ]

        h_token = ctypes.wintypes.HANDLE()
        if not ctypes.windll.advapi32.OpenProcessToken(
            CURRENT_PROCESS,
            TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
            ctypes.byref(h_token),
        ):
            return False

        luid = LUID()
        if not ctypes.windll.advapi32.LookupPrivilegeValueW(None, name, ctypes.byref(luid)):
            ctypes.windll.kernel32.CloseHandle(h_token)
            return False

        tp = TOKEN_PRIVILEGES()
        tp.PrivilegeCount = 1
        tp.Privileges[0].Luid = luid
        tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED

        ctypes.windll.advapi32.AdjustTokenPrivileges(
            h_token, False, ctypes.byref(tp), ctypes.sizeof(tp), None, None
        )
        err = ctypes.windll.kernel32.GetLastError()
        ctypes.windll.kernel32.CloseHandle(h_token)
        return err == 0

    @staticmethod
    def clear_standby_memory() -> tuple[bool, str]:
        # Requires SeProfileSingleProcessPrivilege — enable it before calling
        for priv in ("SeProfileSingleProcessPrivilege", "SeIncreaseQuotaPrivilege"):
            if not CleanerEngine._enable_privilege(priv):
                return False, f"Could not enable {priv} — run as administrator"
        # SystemMemoryListInformation = 80, MemoryPurgeStandbyList = 4
        cmd = ctypes.c_uint(4)
        status = ctypes.windll.ntdll.NtSetSystemInformation(
            80, ctypes.byref(cmd), ctypes.sizeof(cmd)
        )
        if status == 0:
            return True, "Standby list purged"
        return False, f"NTSTATUS 0x{status & 0xFFFFFFFF:08X}"


# =============================================================================
# WizardApp — UI and step orchestration
# =============================================================================

class WizardApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(f"SC Performance Tool v{VERSION}")
        self.root.resizable(True, True)

        self.is_admin = bool(ctypes.windll.shell32.IsUserAnAdmin())

        try:
            self.local_appdata = Path(os.environ["LOCALAPPDATA"])
            self.program_data = Path(os.environ["PROGRAMDATA"])
            self.windir = Path(os.environ["WINDIR"])
            self.temp_dir = Path(os.environ["TEMP"])
        except KeyError as e:
            messagebox.showerror("Error", f"Missing environment variable: {e}")
            root.destroy()
            return

        self.analyzer = Analyzer(
            self.local_appdata, self.program_data, self.windir, self.temp_dir
        )
        self.cleaner = CleanerEngine()

        self.report: dict = {}
        self.clean_vars: dict[str, tk.BooleanVar] = {}
        self.current_step = STEP_ANALYSIS
        self.analysis_done = False
        self.cleaning_running = False

        self.current_theme = "Dark"
        self.theme_colors = THEMES["Dark"]
        self.style = ttk.Style(self.root)

        self._build_chrome()
        self._build_all_steps()
        self._set_icon()
        self._apply_theme("Dark")
        self._center_window(780, 700)
        self._show_step(STEP_ANALYSIS)
        self._start_analysis()
        self._check_for_updates_async()

    # -------------------------------------------------------------------------
    # Window chrome — step indicator, content area, nav bar
    # -------------------------------------------------------------------------

    def _center_window(self, w: int, h: int) -> None:
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    def _build_chrome(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        # Step indicator bar — progress display only, not interactive
        bar = ttk.Frame(self.root, style="Bar.TFrame", padding="10 10 10 0")
        bar.grid(row=0, column=0, sticky="ew")
        bar.columnconfigure(list(range(4)), weight=1)

        self.step_lbl: list[ttk.Label] = []
        self.step_indicators: list[tk.Frame] = []
        for i, text in enumerate(STEP_LABELS):
            cell = ttk.Frame(bar, style="Bar.TFrame")
            cell.grid(row=0, column=i, sticky="ew", padx=2, pady=(0, 4))
            lbl = ttk.Label(cell, text=text, anchor="center",
                            font=("Segoe UI", 10), style="Bar.TLabel")
            lbl.pack(fill="x")
            indicator = tk.Frame(cell, height=3)
            indicator.pack(fill="x")
            self.step_lbl.append(lbl)
            self.step_indicators.append(indicator)

        self.rescan_btn = ttk.Button(bar, text="↺ Re-scan", command=self._rerun_scan,
                                     style="Bar.TButton")
        self.rescan_btn.grid(row=0, column=4, sticky="e", padx=(8, 0))

        # Content area — all step frames stack here
        self.content = ttk.Frame(self.root)
        self.content.grid(row=1, column=0, sticky="nsew")
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)

        # Nav bar — Back | version (centred) | theme toggle | Next
        nav = ttk.Frame(self.root, style="Bar.TFrame", padding="10 4 10 10")
        nav.grid(row=2, column=0, sticky="ew")
        nav.columnconfigure(1, weight=1)

        self.back_btn = ttk.Button(nav, text="← Back", command=self._go_back,
                                   state="disabled", style="Bar.TButton")
        self.back_btn.grid(row=0, column=0)

        self.ver_lbl = ttk.Label(nav, text=f"v{VERSION}", style="Bar.TLabel")
        self.ver_lbl.grid(row=0, column=1)

        self.theme_btn = ttk.Button(nav, text="☀  Light Mode", command=self._toggle_theme,
                                    width=13, style="Bar.TButton")
        self.theme_btn.grid(row=0, column=2, padx=(0, 8))

        self.next_btn = ttk.Button(nav, text="Next →", command=self._go_next, state="disabled")
        self.next_btn.grid(row=0, column=3)

    def _show_step(self, step: int) -> None:
        self.current_step = step
        self.step_frames[step].tkraise()
        c = self.theme_colors
        for i, (lbl, indicator) in enumerate(zip(self.step_lbl, self.step_indicators)):
            if i == step:
                lbl.configure(foreground=c["step_active"], font=("Segoe UI", 10, "bold"))
                indicator.configure(bg=c["step_active"])
            elif i < step:
                lbl.configure(foreground=c["step_done"], font=("Segoe UI", 10))
                indicator.configure(bg=c["step_done"])
            else:
                lbl.configure(foreground=c["step_future"], font=("Segoe UI", 10))
                indicator.configure(bg=c["bar_bg"])
        self._update_nav()

    def _update_nav(self) -> None:
        step = self.current_step
        if step == STEP_ANALYSIS:
            self.back_btn.configure(state="disabled")
            self.next_btn.configure(
                text="Proceed to Manual →",
                state="normal" if self.analysis_done else "disabled",
                style="Primary.TButton",
            )
        elif step == STEP_MANUAL:
            self.back_btn.configure(state="normal")
            self.next_btn.configure(
                text="Proceed to Cleaning →", state="normal", style="Primary.TButton",
            )
        elif step == STEP_CLEANING:
            self.back_btn.configure(state="normal" if not self.cleaning_running else "disabled")
            self.next_btn.configure(
                text="Run Cleaning",
                state="normal" if not self.cleaning_running else "disabled",
                style="Primary.TButton",
            )
        elif step == STEP_DONE:
            self.back_btn.configure(state="disabled")
            self.next_btn.configure(text="Close", state="normal", style="Primary.TButton")

    def _toggle_theme(self) -> None:
        self._apply_theme("Light" if self.current_theme == "Dark" else "Dark")

    def _go_back(self) -> None:
        if self.current_step == STEP_MANUAL:
            self._show_step(STEP_ANALYSIS)
        elif self.current_step == STEP_CLEANING and not self.cleaning_running:
            self._show_step(STEP_MANUAL)

    def _go_next(self) -> None:
        if self.current_step == STEP_ANALYSIS:
            self._populate_manual_ui()
            self._show_step(STEP_MANUAL)
        elif self.current_step == STEP_MANUAL:
            self._populate_cleaning_ui()
            self._show_step(STEP_CLEANING)
        elif self.current_step == STEP_CLEANING:
            self._run_cleaning()
        elif self.current_step == STEP_DONE:
            self.root.destroy()

    # -------------------------------------------------------------------------
    # Step frame construction
    # -------------------------------------------------------------------------

    def _build_all_steps(self) -> None:
        self.step_frames: dict[int, ttk.Frame] = {}
        for i in range(4):
            f = ttk.Frame(self.content)
            f.grid(row=0, column=0, sticky="nsew")
            self.step_frames[i] = f
        self._build_analysis_step()
        self._build_manual_step()
        self._build_cleaning_step()
        self._build_done_step()

    def _build_analysis_step(self) -> None:
        f = self.step_frames[STEP_ANALYSIS]
        f.columnconfigure(0, weight=1)
        f.rowconfigure(1, weight=1)

        ttk.Label(f, text="System Analysis", font=("Segoe UI", 13, "bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 4)
        )

        self.analysis_inner = ttk.Frame(f, padding="8")
        self.analysis_inner.grid(row=1, column=0, sticky="nsew")
        self.analysis_inner.columnconfigure(0, weight=1)
        self.analysis_inner.rowconfigure(0, weight=1)

        self.analysis_txt = scrolledtext.ScrolledText(
            self.analysis_inner, wrap=tk.WORD, font=("Consolas", 11), state="disabled"
        )
        self.analysis_txt.grid(row=0, column=0, sticky="nsew")
        self._configure_log_tags(self.analysis_txt)

        # Scanning overlay — shown on top while scan is running
        self.scan_overlay = ttk.Frame(f)
        self.scan_overlay.grid(row=1, column=0, sticky="nsew")
        self.scan_overlay.columnconfigure(0, weight=1)
        self.scan_overlay.rowconfigure(0, weight=1)
        ttk.Label(
            self.scan_overlay,
            text="Scanning, please wait...",
            font=("Segoe UI", 50, "bold"),
            anchor="center",
        ).grid(row=0, column=0, sticky="nsew")
        self.scan_overlay.tkraise()

        self.analysis_status = ttk.Label(f, text="Scanning...", foreground="gray")
        self.analysis_status.grid(row=2, column=0, sticky="w", padx=12, pady=(0, 6))

    def _build_manual_step(self) -> None:
        f = self.step_frames[STEP_MANUAL]
        f.columnconfigure(0, weight=1)
        f.rowconfigure(2, weight=1)

        ttk.Label(f, text="Manual Actions", font=("Segoe UI", 13, "bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 2)
        )
        ttk.Label(
            f,
            text="Review these items and make any changes needed. Proceed when ready.",
            foreground="gray",
        ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 6))

        container = ttk.Frame(f, padding="8")
        container.grid(row=2, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)

        canvas = tk.Canvas(container, highlightthickness=0)
        sb = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.manual_inner = ttk.Frame(canvas)
        self.manual_inner.columnconfigure(1, weight=1)
        self.manual_inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self.manual_inner, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")
        self.manual_canvas = canvas
        self._bind_mousewheel(canvas)


    def _build_cleaning_step(self) -> None:
        f = self.step_frames[STEP_CLEANING]
        f.columnconfigure(0, weight=1)
        f.rowconfigure(2, weight=1)
        f.rowconfigure(3, weight=1)

        ttk.Label(f, text="Automated Cleaning", font=("Segoe UI", 13, "bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 4)
        )

        btn_bar = ttk.Frame(f, padding="8 0 8 4")
        btn_bar.grid(row=1, column=0, sticky="w")
        ttk.Button(
            btn_bar, text="Select All",
            command=lambda: [v.set(True) for v in self.clean_vars.values()],
        ).pack(side="left", padx=(0, 4))
        ttk.Button(
            btn_bar, text="Deselect All",
            command=lambda: [v.set(False) for v in self.clean_vars.values()],
        ).pack(side="left")

        sel = ttk.LabelFrame(f, text="Items to Clean", padding="4 0 4 4")
        sel.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 4))
        sel.columnconfigure(0, weight=1)
        sel.rowconfigure(0, weight=1)

        canvas = tk.Canvas(sel, highlightthickness=0)
        sb = ttk.Scrollbar(sel, orient="vertical", command=canvas.yview)
        self.cleaning_inner = ttk.Frame(canvas)
        self.cleaning_inner.columnconfigure(1, weight=1)
        self.cleaning_inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self.cleaning_inner, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")
        self.cleaning_canvas = canvas
        self._bind_mousewheel(canvas)

        log_frame = ttk.LabelFrame(f, text="Cleaning Log", padding="8")
        log_frame.grid(row=3, column=0, sticky="nsew", padx=8, pady=(0, 8))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.clean_txt = scrolledtext.ScrolledText(
            log_frame, wrap=tk.WORD, font=("Consolas", 11), state="disabled"
        )
        self.clean_txt.grid(row=0, column=0, sticky="nsew")
        self._configure_log_tags(self.clean_txt)
        # Placeholder — cleared when cleaning starts
        self.clean_txt.configure(state="normal")
        self.clean_txt.insert("1.0", "Cleaning log will appear here when you run cleaning.\n", "dim")
        self.clean_txt.configure(state="disabled")

    def _build_done_step(self) -> None:
        f = self.step_frames[STEP_DONE]
        f.columnconfigure(0, weight=1)
        f.rowconfigure(1, weight=1)

        ttk.Label(f, text="Complete", font=("Segoe UI", 13, "bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 4)
        )

        self.done_txt = scrolledtext.ScrolledText(
            f, wrap=tk.WORD, font=("Consolas", 11), state="disabled"
        )
        self.done_txt.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self._configure_log_tags(self.done_txt)

        ttk.Button(
            f,
            text="Restart Computer",
            command=self._do_restart,
            style="Red.TButton",
        ).grid(row=2, column=0, sticky="ew", padx=16, pady=(4, 10), ipady=8)

    # -------------------------------------------------------------------------
    # Analysis step
    # -------------------------------------------------------------------------

    def _start_analysis(self) -> None:
        threading.Thread(target=self._analysis_worker, daemon=True).start()

    def _rerun_scan(self) -> None:
        if self.cleaning_running:
            return
        self.analysis_done = False
        self.report = {}
        self.analysis_txt.configure(state="normal")
        self.analysis_txt.delete("1.0", tk.END)
        self.analysis_txt.configure(state="disabled")
        self.analysis_status.configure(text="Scanning...")
        self.scan_overlay.tkraise()
        self._show_step(STEP_ANALYSIS)
        self._start_analysis()

    def _analysis_worker(self) -> None:
        def progress(msg: str) -> None:
            self.root.after(0, lambda m=msg: self.analysis_status.configure(text=m))

        self.report = self.analyzer.run(progress)
        self.root.after(0, self._render_analysis_report)

    def _render_analysis_report(self) -> None:
        r = self.report
        log = self._make_logger(self.analysis_txt)

        log("=" * 56, "header")
        log("  SYSTEM ANALYSIS REPORT", "header")
        log(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "header")
        log("=" * 56, "header")
        log("")

        # Hero summary — total reclaimable across all cache categories
        _sc_shaders_pre = r.get("sc_shaders", [])
        _sc_installs_pre = r.get("sc_installs", {})
        _gpu_pre = r.get("gpu_caches", {})
        _reclaimable = (
            sum(s for _, _, s in _sc_shaders_pre)
            + sum(sz for _, (_, cp, sz) in _sc_installs_pre.items() if cp)
            + sum(sz for items in _gpu_pre.values() for _, _, _, sz, _ in items)
            + r.get("temp_size", 0)
            + r.get("wintemp_size", 0)
        )
        log(f"  ▶  {self._fmt(_reclaimable)} reclaimable", "hero")
        log("  Clearing these caches can reduce shader stutter and improve load times.", "info")
        log("")

        if self.is_admin:
            log("  ● Running as administrator", "good")
        else:
            log("  ○ Not administrator — standby memory clear unavailable", "warning")
        log("")

        # SC Shaders
        log("  STAR CITIZEN SHADER CACHES", "header")
        sc_shaders = r.get("sc_shaders", [])
        if sc_shaders:
            total = sum(s for _, _, s in sc_shaders)
            for name, _, size in sc_shaders:
                log(f"    {name:<42} {self._fmt(size):>10}", "warning" if size > 0 else "dim")
            log(f"    {'Total':<42} {self._fmt(total):>10}", "info")
        else:
            log("    (none found)", "dim")
        log("")

        # SC Installs
        log("  STAR CITIZEN INSTALL CACHES", "header")
        sc_installs = r.get("sc_installs", {})
        if sc_installs:
            for channel, (install_path, cache_path, cache_size) in sc_installs.items():
                log(f"    [{channel}]  {install_path}", "info")
                if cache_path:
                    log(
                        f"      data\\cache   {self._fmt(cache_size):>10}",
                        "warning" if cache_size > 0 else "good",
                    )
                else:
                    log("      data\\cache   not found", "dim")
        else:
            log("    (no installation found)", "dim")
        log("")

        # GPU Caches
        log("  GPU DRIVER CACHES", "header")
        for category, items in r.get("gpu_caches", {}).items():
            log(f"    {category}", "info")
            for _, name, path, size, _ in items:
                if path.exists():
                    log(
                        f"      {name:<28} {self._fmt(size):>10}",
                        "warning" if size > 0 else "good",
                    )
                else:
                    log(f"      {name:<28} {'not found':>10}", "dim")
        log("")

        # Temp
        log("  TEMPORARY FILES", "header")
        temp = r.get("temp_size", 0)
        wintemp = r.get("wintemp_size", 0)
        log(f"    %TEMP%              {self._fmt(temp):>10}", "warning" if temp > 0 else "good")
        log(f"    Windows\\Temp        {self._fmt(wintemp):>10}", "warning" if wintemp > 0 else "good")
        log("")

        # Memory
        log("  MEMORY", "header")
        mem = r.get("memory", {})
        total_gb = mem.get("total_gb", 0)
        avail_gb = mem.get("available_gb", 0)
        ram_tag = "good" if total_gb >= 32 else ("warning" if total_gb >= 16 else "issue")
        log(f"    Total RAM           {total_gb:.1f} GB", ram_tag)
        log(f"    Available           {avail_gb:.1f} GB", "info")
        log(
            f"    Standby clear       {'available' if self.is_admin else 'requires admin'}",
            "good" if self.is_admin else "warning",
        )
        log("")

        # Processes
        log("  RUNNING PROCESSES", "header")
        sc_procs = r.get("sc_procs", {})
        conflict_procs = r.get("conflict_procs", {})
        if sc_procs:
            for exe, (display, pid) in sc_procs.items():
                log(f"    ● {display} (PID {pid}) — must close before cleaning", "issue")
        else:
            log("    ● No Star Citizen processes running", "good")
        if conflict_procs:
            for exe, (display, pid) in conflict_procs.items():
                log(f"    ● {display} (PID {pid}) — may cause stuttering", "warning")
        else:
            log("    ● No conflicting processes detected", "good")
        log("")

        # System settings
        log("  SYSTEM SETTINGS", "header")
        hags = r.get("hags_enabled")
        if hags is True:
            log("    HAGS                Enabled", "good")
        elif hags is False:
            log("    HAGS                Disabled — recommended for modern GPUs", "warning")
        else:
            log("    HAGS                Unknown", "dim")

        plan_name, plan_guid = r.get("power_plan", ("Unknown", ""))
        if plan_guid in RECOMMENDED_POWER_GUIDS:
            log(f"    Power Plan          {plan_name}", "good")
        else:
            log(f"    Power Plan          {plan_name} — High Performance recommended", "warning")
        log("")
        log("  Analysis complete.", "info")

        self.analysis_done = True
        self.analysis_status.configure(text="Analysis complete.")
        self.analysis_txt.see("1.0")
        self.analysis_inner.tkraise()
        self._update_nav()

    # -------------------------------------------------------------------------
    # Manual step
    # -------------------------------------------------------------------------

    def _populate_manual_ui(self) -> None:
        for w in self.manual_inner.winfo_children():
            w.destroy()

        r = self.report
        row = [0]

        def add_item(
            name: str,
            status: str,
            detail: str,
            instruction: str,
            action: tuple[str, object] | None = None,
        ) -> None:
            i = row[0]
            c = self.theme_colors
            color = {
                "good": c["color_good"],
                "warning": c["color_warn"],
                "issue": c["color_issue"],
            }.get(status, c["dim_fg"])
            status_text = {"good": "● OK", "warning": "● !", "issue": "● ✕"}.get(status, "●  ?")
            ttk.Label(
                self.manual_inner, text=status_text, foreground=color,
                font=("Segoe UI", 9, "bold"), anchor="center",
            ).grid(row=i, column=0, sticky="nw", padx=(10, 6), pady=(8, 0))

            right = ttk.Frame(self.manual_inner)
            right.grid(row=i, column=1, sticky="ew", padx=(0, 10), pady=(6, 0))
            right.columnconfigure(0, weight=1)

            ttk.Label(right, text=name, font=("Segoe UI", 10, "bold")).grid(
                row=0, column=0, sticky="w"
            )
            ttk.Label(
                right, text=detail, foreground=self.theme_colors["detail_fg"],
                wraplength=580, justify="left",
            ).grid(row=1, column=0, sticky="w")
            next_row = 2
            if instruction:
                ttk.Label(
                    right,
                    text=f"→ {instruction}",
                    foreground=self.theme_colors["accent"],
                    wraplength=580,
                    justify="left",
                ).grid(row=next_row, column=0, sticky="w")
                next_row += 1
            if action:
                btn_text, btn_cmd = action
                ttk.Button(right, text=btn_text, command=btn_cmd).grid(
                    row=next_row, column=0, sticky="w", pady=(4, 0)
                )

            ttk.Separator(self.manual_inner, orient="horizontal").grid(
                row=i + 1, column=0, columnspan=2, sticky="ew", padx=8, pady=(6, 0)
            )
            row[0] += 2

        # HAGS
        hags = r.get("hags_enabled")
        if hags is True:
            add_item(
                "Hardware-Accelerated GPU Scheduling (HAGS)",
                "good",
                "Enabled. Improves frame pacing and reduces GPU latency in SC.",
                "",
                action=(
                    "Open Graphics Settings",
                    lambda: subprocess.Popen(
                        ["explorer.exe", "ms-settings:display-advancedgraphics"]
                    ),
                ),
            )
        elif hags is False:
            add_item(
                "Hardware-Accelerated GPU Scheduling (HAGS)",
                "warning",
                "Disabled. Recommended for RTX 30/40 and RX 6000+ series GPUs.",
                "Press Win + I → System → Display → Graphics"
                " → Hardware-accelerated GPU scheduling → On",
                action=(
                    "Open Graphics Settings",
                    lambda: subprocess.Popen(
                        ["explorer.exe", "ms-settings:display-advancedgraphics"]
                    ),
                ),
            )
        else:
            add_item(
                "Hardware-Accelerated GPU Scheduling (HAGS)",
                "info",
                "Status could not be determined.",
                "Press Win + I → System → Display → Graphics → Hardware-accelerated GPU scheduling",
                action=(
                    "Open Graphics Settings",
                    lambda: subprocess.Popen(
                        ["explorer.exe", "ms-settings:display-advancedgraphics"]
                    ),
                ),
            )

        # Power plan
        plan_name, plan_guid = r.get("power_plan", ("Unknown", ""))
        if plan_guid in RECOMMENDED_POWER_GUIDS:
            add_item(
                "Power Plan",
                "good",
                f"Currently: {plan_name}. No action needed.",
                "",
                action=("Open Power Options", lambda: subprocess.Popen(["control", "powercfg.cpl"])),
            )
        else:
            add_item(
                "Power Plan",
                "warning",
                f"Currently: {plan_name}. "
                "Balanced plan throttles CPU frequency, causing frame spikes in SC.",
                "Control Panel → Power Options → High Performance",
                action=(
                    "Open Power Options",
                    lambda: subprocess.Popen(["control", "powercfg.cpl"]),
                ),
            )

        # Conflicting processes
        conflict_procs = r.get("conflict_procs", {})
        if conflict_procs:
            for exe, (display, pid) in conflict_procs.items():
                settings_entry = CONFLICT_SETTINGS.get(exe)
                action = None
                if settings_entry:
                    btn_label, uri = settings_entry
                    action = (btn_label, lambda u=uri: subprocess.Popen(["explorer.exe", u]))
                add_item(
                    f"Conflicting Process: {display}",
                    "warning",
                    f"Running (PID {pid}). "
                    "Known to cause stuttering or hook conflicts with Star Citizen.",
                    CONFLICT_INSTRUCTIONS.get(exe, "Close this application before playing."),
                    action=action,
                )
        else:
            add_item(
                "Conflicting Processes",
                "good",
                "No known conflicting processes detected.",
                "",
            )

        # Admin
        if self.is_admin:
            add_item(
                "Administrator Privileges",
                "good",
                "Running as administrator. All cleaning features available.",
                "",
            )
        else:
            add_item(
                "Administrator Privileges",
                "warning",
                "Not running as administrator. Standby memory clear will be skipped.",
                "Right-click the .exe → Run as administrator.",
            )

    # -------------------------------------------------------------------------
    # Cleaning step
    # -------------------------------------------------------------------------

    def _populate_cleaning_ui(self) -> None:
        for w in self.cleaning_inner.winfo_children():
            w.destroy()
        self.clean_vars = {}

        r = self.report
        row = [0]

        def section(title: str) -> None:
            ttk.Label(
                self.cleaning_inner,
                text=title,
                font=("Segoe UI", 10, "bold"),
                foreground=self.theme_colors["section_fg"],
            ).grid(row=row[0], column=0, columnspan=2, sticky="w", padx=(10, 0), pady=(8, 2))
            row[0] += 1

        def item(key: str, label: str, size: int, select: bool) -> None:
            var = tk.BooleanVar(value=select)
            self.clean_vars[key] = var
            ttk.Checkbutton(self.cleaning_inner, text=label, variable=var).grid(
                row=row[0], column=0, sticky="w", padx=(18, 4)
            )
            ttk.Label(
                self.cleaning_inner,
                text=self._fmt(size) if size >= 0 else "",
                foreground=self.theme_colors["info_fg"],
            ).grid(row=row[0], column=1, sticky="w")
            row[0] += 1

        # Processes to close
        sc_procs = r.get("sc_procs", {})
        if sc_procs:
            section("Processes to Close")
            for exe, (display, pid) in sc_procs.items():
                item(f"kill_{exe}", f"Kill {display} (PID {pid})", -1, select=True)

        # SC Shader caches
        sc_shaders = r.get("sc_shaders", [])
        if sc_shaders:
            section("Star Citizen Shader Caches")
            for name, _, size in sc_shaders:
                item(f"sc_shader_{name}", name, size, select=size > 0)

        # SC Install caches
        sc_installs = r.get("sc_installs", {})
        for channel, (_, cache_path, cache_size) in sc_installs.items():
            if cache_path:
                section(f"Star Citizen {channel} — Install Cache")
                item(f"sc_data_{channel}", "data\\cache", cache_size, select=cache_size > 0)

        # GPU caches
        for category, items_list in r.get("gpu_caches", {}).items():
            existing = [(k, n, p, s, rc) for k, n, p, s, rc in items_list if p.exists()]
            if existing:
                section(f"GPU Driver Caches — {category}")
                for key, name, _, size, _ in existing:
                    item(f"gpu_{key}", name, size, select=size > 0)

        # Temp files
        temp = r.get("temp_size", 0)
        wintemp = r.get("wintemp_size", 0)
        section("Temporary Files")
        item("temp_user", "%TEMP%", temp, select=temp > 0)
        item("temp_win", "Windows\\Temp", wintemp, select=wintemp > 0)

        # System operations
        section("System")
        item("dns_flush", "Flush DNS Cache", -1, select=True)
        if self.is_admin:
            item("standby_mem", "Clear Standby Memory List", -1, select=True)
        else:
            ttk.Label(
                self.cleaning_inner,
                text="  Clear Standby Memory (requires administrator)",
                foreground=self.theme_colors["disabled_fg"],
            ).grid(row=row[0], column=0, columnspan=2, sticky="w", padx=(18, 4))
            row[0] += 1

    def _clear_clean_log(self) -> None:
        self.clean_txt.configure(state="normal")
        self.clean_txt.delete("1.0", tk.END)
        self.clean_txt.configure(state="disabled")

    def _run_cleaning(self) -> None:
        # Prompt per SC process before anything else runs
        sc_procs = self.report.get("sc_procs", {})
        for key, var in list(self.clean_vars.items()):
            if not key.startswith("kill_") or not var.get():
                continue
            exe = key.removeprefix("kill_")
            if exe not in sc_procs:
                continue
            display, pid = sc_procs[exe]
            answer = messagebox.askyesnocancel(
                "Kill Process",
                f"{display} is running (PID {pid}).\n\n"
                f"Kill it before cleaning?\n\n"
                f"Yes  = kill it now\n"
                f"No   = leave it running\n"
                f"Cancel = abort cleaning",
                icon="warning",
            )
            if answer is None:
                return
            if not answer:
                var.set(False)

        self.cleaning_running = True
        self._update_nav()
        threading.Thread(target=self._cleaning_worker, daemon=True).start()

    def _cleaning_worker(self) -> None:
        self.root.after(0, self._clear_clean_log)
        r = self.report
        stats: dict = {"ok": 0, "fail": 0, "results": []}

        def log(text: str, tag: str = "") -> None:
            self.root.after(0, lambda t=text, g=tag: self._append(self.clean_txt, t, g))

        def selected(key: str) -> bool:
            v = self.clean_vars.get(key)
            return v.get() if v else False

        def run_op(label: str, success: bool, msg: str) -> None:
            prefix = "[OK]  " if success else "[FAIL]"
            log(f"  {prefix} {label} — {msg}", "ok" if success else "fail")
            stats["ok" if success else "fail"] += 1
            stats["results"].append((label, success, msg))

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log("=" * 52, "header")
        log(f"  CLEANING — {ts}", "header")
        log("=" * 52, "header")
        log("")

        # Kill processes
        for key, var in self.clean_vars.items():
            if not key.startswith("kill_") or not var.get():
                continue
            exe = key.removeprefix("kill_")
            procs = r.get("sc_procs", {})
            if exe in procs:
                display, pid = procs[exe]
                log(f"  Killing {display}...", "info")
                run_op(display, *self.cleaner.kill_process(exe, pid))
        log("")

        # SC Shader caches
        shown = False
        for name, path, _ in r.get("sc_shaders", []):
            if not selected(f"sc_shader_{name}"):
                continue
            if not shown:
                log("  [SC SHADER CACHES]", "header")
                shown = True
            log(f"  Clearing {name}...", "info")
            run_op(name, *self.cleaner.clear_folder(path, recreate=False))
        if shown:
            log("")

        # SC Install caches
        for channel, (_, cache_path, _) in r.get("sc_installs", {}).items():
            if cache_path and selected(f"sc_data_{channel}"):
                log(f"  [SC {channel} INSTALL CACHE]", "header")
                log("  Clearing data\\cache...", "info")
                run_op(f"{channel} data\\cache", *self.cleaner.clear_folder(cache_path, recreate=True))
                log("")

        # GPU caches
        for category, items_list in r.get("gpu_caches", {}).items():
            shown = False
            for key, name, path, _, recreate in items_list:
                if not selected(f"gpu_{key}"):
                    continue
                if not shown:
                    log(f"  [{category.upper()}]", "header")
                    shown = True
                log(f"  Clearing {name}...", "info")
                run_op(name, *self.cleaner.clear_folder(path, recreate=recreate))
            if shown:
                log("")

        # Temp files
        if selected("temp_user") or selected("temp_win"):
            log("  [TEMP FILES]", "header")
            if selected("temp_user"):
                log("  Clearing %TEMP%...", "info")
                run_op("%TEMP%", *self.cleaner.clear_folder(self.temp_dir, recreate=True))
            if selected("temp_win"):
                log("  Clearing Windows\\Temp...", "info")
                run_op("Windows\\Temp", *self.cleaner.clear_folder(self.windir / "Temp", recreate=True))
            log("")

        # DNS flush
        if selected("dns_flush"):
            log("  [DNS]", "header")
            log("  Flushing DNS cache...", "info")
            run_op("DNS flush", *self.cleaner.flush_dns())
            log("")

        # Standby memory
        if selected("standby_mem") and self.is_admin:
            log("  [MEMORY]", "header")
            log("  Clearing standby memory list...", "info")
            run_op("Standby memory", *self.cleaner.clear_standby_memory())
            log("")

        log("=" * 52, "header")
        log("  SUMMARY", "header")
        log("=" * 52, "header")
        log(f"  Completed:  {stats['ok']}", "ok")
        log(f"  Failed:     {stats['fail']}", "fail" if stats["fail"] else "info")
        log("")
        log("  First SC launch will recompile shaders — this is normal.", "info")

        self.root.after(0, lambda: self._on_cleaning_done(stats))

    def _on_cleaning_done(self, stats: dict) -> None:
        self.cleaning_running = False
        self._render_done(stats)
        self._show_step(STEP_DONE)

    # -------------------------------------------------------------------------
    # Done step
    # -------------------------------------------------------------------------

    def _render_done(self, stats: dict) -> None:
        log = self._make_logger(self.done_txt)
        log("=" * 52, "header")
        log("  CLEANING COMPLETE", "header")
        log("=" * 52, "header")
        log("")

        results: list[tuple[str, bool, str]] = stats.get("results", [])
        ok_items = [(l, m) for l, s, m in results if s]
        fail_items = [(l, m) for l, s, m in results if not s]

        if ok_items:
            log(f"  COMPLETED ({len(ok_items)})", "ok")
            for label, msg in ok_items:
                log(f"    ✔  {label} — {msg}", "ok")
            log("")

        if fail_items:
            log(f"  FAILED ({len(fail_items)})", "fail")
            for label, msg in fail_items:
                log(f"    ✘  {label} — {msg}", "fail")
            log("")

        if not results:
            log("  No operations were run.", "info")
            log("")

        has_scheduled = any("scheduled for reboot" in m for _, _, m in results)
        if has_scheduled:
            log("=" * 52, "header")
            log("  REBOOT REQUIRED", "warning")
            log("=" * 52, "header")
            log("  Some locked files were scheduled for cleanup at next restart.", "warning")
            log("  Use the button below to restart now.", "warning")
        elif results:
            log("  A restart is recommended for all changes to take full effect.", "info")

    def _do_restart(self) -> None:
        if not messagebox.askyesno(
            "Restart?",
            "Restart the computer now?",
            icon="question",
        ):
            return
        try:
            subprocess.run(
                [
                    "shutdown", "/r", "/t", "10",
                    "/c", "SC Performance Tool — post-clean restart.",
                ],
                check=True,
            )
        except subprocess.CalledProcessError:
            messagebox.showerror("Error", "Could not initiate restart.\nRun as administrator.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not restart:\n{e}")

    # -------------------------------------------------------------------------
    # Shared helpers
    # -------------------------------------------------------------------------

    def _bind_mousewheel(self, canvas: tk.Canvas) -> None:
        """Enable mousewheel scrolling anywhere over the canvas and its children."""
        def scroll(event: tk.Event) -> None:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<Enter>", lambda e: self.root.bind_all("<MouseWheel>", scroll))
        canvas.bind("<Leave>", lambda e: self.root.unbind_all("<MouseWheel>"))

    def _configure_log_tags(self, widget: scrolledtext.ScrolledText) -> None:
        c = self.theme_colors
        widget.tag_configure("good", foreground=c["color_good"])
        widget.tag_configure("warning", foreground=c["color_warn"])
        widget.tag_configure("issue", foreground=c["color_issue"])
        widget.tag_configure("header", foreground=c["tag_header"], font=("Consolas", 11, "bold"))
        widget.tag_configure("info", foreground=c["tag_info"])
        widget.tag_configure("dim", foreground=c["tag_dim"])
        widget.tag_configure("ok", foreground=c["color_good"])
        widget.tag_configure("fail", foreground=c["color_issue"])
        widget.tag_configure("hero", foreground=c["accent"], font=("Consolas", 14, "bold"))

    # -------------------------------------------------------------------------
    # Theme and icon
    # -------------------------------------------------------------------------

    def _set_icon(self) -> None:
        self._icon_img = self._make_magnifier_icon()
        self.root.iconphoto(True, self._icon_img)

    @staticmethod
    def _make_magnifier_icon(size: int = 32) -> tk.PhotoImage:
        img = tk.PhotoImage(width=size, height=size)
        cx, cy = 13, 13
        r_outer, r_inner = 10, 7
        bg = "#d0d0d0"
        ring = "#202020"
        lens = "#b8d4f0"
        handle = "#303030"

        rows: list[list[str]] = []
        for y in range(size):
            row: list[str] = []
            for x in range(size):
                dx, dy = x - cx, y - cy
                dist2 = dx * dx + dy * dy
                on_handle = (
                    20 <= x <= 28
                    and 20 <= y <= 28
                    and abs((x - 20) - (y - 20)) <= 1
                )
                if dist2 <= r_inner * r_inner:
                    row.append(lens)
                elif dist2 <= r_outer * r_outer:
                    row.append(ring)
                elif on_handle:
                    row.append(handle)
                else:
                    row.append(bg)
            rows.append(row)

        for y, row in enumerate(rows):
            img.put("{" + " ".join(row) + "}", to=(0, y))

        return img

    def _apply_theme(self, theme_name: str) -> None:
        self.current_theme = theme_name
        self.theme_colors = THEMES[theme_name]
        c = self.theme_colors

        self.style.theme_use("clam")
        self.style.configure(".", background=c["bg"], foreground=c["fg"])
        self.style.configure("TFrame", background=c["bg"])
        self.style.configure("TLabel", background=c["bg"], foreground=c["fg"])

        # Bar styles — step indicator bar and nav bar share a tinted background
        self.style.configure("Bar.TFrame", background=c["bar_bg"])
        self.style.configure("Bar.TLabel", background=c["bar_bg"], foreground=c["fg"])
        self.style.configure(
            "Bar.TButton",
            background=c["bar_bg"], foreground=c["fg"],
            bordercolor=c["step_done"],
            focuscolor=c["accent"], focusthickness=2,
        )
        self.style.map(
            "Bar.TButton",
            background=[("active", c["bg"]), ("pressed", c["step_done"]),
                        ("disabled", c["bar_bg"])],
            foreground=[("disabled", c["dim_fg"])],
        )
        self.style.configure(
            "TButton",
            background=c["bg"], foreground=c["fg"],
            bordercolor=c["step_done"],
            focuscolor=c["accent"], focusthickness=2,
        )
        self.style.map(
            "TButton",
            background=[("active", c["canvas_bg"]), ("pressed", c["step_done"])],
        )
        self.style.configure(
            "Primary.TButton",
            background=c["btn_primary"], foreground="#ffffff",
            bordercolor=c["btn_primary"],
            font=("Segoe UI", 10, "bold"),
            focuscolor="#ffffff", focusthickness=2,
            padding=(12, 4),
        )
        self.style.map(
            "Primary.TButton",
            background=[("active", c["accent"]), ("pressed", c["step_done"]),
                        ("disabled", c["step_future"])],
            foreground=[("active", "#ffffff"), ("pressed", "#ffffff"),
                        ("disabled", c["bg"])],
        )
        self.style.configure(
            "TCheckbutton", background=c["bg"], foreground=c["fg"],
            focuscolor=c["accent"], focusthickness=2,
        )
        self.style.map(
            "TCheckbutton",
            background=[("active", c["bg"])],
            indicatorcolor=[("selected", c["accent"]), ("!selected", c["step_done"])],
        )
        self.style.configure(
            "TLabelframe",
            background=c["bg"], foreground=c["fg"],
            bordercolor=c["labelframe_border"],
        )
        self.style.configure(
            "TLabelframe.Label",
            background=c["bg"], foreground=c["accent"],
            font=("Segoe UI", 9, "bold"),
        )
        self.style.configure("TSeparator", background=c["step_done"])
        self.style.configure(
            "TScrollbar",
            background=c["step_done"], troughcolor=c["canvas_bg"],
            arrowcolor=c["bg"], width=8, arrowsize=8,
        )
        self.style.map(
            "TScrollbar",
            background=[("active", c["accent"]), ("pressed", c["step_active"])],
        )
        self.style.configure(
            "TCombobox",
            fieldbackground=c["text_bg"], background=c["bg"],
            foreground=c["fg"], selectbackground=c["step_active"],
        )
        self.style.map(
            "TCombobox",
            fieldbackground=[("readonly", c["text_bg"])],
            foreground=[("readonly", c["fg"])],
        )

        self.style.configure(
            "Red.TButton",
            background="#c0392b", foreground="#ffffff",
            bordercolor="#922b21", font=("Segoe UI", 10, "bold"),
        )
        self.style.map(
            "Red.TButton",
            background=[("active", "#e74c3c"), ("pressed", "#922b21")],
            foreground=[("active", "#ffffff"), ("pressed", "#ffffff")],
        )

        self.root.configure(bg=c["bg"])

        for widget in [self.analysis_txt, self.clean_txt, self.done_txt]:
            widget.configure(
                bg=c["text_bg"], fg=c["text_fg"],
                insertbackground=c["text_insert"],
            )
            self._configure_log_tags(widget)

        self.manual_canvas.configure(bg=c["canvas_bg"])
        self.cleaning_canvas.configure(bg=c["canvas_bg"])

        self.analysis_status.configure(foreground=c["info_fg"])
        self.ver_lbl.configure(foreground=c["dim_fg"])
        self.theme_btn.configure(
            text="☀  Light Mode" if theme_name == "Dark" else "◑  Dark Mode"
        )
        self._show_step(self.current_step)

    @staticmethod
    def _make_logger(widget: scrolledtext.ScrolledText) -> collections.abc.Callable[..., None]:
        def log(text: str, tag: str = "") -> None:
            WizardApp._append(widget, text, tag)

        return log

    @staticmethod
    def _append(widget: scrolledtext.ScrolledText, text: str, tag: str = "") -> None:
        widget.configure(state="normal")
        if tag:
            widget.insert(tk.END, text + "\n", tag)
        else:
            widget.insert(tk.END, text + "\n")
        widget.see(tk.END)
        widget.configure(state="disabled")

    @staticmethod
    def _fmt(size: int) -> str:
        if size < 1024:
            return f"{size} B"
        if size < 1024**2:
            return f"{size / 1024:.1f} KB"
        if size < 1024**3:
            return f"{size / 1024**2:.1f} MB"
        return f"{size / 1024**3:.2f} GB"

    # -------------------------------------------------------------------------
    # Update check
    # -------------------------------------------------------------------------

    def _check_for_updates_async(self) -> None:
        threading.Thread(target=self._check_for_updates, daemon=True).start()

    def _check_for_updates(self) -> None:
        try:
            api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            req = urllib.request.Request(api_url, headers={"User-Agent": "SCPerfTool"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                latest = data.get("tag_name", "").lstrip("v")
                release_url = data.get("html_url", "")
                if latest and self._version_compare(latest, VERSION) > 0:
                    self.root.after(0, lambda: self._show_update(latest, release_url))
        except (urllib.error.URLError, TimeoutError):
            pass  # Network unavailable — expected, silent
        except (json.JSONDecodeError, KeyError, ValueError):
            logging.warning("Update check: unexpected response format")

    def _show_update(self, latest: str, url: str) -> None:
        # Only open URLs with safe schemes pointing to github.com
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("https", "http") or not parsed.netloc.endswith("github.com"):
            return
        self.ver_lbl.configure(
            text=f"v{VERSION} → v{latest} available",
            foreground="purple",
            cursor="hand2",
        )
        self.ver_lbl.bind("<Button-1>", lambda e: webbrowser.open(url))

    @staticmethod
    def _version_compare(v1: str, v2: str) -> int:
        def parse(v: str) -> list[int]:
            return [int(x) for x in re.split(r"[.\-]", v) if x.isdigit()]

        p1, p2 = parse(v1), parse(v2)
        length = max(len(p1), len(p2))
        p1 += [0] * (length - len(p1))
        p2 += [0] * (length - len(p2))
        for a, b in zip(p1, p2):
            if a != b:
                return 1 if a > b else -1
        return 0


def main() -> None:
    if not ctypes.windll.shell32.IsUserAnAdmin():
        if getattr(sys, "frozen", False):
            # Running as compiled exe — re-launch the exe itself elevated
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, None, None, 1)
        else:
            # Running as a script — use pythonw.exe to avoid a console window
            pythonw = sys.executable.replace("python.exe", "pythonw.exe")
            script_dir = str(Path(sys.argv[0]).resolve().parent)
            # subprocess.list2cmdline correctly escapes paths with spaces and quotes
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", pythonw,
                subprocess.list2cmdline(sys.argv),
                script_dir, 1,
            )
        return
    root = tk.Tk()
    WizardApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
