#!/usr/bin/env python3
"""
Clean utility - removes Python cache files and build artifacts
"""

import shutil
from pathlib import Path


def clean():
    """Remove __pycache__ directories and .pyc/.pyo files."""
    root = Path(".")
    removed = 0
    
    # Remove __pycache__ directories
    for pycache in root.rglob("__pycache__"):
        shutil.rmtree(pycache)
        print(f"Removed: {pycache}")
        removed += 1
    
    # Remove .pyc files
    for pyc in root.rglob("*.pyc"):
        pyc.unlink()
        print(f"Removed: {pyc}")
        removed += 1
    
    # Remove .pyo files
    for pyo in root.rglob("*.pyo"):
        pyo.unlink()
        print(f"Removed: {pyo}")
        removed += 1
    
    # Remove build artifacts
    for dirname in ["build", "dist"]:
        dirpath = root / dirname
        if dirpath.exists():
            shutil.rmtree(dirpath)
            print(f"Removed: {dirpath}")
            removed += 1
    
    # Remove .spec files
    for spec in root.glob("*.spec"):
        spec.unlink()
        print(f"Removed: {spec}")
        removed += 1
    
    if removed == 0:
        print("Nothing to clean.")
    else:
        print(f"\nCleaned {removed} items.")


if __name__ == "__main__":
    clean()
