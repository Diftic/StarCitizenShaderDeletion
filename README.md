The Problem
CIG recommends deleting shader caches when experiencing FPS drops or visual glitches. However, the RSI Launcher's "Delete Shaders" function only clears Star Citizen's internal cache—it doesn't touch the NVIDIA/AMD driver-level shader caches that can also cause performance degradation.
These driver caches accumulate corrupted or outdated compiled shaders over time, especially after game patches. The result: stuttering, lower framerates, and longer load times.

The Solution
  Shader Cache Nuke is a lightweight utility that performs a comprehensive shader cache cleanup:
  Star Citizen — All shader data including version-specific folders (automatically handles new patch folders)
    NVIDIA — DXCache, GLCache, ComputeCache, NV_Cache
    AMD — DxCache, GLCache, VkCache, Dx9Cache
    DirectX — System-wide D3DSCache

Features:
  Simple GUI with checkboxes to select which caches to clear
  Visual indicators showing which caches exist on your system
  Graceful handling of locked files (clears what it can, skips what's in use)
  Prompts for system restart after completion
  Auto-update notification when new versions are available
  Requests admin privileges automatically for full cache access

Results
  On my system (RTX 4070 Ti), clearing all shader caches resulted in a 20% FPS increase. Your results may vary depending on how long since your last clean and your specific hardware configuration.

📣 Suggestion to CIG
The RSI Launcher's shader deletion is a good start, but it's incomplete. Players experiencing performance issues often don't realize that driver-level caches are a contributing factor.
Recommendation: Expand the Launcher's "Delete Shaders" functionality to include:
  NVIDIA/AMD driver shader caches (with user consent)
  Optional system restart prompt after deletion
  A brief explanation of why this helps (corrupted shaders after patches)
This could reduce support tickets, improve the new player experience after patches, and eliminate the need for third-party tools like this one.
