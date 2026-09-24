"""タスクスケジューラから pythonw で起動するためのラッパー。

コンソールが無いので出力をログファイルへ書き、.env から NOTIFY_URL などを読み込む。
"""

import contextlib
import os
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG_PATH = ROOT / "logs" / "check.log"
MAX_LOG_BYTES = 1_000_000
JST = timezone(timedelta(hours=9))


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def main() -> int:
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    LOG_PATH.parent.mkdir(exist_ok=True)
    if LOG_PATH.exists() and LOG_PATH.stat().st_size > MAX_LOG_BYTES:
        LOG_PATH.replace(LOG_PATH.with_suffix(".log.old"))

    with (
        open(LOG_PATH, "a", encoding="utf-8") as log,
        contextlib.redirect_stdout(log),
        contextlib.redirect_stderr(log),
    ):
        print(f"[{datetime.now(JST):%Y-%m-%d %H:%M:%S}] ", end="")
        try:
            load_env(ROOT / ".env")
            import check

            sys.argv = [sys.argv[0]]
            return check.main()
        except Exception:
            # pythonw では標準エラーが見えないため、ログに残してから終了コードで失敗を伝える
            traceback.print_exc()
            raise


if __name__ == "__main__":
    sys.exit(main())
