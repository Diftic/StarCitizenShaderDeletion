# TODO — Star Citizen Performance Tool

## In Progress / Next

- [ ] Verify GitHub Pages landing page renders correctly at `https://diftic.github.io/StarCitizenShaderDeletion/`

- [ ] WCAG contrast pass for light mode log tag colours (`good`/`warning`/`issue` hardcoded hex values; move to `THEMES` dict)
- [ ] Threading cancellation token — add `threading.Event` to `_analysis_worker` so re-scan cancels a running scan cleanly
- [ ] Custom SC install path — surface a "Browse" option in `_scan_sc_installs` for non-standard locations

- [x] Build and test compiled `.exe` with new icon + UAC elevation
- [ ] Verify dark mode colours on high-DPI / 4K displays
- [ ] Confirm standby memory clears after privilege fix (post-restart test)
- [ ] Confirm locked file reboot-scheduling works end-to-end after restart

## Backlog

- [ ] Persist theme preference to a local config file (e.g. `%APPDATA%\SCPerfTool\settings.json`)
- [ ] Add tray icon / minimise-to-tray option
- [ ] Export analysis report to text file
- [ ] Add "Open Windows Settings" shortcut for power plan (ms-settings:powersleep as alternative)

## Verified Patterns

- `ShellExecuteW(None, "runas", ...)` with explicit `script_dir` as `lpDirectory` reliably elevates on Win 10/11
- Use `ctypes.wintypes.HANDLE(-1)` for the current-process pseudo-handle — avoids 64-bit truncation from `GetCurrentProcess()` without `restype`
- `MoveFileExW(path, NULL, MOVEFILE_DELAY_UNTIL_REBOOT)` requires admin; schedules file for deletion at early boot before any locks
- `ttk.Style` with `clam` theme is the most customisable built-in base for manual dark-mode theming
- `tk.PhotoImage.put("{hex hex ...}", to=(0, y))` is the fastest row-by-row pixel write without PIL
- Missing `HwSchMode` registry value = HAGS disabled (not unknown); absent key = genuinely unknown

## Known Issues

- `ttk.Scrollbar` inside `ScrolledText` does not fully repaint on theme switch (OS-rendered widget on Windows)
- Combobox dropdown background does not honour `fieldbackground` on all Windows versions — may stay white in dark mode
- HAGS registry detection: if elevated `pythonw.exe` reads differently from non-elevated Python, Re-scan is the workaround
