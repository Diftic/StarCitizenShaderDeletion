---
description: Fresh-eyes code review of nuke_shaders_gui.py — Star Citizen Performance Tool v2.0.0
tags: [code-review, findings, python, tkinter, windows]
audience: { human: 80, agent: 20 }
purpose: { findings: 100 }
---

# Code Review — nuke_shaders_gui.py

**Reviewed:** `nuke_shaders_gui.py` (Star Citizen Performance Tool v2.0.0, ~1689 lines)
**Scope:** Correctness, security, maintainability

## Summary

A single-file Windows desktop tool that scans Star Citizen-related caches, surfaces system health issues (HAGS, power plan, conflicting processes), and automates cache clearing through a 4-step tkinter wizard. The architecture is clean — `Analyzer` handles scanning, `CleanerEngine` handles file operations, and `WizardApp` owns all UI. The code is well-structured for its scope and handles many edge cases gracefully. Several issues need attention before this tool can be trusted to run with admin privileges on users' machines.

**Verdict: REQUEST CHANGES**

---

## Blocking Issues

### 🔴 `_check_for_updates` silently swallows all exceptions
`nuke_shaders_gui.py:1641`

```python
except Exception:
    pass
```

A bare `except Exception: pass` on the update check means network errors, malformed JSON, unexpected response shapes, and encoding issues all vanish silently. This is fine for a background thread — but the issue is that if `data.get("html_url", "")` returns something unexpected (e.g., non-string), the lambda passed to `root.after` will also fail silently. The real risk: if the GitHub API response schema changes, users silently never see updates.

More critically, `_version_compare` calls `int(x)` inside a list comprehension — if `tag_name` contains a version like `2.0.0-beta`, the `isdigit()` filter handles it, but the function would return 0 (equal) rather than correctly comparing pre-release versions. A `2.0.0-beta` tag would never trigger an update prompt for a user already on `2.0.0`.

**Fix:** At minimum, log the exception to stderr. Consider adding a visible "could not check for updates" indicator rather than silently doing nothing.

---

### 🔴 `main()` UAC elevation path uses manual string argument reconstruction
`nuke_shaders_gui.py:1676-1679`

```python
" ".join(f'"{a}"' for a in sys.argv)
```

This re-assembles command-line arguments by wrapping each in double quotes. If any argument contains double quotes, backslashes, or spaces in unexpected patterns, the argument string passed to `ShellExecuteW` will be malformed. This is a classic shell injection surface — not from external input, but from the tool's own invocation path on a user's filesystem (e.g., a path like `C:\Users\John "JD" Doe\Scripts\tool.py`).

**Fix:** Use `subprocess.list2cmdline(sys.argv)` which correctly escapes arguments for Windows command-line parsing.

---

### 🔴 `clear_folder` removes the target folder, then tries to recreate it — race condition
`nuke_shaders_gui.py:413-425`

```python
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
```

The folder removal only runs if it's empty after the walk — that's correct. The recreate logic then runs unconditionally. However, if `rmdir` raises silently (directory still exists with locked content), `mkdir` with `exist_ok=True` will still succeed without error, giving a false impression of a clean state. The returned message will say "Cleared N files" even if the directory itself couldn't be cleaned. This is not data-loss risk, but it means the user is told success when the cache folder still exists with content.

Separately: `bytes_freed` is measured via `stat().st_size` before deletion, but if any file is scheduled for reboot deletion (via `MoveFileExW`), those bytes are reported as "freed" even though the file still occupies disk space until reboot. The UI should distinguish "freed now" from "will be freed on reboot."

---

### 🔴 `_enable_privilege` return value is ignored in `clear_standby_memory`
`nuke_shaders_gui.py:525-526`

```python
for priv in ("SeProfileSingleProcessPrivilege", "SeIncreaseQuotaPrivilege"):
    CleanerEngine._enable_privilege(priv)
```

