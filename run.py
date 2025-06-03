# run.py - 新しい起動スクリプト

import streamlit as st
import sys
import subprocess
from pathlib import Path

def main():
    """アプリケーション起動"""
    project_root = Path(__file__).parent
    app_path = project_root / "app" / "main.py"
    
    if app_path.exists():
        print("🚀 新構造でアプリを起動します...")
        subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)])
    else:
        print("🔄 フォールバック: 旧ファイルでアプリを起動します...")
        old_path = project_root / "asin_app_main.py"
        subprocess.run([sys.executable, "-m", "streamlit", "run", str(old_path)])

if __name__ == "__main__":
    main()