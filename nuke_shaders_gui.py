#!/usr/bin/env python3
"""
Shader Cache Nuke Script v4 - GUI Version
Clears shader caches for Star Citizen, NVIDIA, AMD, and DirectX
With dynamic Star Citizen subfolder selection and GitHub update checking
"""

import os
import shutil
import winreg
import subprocess
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from pathlib import Path
from datetime import datetime
import threading
import urllib.request
import json

# Version info
VERSION = "1.2.0"
GITHUB_REPO = "Diftic/StarCitizenShaderDeletion"


class ShaderNukeApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Shader Cache Nuke v{VERSION}")
        self.root.resizable(True, True)

        # Setup paths
        self.local_appdata = Path(os.environ.get("LOCALAPPDATA", ""))
        self.program_data = Path(os.environ.get("PROGRAMDATA", ""))
        self.sc_path = self.local_appdata / "star citizen"

        # Cache definitions for static caches (NVIDIA, AMD, DirectX)
        self.static_cache_definitions = self._build_static_cache_definitions()

        # Dynamic Star Citizen subfolders
        self.sc_subfolders = []  # List of (name, path, size_bytes)

        # Checkbox variables
        self.static_cache_vars = {}
        self.sc_cache_vars = {}  # Separate dict for dynamic SC checkboxes

        self._build_ui()
        self._scan_sc_subfolders()

        # Center window on screen
        self._center_window(700, 750)

        # Check for updates in background
        self._check_for_updates_async()

    def _build_static_cache_definitions(self) -> dict:
        """Build dictionary of static cache locations (non-SC)."""
        nvidia_local = self.local_appdata / "NVIDIA"
        amd_local = self.local_appdata / "AMD"

        # Get NV_Cache path from registry or default
        nv_cache_path = self._get_nvidia_cache_from_registry()
        if nv_cache_path is None:
            nv_cache_path = self.program_data / "NVIDIA Corporation" / "NV_Cache"

        return {
            "NVIDIA": {
                "nv_dxcache": ("DXCache", nvidia_local / "DXCache", True),
                "nv_glcache": ("GLCache", nvidia_local / "GLCache", True),
                "nv_compute": ("ComputeCache", nvidia_local / "ComputeCache", True),
                "nv_cache": ("NV_Cache (system)", nv_cache_path, True),
            },
            "AMD": {
                "amd_dxcache": ("DxCache", amd_local / "DxCache", True),
                "amd_glcache": ("GLCache", amd_local / "GLCache", True),
                "amd_vkcache": ("VkCache", amd_local / "VkCache", True),
                "amd_dx9cache": ("Dx9Cache", amd_local / "Dx9Cache", True),
            },
            "DirectX": {
                "dx_d3ds": ("D3DSCache", self.local_appdata / "D3DSCache", True),
            },
        }

    def _center_window(self, width: int, height: int):
        """Center the window on screen."""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _get_nvidia_cache_from_registry(self) -> Path | None:
        """Query registry for NVIDIA cache location."""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\NVIDIA Corporation\Global\NVCache"
            )
            value, _ = winreg.QueryValueEx(key, "NVCachePath")
            winreg.CloseKey(key)
            return Path(value)
        except (WindowsError, FileNotFoundError, OSError):
            return None

    def _get_folder_size(self, path: Path) -> int:
        """Calculate total size of a folder in bytes."""
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

    def _format_size(self, size_bytes: int) -> str:
        """Format bytes to human readable string."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

    def _scan_sc_subfolders(self):
        """Scan Star Citizen folder for subfolders and populate UI."""
        # Clear existing
        self.sc_subfolders = []
        self.sc_cache_vars = {}

        # Clear the SC frame contents
        for widget in self.sc_inner_frame.winfo_children():
            widget.destroy()

        if not self.sc_path.exists():
            ttk.Label(self.sc_inner_frame, text="(folder not found)", foreground="gray").grid(row=0, column=0)
            return

        # Scan for subfolders
        try:
            subfolders = [f for f in self.sc_path.iterdir() if f.is_dir()]
        except (PermissionError, OSError):
            ttk.Label(self.sc_inner_frame, text="(access denied)", foreground="red").grid(row=0, column=0)
            return

        if not subfolders:
            ttk.Label(self.sc_inner_frame, text="(empty)", foreground="gray").grid(row=0, column=0)
            return

        # Sort: shader folders first (contain version numbers), then others
        def sort_key(p):
            name = p.name.lower()
            # Shader folders typically start with "starcitizen_"
            if name.startswith("starcitizen_"):
                return (0, name)
            elif name == "crashes":
                return (2, name)  # Crashes last
            else:
                return (1, name)

        subfolders.sort(key=sort_key)

        # Create checkboxes for each subfolder
        row = 0
        for folder_path in subfolders:
            folder_name = folder_path.name
            folder_size = self._get_folder_size(folder_path)
            self.sc_subfolders.append((folder_name, folder_path, folder_size))

            # Create checkbox variable - default ON for shader folders, OFF for crashes
            is_shader = folder_name.lower().startswith("starcitizen_")
            var = tk.BooleanVar(value=is_shader)
            self.sc_cache_vars[folder_name] = var

            # Checkbox
            cb = ttk.Checkbutton(self.sc_inner_frame, text=folder_name, variable=var)
            cb.grid(row=row, column=0, sticky="w")

            # Size label
            size_str = self._format_size(folder_size)
            size_label = ttk.Label(self.sc_inner_frame, text=size_str, foreground="gray")
            size_label.grid(row=row, column=1, sticky="e", padx=(10, 5))

            # Existence indicator (always green since we scanned existing folders)
            indicator = ttk.Label(self.sc_inner_frame, text="●", foreground="green")
            indicator.grid(row=row, column=2, sticky="e")

            row += 1

        # Update total size label
        total_size = sum(s[2] for s in self.sc_subfolders)
        self.sc_total_label.config(text=f"Total: {self._format_size(total_size)}")

    def _build_ui(self):
        """Build the user interface."""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=0)  # SC section
        main_frame.rowconfigure(3, weight=1)  # Log area expands

        # === STAR CITIZEN SECTION (Dynamic) ===
        sc_frame = ttk.LabelFrame(main_frame, text="Star Citizen Caches", padding="10")
        sc_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        sc_frame.columnconfigure(0, weight=1)

        # SC controls row
        sc_controls = ttk.Frame(sc_frame)
        sc_controls.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        ttk.Button(sc_controls, text="Select All SC", command=self._select_all_sc).pack(side="left", padx=(0, 5))
        ttk.Button(sc_controls, text="Deselect All SC", command=self._deselect_all_sc).pack(side="left", padx=(0, 5))
        ttk.Button(sc_controls, text="Shaders Only", command=self._select_sc_shaders_only).pack(side="left", padx=(0, 5))
        ttk.Button(sc_controls, text="Refresh", command=self._scan_sc_subfolders).pack(side="left", padx=(0, 5))

        self.sc_total_label = ttk.Label(sc_controls, text="Total: --", foreground="blue")
        self.sc_total_label.pack(side="right")

        # Scrollable frame for SC subfolders
        sc_canvas = tk.Canvas(sc_frame, height=120)
        sc_scrollbar = ttk.Scrollbar(sc_frame, orient="vertical", command=sc_canvas.yview)
        self.sc_inner_frame = ttk.Frame(sc_canvas)

        self.sc_inner_frame.bind(
            "<Configure>",
            lambda e: sc_canvas.configure(scrollregion=sc_canvas.bbox("all"))
        )

        sc_canvas.create_window((0, 0), window=self.sc_inner_frame, anchor="nw")
        sc_canvas.configure(yscrollcommand=sc_scrollbar.set)

        sc_canvas.grid(row=1, column=0, sticky="ew")
        sc_scrollbar.grid(row=1, column=1, sticky="ns")

        # Configure columns in inner frame
        self.sc_inner_frame.columnconfigure(0, weight=1)

        # === STATIC CACHES SECTION ===
        static_frame = ttk.LabelFrame(main_frame, text="GPU Driver Caches", padding="10")
        static_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        static_frame.columnconfigure((0, 1, 2), weight=1)

        col = 0
        for category, caches in self.static_cache_definitions.items():
            # Category frame
            cat_frame = ttk.LabelFrame(static_frame, text=category, padding="5")
            cat_frame.grid(row=0, column=col, sticky="nsew", padx=5)

            row = 0
            for cache_id, (name, path, _) in caches.items():
                var = tk.BooleanVar(value=True)
                self.static_cache_vars[cache_id] = var

                # Check if path exists
                exists = path.exists()
                cb = ttk.Checkbutton(cat_frame, text=name, variable=var)
                cb.grid(row=row, column=0, sticky="w")

                # Existence indicator
                if exists:
                    indicator = ttk.Label(cat_frame, text="●", foreground="green")
                else:
                    indicator = ttk.Label(cat_frame, text="○", foreground="gray")
                indicator.grid(row=row, column=1, sticky="e", padx=(5, 0))

                row += 1

            col += 1

        # === BUTTON FRAME ===
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        button_frame.columnconfigure((0, 1, 2, 3), weight=1)

        ttk.Button(button_frame, text="Select All", command=self._select_all).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Deselect All", command=self._deselect_all).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="Select Existing Only", command=self._select_existing).grid(row=0, column=2, padx=5)

        self.nuke_button = ttk.Button(button_frame, text="NUKE SELECTED", command=self._run_nuke)
        self.nuke_button.grid(row=0, column=3, padx=5)

        # === LOG FRAME ===
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="10")
        log_frame.grid(row=3, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, font=("Consolas", 10))
        self.log_text.grid(row=0, column=0, sticky="nsew")

        # Configure log text tags for coloring
        self.log_text.tag_configure("ok", foreground="green")
        self.log_text.tag_configure("skip", foreground="orange")
        self.log_text.tag_configure("fail", foreground="red")
        self.log_text.tag_configure("header", foreground="blue", font=("Consolas", 10, "bold"))
        self.log_text.tag_configure("info", foreground="gray")
        self.log_text.tag_configure("update", foreground="purple", font=("Consolas", 10, "bold"))

        # === FOOTER ===
        footer_frame = ttk.Frame(main_frame)
        footer_frame.grid(row=4, column=0, sticky="ew", pady=(5, 0))

        ttk.Label(footer_frame, text="● = Exists", foreground="green").pack(side="left", padx=(0, 15))
        ttk.Label(footer_frame, text="○ = Not found", foreground="gray").pack(side="left")

        self.version_label = ttk.Label(footer_frame, text=f"v{VERSION}", foreground="gray")
        self.version_label.pack(side="right")

        # Initial log message
        self._log(f"Shader Cache Nuke v{VERSION} ready.", "info")
        self._log("Green dots indicate caches that exist on your system.", "info")
        self._log("Select caches to clear and click NUKE SELECTED.", "info")
        self._log("", "info")

    def _log(self, message: str, tag: str = None):
        """Add message to log with optional tag for coloring."""
        self.log_text.configure(state="normal")
        if tag:
            self.log_text.insert(tk.END, message + "\n", tag)
        else:
            self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def _clear_log(self):
        """Clear the log."""
        self.log_text.configure(state="normal")
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state="disabled")

    # === Selection methods ===

    def _select_all(self):
        """Select all checkboxes."""
        self._select_all_sc()
        for var in self.static_cache_vars.values():
            var.set(True)

    def _deselect_all(self):
        """Deselect all checkboxes."""
        self._deselect_all_sc()
        for var in self.static_cache_vars.values():
            var.set(False)

    def _select_existing(self):
        """Select only caches that exist."""
        # SC folders are all existing (we scanned them)
        for var in self.sc_cache_vars.values():
            var.set(True)

        # Static caches - check existence
        for category, caches in self.static_cache_definitions.items():
            for cache_id, (name, path, _) in caches.items():
                self.static_cache_vars[cache_id].set(path.exists())

    def _select_all_sc(self):
        """Select all Star Citizen subfolders."""
        for var in self.sc_cache_vars.values():
            var.set(True)

    def _deselect_all_sc(self):
        """Deselect all Star Citizen subfolders."""
        for var in self.sc_cache_vars.values():
            var.set(False)

    def _select_sc_shaders_only(self):
        """Select only shader folders in Star Citizen (not crashes, etc.)."""
        for name, var in self.sc_cache_vars.items():
            is_shader = name.lower().startswith("starcitizen_")
            var.set(is_shader)

    # === Nuke operations ===

    def _clear_folder(self, path: Path, recreate: bool = True) -> tuple[bool, str]:
        """
        Clear a folder's contents.
        Returns (success, message).
        """
        if not path.exists():
            return False, "Not found"

        deleted = 0
        skipped = 0
        bytes_freed = 0

        # Walk through all files and try to delete each
        for root, dirs, files in os.walk(path, topdown=False):
            for name in files:
                file_path = Path(root) / name
                try:
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    deleted += 1
                    bytes_freed += file_size
                except (PermissionError, OSError):
                    skipped += 1

            for name in dirs:
                dir_path = Path(root) / name
                try:
                    dir_path.rmdir()
                except (PermissionError, OSError):
                    pass

        # Try to remove the root folder itself
        try:
            if path.exists() and not any(path.iterdir()):
                path.rmdir()
                if recreate:
                    path.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError):
            pass

        mb_freed = bytes_freed / (1024 * 1024)

        if deleted == 0 and skipped > 0:
            return False, f"All {skipped} files locked"
        elif skipped > 0:
            return True, f"Cleared {deleted} files ({mb_freed:.1f} MB), {skipped} locked"
        else:
            return True, f"Cleared {deleted} files ({mb_freed:.1f} MB)"

    def _run_nuke(self):
        """Execute the nuke operation in a separate thread."""
        confirm = messagebox.askokcancel(
            "Confirm Shader Cache Nuke",
            "BEFORE PROCEEDING:\n\n"
            "• Close all games\n"
            "• Close rendering software (Blender, Premiere, etc.)\n"
            "• Close any GPU-intensive applications\n\n"
            "After the shader nuke completes, it is advised to\n"
            "restart your computer for changes to take full effect.\n\n"
            "Continue with shader cache deletion?",
            icon="warning"
        )

        if not confirm:
            return

        self.nuke_button.configure(state="disabled")
        thread = threading.Thread(target=self._nuke_thread)
        thread.start()

    def _nuke_thread(self):
        """Nuke operation running in separate thread."""
        self._clear_log()

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._log(f"{'=' * 50}", "header")
        self._log(f"  SHADER CACHE NUKE v{VERSION} - {timestamp}", "header")
        self._log(f"{'=' * 50}", "header")
        self._log("", "info")

        stats = {"cleared": 0, "skipped": 0, "failed": 0, "not_selected": 0}

        # === Star Citizen subfolders ===
        self._log("[STAR CITIZEN]", "header")
        self._log("-" * 14, "info")

        if not self.sc_subfolders:
            self._log("  (no subfolders found)", "info")
        else:
            for folder_name, folder_path, _ in self.sc_subfolders:
                if folder_name not in self.sc_cache_vars:
                    continue

                if not self.sc_cache_vars[folder_name].get():
                    self._log(f"  [--] {folder_name} (not selected)", "info")
                    stats["not_selected"] += 1
                    continue

                if not folder_path.exists():
                    self._log(f"  [SKIP] {folder_name} - not found", "skip")
                    stats["skipped"] += 1
                    continue

                self._log(f"  Clearing {folder_name}...")
                success, message = self._clear_folder(folder_path, recreate=False)

                if success:
                    self._log(f"  [OK] {folder_name} - {message}", "ok")
                    stats["cleared"] += 1
                else:
                    self._log(f"  [FAIL] {folder_name} - {message}", "fail")
                    stats["failed"] += 1

        self._log("", "info")

        # === Static caches (NVIDIA, AMD, DirectX) ===
        for category, caches in self.static_cache_definitions.items():
            self._log(f"[{category.upper()}]", "header")
            self._log("-" * len(category), "info")

            for cache_id, (name, path, recreate) in caches.items():
                if not self.static_cache_vars[cache_id].get():
                    self._log(f"  [--] {name} (not selected)", "info")
                    stats["not_selected"] += 1
                    continue

                if not path.exists():
                    self._log(f"  [SKIP] {name} - not found", "skip")
                    stats["skipped"] += 1
                    continue

                self._log(f"  Clearing {name}...")
                success, message = self._clear_folder(path, recreate)

                if success:
                    self._log(f"  [OK] {name} - {message}", "ok")
                    stats["cleared"] += 1
                else:
                    self._log(f"  [FAIL] {name} - {message}", "fail")
                    stats["failed"] += 1

            self._log("", "info")

        # Summary
        self._log(f"{'=' * 50}", "header")
        self._log("  SUMMARY", "header")
        self._log(f"{'=' * 50}", "header")
        self._log(f"  Cleared:      {stats['cleared']}", "ok" if stats['cleared'] > 0 else "info")
        self._log(f"  Skipped:      {stats['skipped']}", "skip" if stats['skipped'] > 0 else "info")
        self._log(f"  Failed:       {stats['failed']}", "fail" if stats['failed'] > 0 else "info")
        self._log(f"  Not selected: {stats['not_selected']}", "info")
        self._log("", "info")
        self._log("NOTE: First game launch will have longer load", "info")
        self._log("      times as shaders recompile.", "info")

        self.root.after(0, lambda: self.nuke_button.configure(state="normal"))
        self.root.after(0, self._scan_sc_subfolders)
        self.root.after(100, self._prompt_restart)

    def _prompt_restart(self):
        """Ask user if they want to restart the computer."""
        restart = messagebox.askyesno(
            "Restart Computer?",
            "Shader cache nuke complete.\n\n"
            "It is recommended to restart your computer\n"
            "for changes to take full effect.\n\n"
            "Restart now?",
            icon="question"
        )

        if restart:
            try:
                subprocess.run(
                    ["shutdown", "/r", "/t", "10", "/c", "Restarting after shader cache nuke..."],
                    check=True
                )
                self._log("", "info")
                self._log("Computer will restart in 10 seconds...", "header")
                self._log("To cancel: open CMD and run 'shutdown /a'", "info")
            except Exception as e:
                messagebox.showerror("Error", f"Could not initiate restart:\n{e}")

    # === Version checking ===

    def _check_for_updates_async(self):
        """Check for updates in background thread."""
        thread = threading.Thread(target=self._check_for_updates, daemon=True)
        thread.start()

    def _check_for_updates(self):
        """Check GitHub for newer version."""
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            request = urllib.request.Request(url, headers={"User-Agent": "ShaderNuke"})

            with urllib.request.urlopen(request, timeout=5) as response:
                data = json.loads(response.read().decode())
                latest_version = data.get("tag_name", "").lstrip("v")
                release_url = data.get("html_url", "")

                if latest_version and self._version_compare(latest_version, VERSION) > 0:
                    self.root.after(0, lambda: self._show_update_available(latest_version, release_url))

        except Exception:
            # Silent fail - update check is non-critical
            pass

    def _version_compare(self, v1: str, v2: str) -> int:
        """
        Compare two version strings.
        Returns: >0 if v1 > v2, <0 if v1 < v2, 0 if equal
        """
        def parse(v):
            return [int(x) for x in v.split(".") if x.isdigit()]

        parts1 = parse(v1)
        parts2 = parse(v2)

        # Pad shorter version with zeros
        max_len = max(len(parts1), len(parts2))
        parts1.extend([0] * (max_len - len(parts1)))
        parts2.extend([0] * (max_len - len(parts2)))

        for a, b in zip(parts1, parts2):
            if a > b:
                return 1
            elif a < b:
                return -1
        return 0

    def _show_update_available(self, latest_version: str, release_url: str):
        """Show update notification in log and update version label."""
        self._log(f"UPDATE AVAILABLE: v{latest_version}", "update")
        self._log(f"Download: {release_url}", "update")
        self._log("", "info")

        self.version_label.config(
            text=f"v{VERSION} (v{latest_version} available)",
            foreground="purple",
            cursor="hand2"
        )
        self.version_label.bind("<Button-1>", lambda e: self._open_release_page(release_url))

    def _open_release_page(self, url: str):
        """Open release page in browser."""
        import webbrowser
        webbrowser.open(url)


def main():
    root = tk.Tk()
    app = ShaderNukeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()