`_enable_privilege` returns `True`/`False` indicating whether the privilege was successfully enabled. Both return values are silently discarded. If privilege escalation fails (e.g., the process is admin but lacks the specific privilege), `NtSetSystemInformation` will return a non-zero NTSTATUS, which is reported to the user. But the root cause (privilege failure) is invisible — the user sees `NTSTATUS 0xC0000022` (ACCESS_DENIED) with no explanation.

**Fix:** Check the return value and either skip the operation with a clear message or include privilege failure in the error output.

---

## Suggestions

### 🟡 Thread safety: `self.report` is written on a background thread and read on the main thread without synchronisation
`nuke_shaders_gui.py:880`

```python
self.report = self.analyzer.run(progress)
self.root.after(0, self._render_analysis_report)
```

`self.report` is assigned in `_analysis_worker` (a daemon thread), and `root.after` schedules `_render_analysis_report` to run on the main thread. In CPython, the GIL means a dict assignment is effectively atomic, so this is unlikely to cause corruption in practice. However, the `_rerun_scan` method also resets `self.report = {}` on the main thread while a previous analysis thread could theoretically still be running. If a user clicks "Re-scan" immediately after the scan starts, the previous thread continues writing to a stale reference while the new thread also begins. The second thread's `self.report = ...` wins, but the first thread's `progress` callbacks may still fire.

**Fix:** Add a `threading.Event` cancellation token that the worker checks at each stage. This is the standard pattern for cancellable background scans.

---

### 🟡 `_scan_sc_installs` drive enumeration only checks three hardcoded base paths
`nuke_shaders_gui.py:200-206`

```python
for base_rel in (
    "Program Files/Roberts Space Industries/StarCitizen",
    "Roberts Space Industries/StarCitizen",
    "Games/Roberts Space Industries/StarCitizen",
):
```

