# -*- coding: utf-8 -*-
"""
Office Layout Engine - exe用ランチャー
起動するとStreamlitサーバーが立ち上がり、ブラウザで開きます
"""
import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path


def get_base_path():
    """PyInstallerでパッケージ化された場合のベースパスを取得"""
    if getattr(sys, 'frozen', False):
        # exe実行時
        return Path(sys._MEIPASS)
    else:
        # 通常のPython実行時
        return Path(__file__).parent


def main():
    base_path = get_base_path()
    app_path = base_path / "src" / "streamlit_app.py"

    # 作業ディレクトリを設定
    if getattr(sys, 'frozen', False):
        os.chdir(base_path)

    # Streamlitの設定
    port = 8501

    print("=" * 50)
    print("  Office Layout Engine")
    print("=" * 50)
    print(f"\n起動中... ブラウザが自動で開きます")
    print(f"URL: http://localhost:{port}")
    print("\n終了するにはこのウィンドウを閉じてください")
    print("=" * 50)

    # 少し待ってからブラウザを開く
    def open_browser():
        time.sleep(2)
        webbrowser.open(f"http://localhost:{port}")

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    # Streamlitを起動
    from streamlit.web import cli as stcli
    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.port", str(port),
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--theme.base", "light",
    ]

    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
