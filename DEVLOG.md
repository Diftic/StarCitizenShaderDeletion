# DEVLOG — Star Citizen Performance Tool

## v3.2.0 — 2026-04-08

### UI Design Overhaul — Colour System, Accessibility & Visual Polish

#### Design audit
- Conducted three-perspective design audit: sales/marketing appeal, visual design (hierarchy, Gestalt, Fitts's Law), and universal design (WCAG AA compliance)
- Identified 19 issues across accessibility, information hierarchy, consistency, and messaging

#### Fixes implemented
- **Step indicators** — replaced text-only tabs with `tk.Frame` underline bars (3px accent colour for active, muted for inactive/done)
- **Theme toggle** — replaced `ttk.Combobox` with `Bar.TButton` in the nav bar; no dropdown, just a one-click toggle
- **Primary.TButton** — all primary action buttons ("Proceed", "Clean Now", "Re-scan") use a unified named style for visual consistency
- **LabelFrame grouping** — "Items to Clean" and other panels wrapped in `ttk.LabelFrame` with accent-coloured border and label
- **Log font** — Consolas 10 → 11pt; "hero" summary tag added (Consolas 14 bold) for the reclaimable size callout at top of report
- **Hero report block** — `_render_analysis_report` now opens with a prominent reclaimable-space summary in the hero tag
- **Status indicators** — `_populate_manual_ui` uses `● OK / ● ! / ● ✕` with theme-aware `color_good/warn/issue` keys
- **Section headers** — Segoe UI 9 → 10pt in cleaning UI
- **Equal-height panels** — `rowconfigure(weight=1)` on both cleaning panels so Items to Clean and Log share equal height at any window size
- **Scroll anywhere** — mousewheel binds on canvas `<Enter>`/`<Leave>` so the whole panel scrolls

#### Colour system
- Full `THEMES` dict rewrite with user-defined palettes:
  - **Light:** mint/teal/navy — `bg #e6fffb`, `bar_bg #041f2a`, `accent #00c2a8`, `btn_primary #3a506b`
  - **Dark:** amber/navy — `bg #2b2f3a`, `bar_bg #05060a`, `accent #ffb703`, `btn_primary #ffb703`
- New theme-aware colour keys: `bar_fg`, `accent_text`, `btn_primary_fg`, `color_good`, `color_warn`, `color_issue`
- Two-role system: `accent` (decorative teal/amber) vs `accent_text` (readable body colour) — teal fails on light content bg so cannot double as text
- Dark mode 3-level text hierarchy: `#c9d1d9` primary (8.66:1), `#8a9ab0` secondary (4.67:1), `#6a7888` muted

#### Contrast fixes (iterative, user-tested)
1. Primary button `#38bdf8` (sky-400, 2.14:1) → `#ffb703` amber with dark text `#05060a` (11.6:1)
2. Light mode status colours (Tailwind 400-series, 1.5–2.8:1) → 700/800-series for light, 400-series for dark
3. Dark mode amber text (`accent_text`, `section_fg`, `tag_header` were all amber) → `#c9d1d9`; amber restricted to interactive/decorative only
4. Dark mode body text `#f1f5f9` (12.21:1, too harsh) → `#c9d1d9` (8.66:1, VS Code range)

---

## v3.0.0 — 2026-04-08 (post-release)

### Documentation & distribution

- **README rewritten** — updated from old single-screen tool description to accurate v3.0.0 wizard docs; covers all features, 4-step flow, quick start, build instructions
- **GitHub Pages landing page** — `index.html` added to repo root; dark-mode single-page site with download button, feature grid, how-it-works steps, and footer; served at `https://diftic.github.io/StarCitizenShaderDeletion/`
- **GitHub Release v3.0.0 published** — `ShaderCacheNuke.exe` attached as release asset; update checker in existing installs will now detect and link to this release
- **gh CLI installed** — GitHub CLI v2.89.0 installed via winget for future release/PR/issue operations

---

## v3.0.0 — 2026-04-08

### Security & Quality fixes (post red-team + code review)

- **Junction pre-positioning guard** — `Analyzer._is_reparse_point()` added; `_scan_sc_shaders` and `clear_folder` now reject any path that is a symlink or has `FILE_ATTRIBUTE_REPARSE_POINT` set, preventing a non-admin attacker from planting a junction that causes the admin-running tool to delete arbitrary system files
- **`release_url` validation** — `_show_update` now parses the URL returned from the GitHub API and only opens it if the scheme is `https`/`http` and the host ends with `github.com`; rejects injected `file://` or protocol-handler URIs
- **NVIDIA registry path validation** — `_get_nvidia_cache_from_registry` now checks that the path is absolute, not a UNC path, and rooted under `%PROGRAMDATA%` or `%LOCALAPPDATA%` before returning it
- **Update check exception handling** — `except Exception: pass` replaced with specific handlers: network errors silent, malformed response logs a warning
- **UAC re-launch argument quoting** — `subprocess.list2cmdline(sys.argv)` replaces manual `" ".join(f'"{a}"')` which broke on paths with embedded quotes
- **`bytes_freed` accuracy** — `clear_folder` now tracks freed vs scheduled bytes separately; summary says "X MB freed, Y MB pending reboot" instead of reporting scheduled bytes as freed
- **`_enable_privilege` return checked** — `clear_standby_memory` now aborts with a clear error message if a required privilege cannot be enabled instead of proceeding to a confusing NTSTATUS failure
- **Kill by PID** — `kill_process(exe, pid)` now uses `taskkill /PID` when a PID is available to avoid killing unrelated processes with the same name
- **`tasklist` CSV parsing** — `csv.reader` via `io.StringIO` replaces fragile manual `strip('"').split('","')` parsing
- **`_make_logger` deduplication** — now delegates to `_append` instead of duplicating the widget-write logic
- **Type hints** — `callable` builtin replaced with `collections.abc.Callable` in two signatures
- **Restart recommendation conditional** — "A restart is recommended…" message now only shown when at least one operation actually ran; suppressed when no items were cleaned

---

## v2.0.0 — 2026-04-08

### Session 2 additions

- **Select All / Deselect All** buttons added to Cleaning step header row
- **Restart Computer** button moved to Done step — full-width red (`Red.TButton` style), same as old Control Panel button
- **Locked file scheduling** — `clear_folder` now attempts `MoveFileExW(path, NULL, MOVEFILE_DELAY_UNTIL_REBOOT)` on locked files instead of skipping them; Done summary shows "X scheduled for reboot deletion" and a REBOOT REQUIRED banner
- **Done step summary** overhauled — now shows full per-operation breakdown with ✔/✘ per item, not just counts
- **Standby memory privilege fix** — `_enable_privilege()` added to `CleanerEngine`; enables `SeProfileSingleProcessPrivilege` + `SeIncreaseQuotaPrivilege` before `NtSetSystemInformation`; fixed ctypes 64-bit handle truncation bug (`GetCurrentProcess()` restype issue — now uses `HANDLE(-1)` pseudo-handle constant directly)
- **HAGS detection fix** — missing `HwSchMode` registry value now correctly treated as disabled (False) instead of unknown (None); added `KEY_WOW64_64KEY` flag for robustness
- **HAGS instruction fix** — updated to correct path: `Win + I → System → Display → Graphics → Hardware-accelerated GPU scheduling → On`
- **Direct-open buttons** on every Manual step item:
  - HAGS → `ms-settings:display-advancedgraphics`
  - Power Plan → `control powercfg.cpl`
  - Game Bar → `ms-settings:gaming-gamebar`
  - Buttons visible regardless of status (good or warning)
- **Scanning overlay** — large centred "Scanning, please wait..." at 50pt shown while analysis runs; dismissed when scan completes; re-shown on Re-scan
- **Analysis log** now scrolls to top on completion
- **Mousewheel scrolling** works anywhere over the cleaning/manual canvas (not just the scrollbar) via `bind_all`/`unbind_all` on `<Enter>`/`<Leave>`
- **Cleaning list resize** — removed fixed `height=220`; list now grows with window (weight=2) alongside log (weight=1)
- **UAC elevation** — `pythonw.exe` used instead of `python.exe` to avoid console window; working directory explicitly passed to `ShellExecuteW`
- **Control Panel button** removed from Manual step (superseded by per-item direct buttons)

### Architecture notes

- `_configure_log_tags` changed from `@staticmethod` to instance method — reads `self.theme_colors` so log tag colours update on theme switch
- `_show_step` uses `self.theme_colors` for step indicator colours
- `self.manual_canvas` / `self.cleaning_canvas` stored as instance refs for theme repaints
- `_rerun_scan` clears `analysis_txt`, resets `analysis_done`/`report`, shows scan overlay, calls `_start_analysis`
- `stats["results"]` list tracks `(label, success, msg)` per operation for Done summary
- `add_item()` in `_populate_manual_ui` extended with optional `action: tuple[str, callable]` parameter for direct-open buttons
- `CONFLICT_SETTINGS` dict maps process exe → `(btn_label, ms-settings URI)` for Game Bar items

---

## v2.0.0 — Session 1 UI Overhaul

- Added light/dark theme system (`THEMES` dict with full colour palette)
  - Default is **Dark Mode**; selector combobox in top bar next to Re-scan button
- Added **↺ Re-scan** button in top-right of step indicator bar
- Added **auto-elevation** via `ShellExecuteW / runas`
- Changed window icon to programmatically drawn 32×32 magnifying glass

---

## v1.x (pre-session)

- 4-step wizard: Analysis → Manual → Cleaning → Done
- Shader cache detection across all drives and channels
- GPU cache scanning (NVIDIA / AMD / DirectX)
- Power plan + HAGS checks
- PyInstaller build via `build.py`
