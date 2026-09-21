"""家を空ける前の確認。

  python precheck.py

留守中にカメラが止まる原因は、だいたい決まっている。
出かける前にまとめて確かめられるようにする。
"""
import json
import socket
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

OK, WARN, NG = "  [ OK ]", "  [注意]", "  [ NG ]"


def powershell(script: str) -> str:
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=30,
        )
        return (r.stdout or "").strip()
    except Exception:
        return ""


def check_server() -> bool:
    cfg = {}
    f = BASE / "config.json"
    if f.exists():
        cfg = json.loads(f.read_text(encoding="utf-8"))
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        alive = s.connect_ex(("127.0.0.1", int(cfg.get("port", 8443)))) == 0
    print((OK if alive else NG) + " サーバが動いている")
    if not alive:
        print("         → start.bat を実行するか、パソコンを再起動してください")
    return alive


def check_autostart() -> bool:
    out = powershell(
        "$t = Get-ScheduledTask -TaskName 'PetCamera' -ErrorAction SilentlyContinue;"
        "if (-not $t) { 'none' } else {"
        "  $b = if ($t.Triggers[0].CimClass.CimClassName -like '*Boot*')"
        "       { 'boot' } else { 'logon' };"
        "  $b + ' ' + $t.Principal.UserId }"
    )
    if out.startswith("boot"):
        print(OK + " 電源を入れるだけで自動起動する")
        return True
    if out.startswith("logon"):
        print(NG + " 自動起動が「ログオン時」になっている")
        print("         → 留守中の再起動で立ち上がりません。")
        print("            install_autostart.bat を管理者として実行してください")
        return False
    print(NG + " 自動起動が設定されていない")
    print("         → install_autostart.bat を管理者として実行してください")
    return False


def check_fast_startup() -> bool:
    """高速スタートアップが有効だと、シャットダウンが完全な終了にならない。

    その状態から電源を入れ直しても完全な起動をしないため、
    「PCの起動時」のタスクが走らない恐れがある。
    スマートプラグで電源を入れ直す使い方では致命的になる。
    """
    # レジストリの区切りは、エスケープで壊れないように組み立てる
    key = chr(92).join(
        ["HKLM:", "SYSTEM", "CurrentControlSet", "Control",
         "Session Manager", "Power"]
    )
    out = powershell(
        "(Get-ItemProperty '" + key + "' -Name HiberbootEnabled"
        " -ErrorAction SilentlyContinue).HiberbootEnabled"
    )
    if out in ("0", ""):
        print(OK + " 高速スタートアップが無効")
        return True
    print(NG + " 高速スタートアップが有効")
    print("         → 電源を入れ直しても自動起動しない恐れがあります。")
    print("            管理者のPowerShellで powercfg /h off を実行してください")
    return False


def check_sleep() -> bool:
    out = subprocess.run(
        ["powercfg", "/query", "SCHEME_CURRENT", "SUB_SLEEP", "STANDBYIDLE"],
        capture_output=True, text=True, encoding="cp932", errors="replace",
    ).stdout
    ac = [ln for ln in out.splitlines() if "AC" in ln]
    idle = None
    for ln in ac:
        for tok in ln.split():
            if tok.startswith("0x"):
                idle = int(tok, 16)
    if idle == 0:
        print(OK + " コンセント接続時はスリープしない")
        return True
    print(WARN + f" スリープする設定です（{idle}秒）")
    print("         → 電源プラン → スリープ → 「なし」にしてください")
    return False


def check_cert() -> bool:
    try:
        import ts_cert

        left = ts_cert.days_left()
        name = ts_cert.cert_name()
    except Exception:
        left, name = -1, None
    if name and left > 14:
        print(OK + f" 証明書は有効（残り {left:.0f} 日・{name}）")
        return True
    if name and left > 0:
        print(WARN + f" 証明書の残りが少ない（{left:.0f} 日）")
        print("         → 留守中に切れる恐れがあります。出発前に再起動を")
        return False
    print(NG + " 正式な証明書がありません（ブラウザに警告が出ます）")
    return False


def check_devices() -> bool:
    try:
        import ts_cert

        exe = ts_cert.exe()
        if not exe:
            print(WARN + " Tailscale が見つかりません")
            return False
        out = subprocess.run(
            [str(exe), "status"], capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=20,
        ).stdout
    except Exception:
        print(WARN + " Tailscale の状態を取得できません")
        return False

    lines = [l for l in out.splitlines() if l.startswith("100.")]
    names = [l.split()[1] for l in lines if len(l.split()) > 1]
    print(OK + f" Tailscale に {len(names)} 台（{', '.join(names)}）")
    if len(names) < 3:
        print(WARN + " カメラ端末と持ち出す端末が入っているか確認してください")
    return True


def check_recordings() -> bool:
    try:
        import server

        items = server.rec_list()
        total = sum(r.get("size", 0) for r in items) / 1e6
        print(OK + f" 録画 {len(items)} 本 / {total:.0f} MB（古いものから自動で消えます）")
    except Exception:
        pass
    return True


def main() -> int:
    print("=" * 60)
    print("  出かける前の確認")
    print("=" * 60)
    results = [
        check_server(),
        check_autostart(),
        check_fast_startup(),
        check_sleep(),
        check_cert(),
        check_devices(),
        check_recordings(),
    ]
    print("=" * 60)
    bad = results.count(False)
    if bad == 0:
        print("  すべて問題ありません。いってらっしゃい。")
    else:
        print(f"  {bad} 件、直したほうがよい点があります。上の [NG] を見てください。")
    print("=" * 60)
    print()
    print("  ※ カメラ端末側も確認してください")
    print("     ・充電ケーブルが挿さっているか")
    print("     ・画面が点いていて、ページが開いたままか")
    print("     ・Tailscale のスイッチが入っているか")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
