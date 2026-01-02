#!/usr/bin/env python3
"""
Shader Cache Nuke Script v3 - GUI Version
Clears shader caches for Star Citizen, NVIDIA, AMD, and DirectX
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


class ShaderNukeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Shader Cache Nuke v3")
        self.root.resizable(True, True)

        # Setup paths
        self.local_appdata = Path(os.environ.get("LOCALAPPDATA", ""))
        self.program_data = Path(os.environ.get("PROGRAMDATA", ""))

        # Cache definitions: (name, path, recreate_after_delete)
        self.cache_definitions = self._build_cache_definitions()

        # Checkbox variables
        self.cache_vars = {}

        self._build_ui()

        # Center window on screen
        self._center_window(600, 700)

    def _build_cache_definitions(self) -> dict:
        """Build dictionary of all cache locations."""
        nvidia_local = self.local_appdata / "NVIDIA"
        amd_local = self.local_appdata / "AMD"

        # Get NV_Cache path from registry or default
        nv_cache_path = self._get_nvidia_cache_from_registry()
        if nv_cache_path is None:
            nv_cache_path = self.program_data / "NVIDIA Corporation" / "NV_Cache"

        return {
            "Star Citizen": {
                "sc_all": ("All Shader Data", self.local_appdata / "star citizen", False),
            },
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

    def _build_ui(self):
        """Build the user interface."""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)  # Log area expands

        # === SELECTION FRAME ===
        selection_frame = ttk.LabelFrame(main_frame, text="Select Caches to Clear", padding="10")
        selection_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        selection_frame.columnconfigure((0, 1, 2, 3), weight=1)

        col = 0
        for category, caches in self.cache_definitions.items():
            # Category frame
            cat_frame = ttk.LabelFrame(selection_frame, text=category, padding="5")
            cat_frame.grid(row=0, column=col, sticky="nsew", padx=5)

            row = 0
            for cache_id, (name, path, _) in caches.items():
                var = tk.BooleanVar(value=True)
                self.cache_vars[cache_id] = var

                # Check if path exists and style accordingly
                exists = path.exists()
                cb = ttk.Checkbutton(cat_frame, text=name, variable=var)
                cb.grid(row=row, column=0, sticky="w")

                # Add indicator for existing paths
                if exists:
                    indicator = ttk.Label(cat_frame, text="●", foreground="green")
                else:
                    indicator = ttk.Label(cat_frame, text="○", foreground="gray")
                indicator.grid(row=row, column=1, sticky="e", padx=(5, 0))

                row += 1

            col += 1

        # === BUTTON FRAME ===
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        button_frame.columnconfigure((0, 1, 2, 3), weight=1)

        ttk.Button(button_frame, text="Select All", command=self._select_all).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Deselect All", command=self._deselect_all).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="Select Existing Only", command=self._select_existing).grid(row=0, column=2,
                                                                                                  padx=5)

        self.nuke_button = ttk.Button(button_frame, text="NUKE SELECTED", command=self._run_nuke)
        self.nuke_button.grid(row=0, column=3, padx=5)

        # === LOG FRAME ===
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="10")
        log_frame.grid(row=2, column=0, sticky="nsew")
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

        # === LEGEND ===
        legend_frame = ttk.Frame(main_frame)
        legend_frame.grid(row=3, column=0, sticky="w", pady=(5, 0))

        ttk.Label(legend_frame, text="● = Exists", foreground="green").grid(row=0, column=0, padx=(0, 15))
        ttk.Label(legend_frame, text="○ = Not found", foreground="gray").grid(row=0, column=1)

        # Initial log message
        self._log("Shader Cache Nuke v3 ready.", "info")
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

    def _select_all(self):
        """Select all checkboxes."""
        for var in self.cache_vars.values():
            var.set(True)

    def _deselect_all(self):
        """Deselect all checkboxes."""
        for var in self.cache_vars.values():
            var.set(False)

    def _select_existing(self):
        """Select only caches that exist."""
        for category, caches in self.cache_definitions.items():
            for cache_id, (name, path, _) in caches.items():
                self.cache_vars[cache_id].set(path.exists())

    def _clear_folder(self, path: Path, recreate: bool = True) -> tuple[bool, str]:
        """
        Clear a folder's contents.
        Attempts to delete files individually, skipping locked ones.
        Returns (success, message).
        """
        if not path.exists():
            return False, "Not found"

        deleted = 0
        skipped = 0
        bytes_freed = 0

        # Walk through all files and try to delete each
        for root, dirs, files in os.walk(path, topdown=False):
            # Delete files
            for name in files:
                file_path = Path(root) / name
                try:
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    deleted += 1
                    bytes_freed += file_size
                except (PermissionError, OSError):
                    skipped += 1

            # Delete empty directories
            for name in dirs:
                dir_path = Path(root) / name
                try:
                    dir_path.rmdir()  # Only works if empty
                except (PermissionError, OSError):
                    pass  # Directory not empty or locked

        # Try to remove the root folder itself
        try:
            if path.exists() and not any(path.iterdir()):
                path.rmdir()
                if recreate:
                    path.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError):
            pass

        # Build result message
        mb_freed = bytes_freed / (1024 * 1024)

        if deleted == 0 and skipped > 0:
            return False, f"All {skipped} files locked"
        elif skipped > 0:
            return True, f"Cleared {deleted} files ({mb_freed:.1f} MB), {skipped} locked"
        else:
            return True, f"Cleared {deleted} files ({mb_freed:.1f} MB)"

    def _run_nuke(self):
        """Execute the nuke operation in a separate thread."""
        # Confirmation dialog
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

        # Disable button during operation
        self.nuke_button.configure(state="disabled")

        # Run in thread to keep UI responsive
        thread = threading.Thread(target=self._nuke_thread)
        thread.start()

    def _nuke_thread(self):
        """Nuke operation running in separate thread."""
        self._clear_log()

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._log(f"{'=' * 44}", "header")
        self._log(f"  SHADER CACHE NUKE - {timestamp}", "header")
        self._log(f"{'=' * 44}", "header")
        self._log("", "info")

        stats = {"cleared": 0, "skipped": 0, "failed": 0, "not_selected": 0}

        for category, caches in self.cache_definitions.items():
            self._log(f"[{category.upper()}]", "header")
            self._log("-" * len(category), "info")

            for cache_id, (name, path, recreate) in caches.items():
                if not self.cache_vars[cache_id].get():
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
        self._log(f"{'=' * 44}", "header")
        self._log("  SUMMARY", "header")
        self._log(f"{'=' * 44}", "header")
        self._log(f"  Cleared:      {stats['cleared']}", "ok" if stats['cleared'] > 0 else "info")
        self._log(f"  Skipped:      {stats['skipped']}", "skip" if stats['skipped'] > 0 else "info")
        self._log(f"  Failed:       {stats['failed']}", "fail" if stats['failed'] > 0 else "info")
        self._log(f"  Not selected: {stats['not_selected']}", "info")
        self._log("", "info")
        self._log("NOTE: First game launch will have longer load", "info")
        self._log("      times as shaders recompile.", "info")

        # Re-enable button
        self.root.after(0, lambda: self.nuke_button.configure(state="normal"))

        # Refresh existence indicators
        self.root.after(0, self._refresh_indicators)

        # Prompt for restart
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
                subprocess.run(["shutdown", "/r", "/t", "10", "/c", "Restarting after shader cache nuke..."],
                               check=True)
                self._log("", "info")
                self._log("Computer will restart in 10 seconds...", "header")
                self._log("To cancel: open CMD and run 'shutdown /a'", "info")
            except Exception as e:
                messagebox.showerror("Error", f"Could not initiate restart:\n{e}")

    def _refresh_indicators(self):
        """Refresh the UI to update existence indicators."""
        # Rebuild the cache definitions to refresh paths
        self.cache_definitions = self._build_cache_definitions()
        # For simplicity, we'd need to rebuild the UI or store indicator references
        # For now, just log that user can restart to see updated indicators
        self._log("", "info")
        self._log("Restart app to refresh existence indicators.", "info")


def main():
    root = tk.Tk()
    app = ShaderNukeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()