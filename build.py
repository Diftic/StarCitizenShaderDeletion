#!/usr/bin/env python3
"""
Build script for Shader Cache Nuke
Creates a standalone Windows executable using PyInstaller
"""

import subprocess
import sys
import shutil
from pathlib import Path


def check_pyinstaller():
    """Check if PyInstaller is installed, install if not."""
    try:
        import PyInstaller
        print(f"[OK] PyInstaller {PyInstaller.__version__} found")
        return True
    except ImportError:
        print("[!] PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("[OK] PyInstaller installed")
        return True


def clean_build_dirs():
    """Remove previous build artifacts."""
    dirs_to_clean = ["build", "dist", "__pycache__"]
    files_to_clean = list(Path(".").glob("*.spec"))
    
    for d in dirs_to_clean:
        if Path(d).exists():
            shutil.rmtree(d)
            print(f"[CLEAN] Removed {d}/")
    
    for f in files_to_clean:
        f.unlink()
        print(f"[CLEAN] Removed {f}")


def build_exe():
    """Build the executable."""
    script_name = "nuke_shaders_gui.py"
    exe_name = "ShaderCacheNuke"
    
    if not Path(script_name).exists():
        print(f"[ERROR] {script_name} not found in current directory")
        return False
    
    # PyInstaller arguments
    args = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",           # Single executable
        "--windowed",          # No console window (GUI app)
        "--clean",             # Clean cache before building
        f"--name={exe_name}",  # Output name
        "--noconfirm",         # Overwrite without asking
    ]
    
    # Add icon if it exists
    icon_path = Path("icon.ico")
    if icon_path.exists():
        args.append(f"--icon={icon_path}")
        print(f"[OK] Using icon: {icon_path}")
    else:
        print("[INFO] No icon.ico found, using default icon")
    
    # Add the script
    args.append(script_name)
    
    print("\n[BUILD] Running PyInstaller...")
    print(f"[BUILD] Command: {' '.join(args)}\n")
    
    result = subprocess.run(args)
    
    if result.returncode == 0:
        exe_path = Path("dist") / f"{exe_name}.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"\n{'=' * 50}")
            print(f"[SUCCESS] Build complete!")
            print(f"[SUCCESS] Output: {exe_path.absolute()}")
            print(f"[SUCCESS] Size: {size_mb:.1f} MB")
            print(f"{'=' * 50}")
            return True
    
    print("\n[ERROR] Build failed")
    return False


def main():
    print("=" * 50)
    print("  Shader Cache Nuke - Build Script")
    print("=" * 50)
    print()
    
    # Check/install PyInstaller
    if not check_pyinstaller():
        return 1
    
    # Clean previous builds
    print("\n[CLEAN] Removing previous build artifacts...")
    clean_build_dirs()
    
    # Build
    print()
    if build_exe():
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