Users who installed to custom paths (e.g., `D:\SC\` or `E:\Games\SC`) will not have their install caches found or cleaned. The tool already has a "user-specified SC folder" feature mentioned in the git log, but this scan path enumeration doesn't appear to honour any user-provided path. This means the cleaning step won't offer to clear install caches for users with non-standard install locations.

**Fix:** Accept an optional user-provided base path in `_scan_sc_installs` and prepend it to the search list. Or search for `StarCitizen.exe` under each drive root (bounded depth).

---

### 🟡 `_get_running_processes` parses `tasklist /FO CSV` output by splitting on `","`
`nuke_shaders_gui.py:267`

```python
parts = line.strip('"').split('","')
```

CSV output from `tasklist` wraps each field in quotes. This manual split is fragile: it strips the leading `"` then splits on `","`. If a process image name contains a `","` sequence (pathological, but possible with some system process names or locale-specific output), parsing would be incorrect. More practically, `tasklist` output is locale-sensitive — on non-English Windows, field separators and formatting may differ.

**Fix:** Use the `csv` standard library module to parse the output, which handles quoted fields correctly.

---

### 🟡 `_configure_log_tags` uses hardcoded colour values for `good`, `warning`, `issue`, `ok`, `fail`
`nuke_shaders_gui.py:1465-1472`

```python
widget.tag_configure("good", foreground="#2ecc40")
widget.tag_configure("warning", foreground="#ff851b")
widget.tag_configure("issue", foreground="#ff4136")
```

These colours are not theme-aware. In light mode, `#2ecc40` (bright green) on a white background has a contrast ratio around 1.8:1 — well below the WCAG 2.1 AA minimum of 4.5:1 for normal text. Users with colour-vision deficiencies or light themes will have difficulty reading status output.

`_apply_theme` calls `_configure_log_tags` after theme changes, but since the colours are hardcoded inside `_configure_log_tags`, switching to Light mode doesn't fix the contrast issue.

**Fix:** Add theme-appropriate variants to the `THEMES` dict (e.g., `"tag_good"`, `"tag_warning"`) and reference them in `_configure_log_tags`.

---

### 🟡 `_make_logger` and `_append` are functionally identical
`nuke_shaders_gui.py:1592-1612`

`_make_logger` returns a closure that calls `_append`'s logic directly (not `_append` itself). The two implementations are byte-for-byte equivalent in behaviour, except one is a factory and the other is a static method. Having two code paths for the same operation means future changes must be made in two places.

**Fix:** Have `_make_logger` return a closure that calls `_append(widget, text, tag)` directly.

---

### 🟡 `_do_restart` has a broad `except Exception` with user-visible error
`nuke_shaders_gui.py:1448`

```python
except Exception as e:
    messagebox.showerror("Error", f"Could not restart:\n{e}")
```

This catches `CalledProcessError` again (already handled above it) and any other exception. While showing the error to the user is better than swallowing it, the message `f"Could not restart:\n{e}"` will expose raw Python exception messages (e.g., `[WinError 5] Access is denied`) to end users. These are not user-friendly.

---

## Minor Notes

- 🟢 `nuke_shaders_gui.py:133` — `progress: callable` should be `progress: Callable[[str], None]` (or `Callable` from `collections.abc`) for proper type coverage. `callable` is a builtin that checks at runtime, not a type hint.
- 🟢 `nuke_shaders_gui.py:1592` — `_make_logger` return type is annotated as `callable` (lowercase). Same issue as above — should be `Callable[[str, str], None]`.
- 🟢 `nuke_shaders_gui.py:341` — `_get_memory_info` has return type `dict` (unparameterised). Given the fixed structure, `dict[str, float]` would be more precise.
- 🟢 `nuke_shaders_gui.py:135` — `run()` return type is `dict` (unparameterised). The report dict has a well-known set of keys; a `TypedDict` would make this contract explicit and enable IDE assistance.
- 🟢 `nuke_shaders_gui.py:396-412` — `os.walk` is used instead of `Path.rglob` (which is used in `_get_folder_size`). Mixing paradigms — `os.walk` vs `pathlib` — adds cognitive load. Either is fine; consistency would be better.
- 🟢 `nuke_shaders_gui.py:1282` — `stats: dict = {"ok": 0, "fail": 0, "results": []}` — the list is mutable and shared by reference. In this specific code path it's not an issue (new dict per call), but this is a pattern to avoid on default arguments.
- ❓ `nuke_shaders_gui.py:479` — `CURRENT_PROCESS = ctypes.wintypes.HANDLE(-1)` — is using the pseudo-handle constant `-1` for `GetCurrentProcess()` intentional? On 64-bit Windows, `ctypes.wintypes.HANDLE` is 32-bit, which would truncate `-1` to `0xFFFFFFFF`. This may work via Windows pseudo-handle semantics, but the comment says it "avoids ctypes restype truncation" — worth verifying this doesn't silently produce the wrong handle value on 64-bit systems. The safer approach is `ctypes.windll.kernel32.GetCurrentProcess()` with `restype = ctypes.wintypes.HANDLE`.
- ❓ `nuke_shaders_gui.py:599` — `bar.columnconfigure(list(range(4)), weight=1)` — tkinter's `columnconfigure` accepts an integer index or a list of indices. Passing `list(range(4))` gives equal weight to all 4 step label columns but not to columns 4 (theme combo) and 5 (rescan button). Is the intent to make these buttons right-aligned with no extra space, or was this an oversight?

---

## Strengths Worth Noting

- The separation of `Analyzer`, `CleanerEngine`, and `WizardApp` is clean and makes each class independently testable in principle.
- `MoveFileExW` fallback for locked files is a thoughtful addition that many similar tools miss.
- `_get_nvidia_cache_from_registry` with a fallback default path is robust.
- The `_bind_mousewheel` pattern (bind on Enter, unbind on Leave) correctly avoids the common bug where two scrollable areas fight over the global `<MouseWheel>` binding.
- Version comparison correctly zero-pads shorter version arrays before comparing.

---

> To address these findings, invoke the `review-responder` skill with this review.
