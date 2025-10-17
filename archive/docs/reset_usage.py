#!/usr/bin/env python3
"""
Reset Adobe Helper Usage Tracker

This script resets the local usage tracker and clears all session data,
mimicking the effect of clearing browser data in Chrome.
"""

import json
import shutil
from pathlib import Path


def reset_usage():
    """Reset usage tracking and session data"""
    
    adobe_dir = Path.home() / ".adobe-helper"
    
    if not adobe_dir.exists():
        print("✓ No usage data found - nothing to reset")
        return
    
    # Files and directories to clear
    usage_file = adobe_dir / "usage.json"
    cookies_dir = adobe_dir / "cookies"
    session_file = adobe_dir / "session.json"
    
    removed = []
    
    # Remove usage.json
    if usage_file.exists():
        usage_file.unlink()
        removed.append("usage.json")
    
    # Remove session.json
    if session_file.exists():
        session_file.unlink()
        removed.append("session.json")
    
    # Remove cookies directory
    if cookies_dir.exists():
        shutil.rmtree(cookies_dir)
        removed.append("cookies/")
    
    if removed:
        print("✓ Reset complete - removed:")
        for item in removed:
            print(f"  - {item}")
    else:
        print("✓ No data to reset")
    
    print("\nYou can now run conversions again!")


if __name__ == "__main__":
    reset_usage()
