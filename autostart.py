"""パソコンの起動時に、ペットカメラを自動で立ち上げるようにする。

  python autostart.py install    自動起動を設定する
  python autostart.py uninstall  自動起動をやめる
  python autostart.py status     いまの状態とアドレスを表示する
  python autostart.py stop       いま動いているサーバを止める

Windowsのタスクスケジューラに登録する。追加のソフトは要らない。
黒い画面は出さず、落ちても自動で起動し直す。
"""
import json
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
TASK_NAME = "PetCamera"


def powershell(script: str) -> tuple[int, str]:
    r = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()


def pythonw() -> Path:
    """黒い画面を出さないほうのPython。無ければ普通のPythonを使う。"""
    cand = Path(sys.executable).with_name("pythonw.exe")
    return cand if cand.exists() else Path(sys.executable)


def config() -> dict:
    f = BASE / "config.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def port() -> int:
    return int(config().get("port", 8443))


def running() -> bool:
    """そのポートで待ち受けているかどうか。"""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port())) == 0


def task_detail() -> str:
    """どういう条件で起動する設定になっているか。"""
    code, out = powershell(
        f"$t = Get-ScheduledTask -TaskName '{TASK_NAME}' -ErrorAction SilentlyContinue;"
        "if (-not $t) { 'none' } else {"
        "  $kind = if ($t.Triggers[0].CimClass.CimClassName -like '*Boot*')"
        "          { 'PCの起動時' } else { 'ログオン時' };"
        "  $kind + ' / ' + $t.Principal.UserId }"
    )
    return out.strip() if code == 0 else "?"


def task_exists() -> bool:
    code, _ = powershell(
        f"if (Get-ScheduledTask -TaskName '{TASK_NAME}' "
        f"-ErrorAction SilentlyContinue) {{ exit 0 }} else {{ exit 1 }}"
    )
    return code == 0


def is_admin() -> bool:
    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def install() -> int:
    # SYSTEM で動く仕事を登録するには管理者の権限が要る
    if not is_admin():
        print("  管理者として実行する必要があります。")
        print()
        print("  install_autostart.bat を右クリック →「管理者として実行」")
        print("  でやり直してください。")
        return 1

    exe = pythonw()
    script = BASE / "server.py"
    ps = f"""
$ErrorActionPreference = 'Stop'
$action = New-ScheduledTaskAction -Execute '{exe}' `
    -Argument '"{script}"' -WorkingDirectory '{BASE}'
$trigger = New-ScheduledTaskTrigger -AtStartup
$trigger.Delay = 'PT30S'
$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' `
    -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartInterval (New-TimeSpan -Minutes 1) -RestartCount 3
Register-ScheduledTask -TaskName '{TASK_NAME}' -Action $action `
    -Trigger $trigger -Principal $principal -Settings $settings -Force `
    -Description 'ペットカメラのサーバを自動で起動します' | Out-Null
"""
    code, out = powershell(ps)
    if code != 0:
        print("  自動起動の設定に失敗しました。")
        print()
        print("  " + out.replace("\n", "\n  ")[:900])
        print()
        print("  「アクセスが拒否されました」と出ている場合は、")
        print("  このファイルを右クリック →「管理者として実行」でやり直してください。")
        return 1

    print("  自動起動を設定しました。")
    print()
    print("  ・パソコンの電源を入れると、ログインしなくても立ち上がります")
    print("  ・Windows Update の再起動のあとも、自分で復帰します")
    print("  ・黒い画面は出ません")
    print("  ・止まっても自動で起動し直します")
    print()
    if not running():
        powershell(f"Start-ScheduledTask -TaskName '{TASK_NAME}'")
        print("  いま起動しました。")
    else:
        print("  すでに動いているので、そのまま使えます。")
    return 0


def uninstall() -> int:
    if not task_exists():
        print("  自動起動は設定されていません。")
        return 0
    code, out = powershell(
        f"Unregister-ScheduledTask -TaskName '{TASK_NAME}' -Confirm:$false"
    )
    if code != 0:
        print("  解除に失敗しました:")
        print("  " + out.replace("\n", "\n  ")[:500])
        return 1
    print("  自動起動をやめました。")
    print("  これからは start.bat をダブルクリックして起動してください。")
    return 0


def stop() -> int:
    if task_exists():
        powershell(f"Stop-ScheduledTask -TaskName '{TASK_NAME}'")
    # タスク経由でない起動も止める
    powershell(
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe' "
        "or Name='pythonw.exe'\" | "
        "Where-Object { $_.CommandLine -like '*server.py*' } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
    )
    print("  サーバを止めました。" if not running() else "  止めきれませんでした。")
    return 0


def status() -> int:
    cfg = config()
    print("=" * 58)
    print("  PET CAMERA の状態")
    print("=" * 58)
    print(f"  サーバ    : {'動いています' if running() else '止まっています'}")
    if task_exists():
        detail = task_detail()
        print(f"  自動起動  : 設定済み（{detail}）")
        if "ログオン時" in detail:
            print("              ※ ログオンしないと立ち上がりません。")
            print("                 install_autostart.bat を管理者として実行し直すと、")
            print("                 電源投入だけで立ち上がるようになります。")
    else:
        print("  自動起動  : 未設定")
    print()
    if cfg.get("pin"):
        print(f"  PIN       : {cfg['pin']}")

    try:
        sys.path.insert(0, str(BASE))
        import ts_cert, make_cert

        name = ts_cert.hostname()
        if name and (BASE / "certs" / "ts-cert.pem").exists():
            print()
            print("  どこからでも（Tailscaleに繋いだ端末）")
            print(f"    カメラ  : https://{name}:{port()}/camera")
            print(f"    見る    : https://{name}:{port()}/viewer")
        ip = make_cert.local_ip()
        print()
        print("  家の中だけ")
        print(f"    カメラ  : https://{ip}:{port()}/camera")
        print(f"    見る    : https://{ip}:{port()}/viewer")
    except Exception:
        pass

    print()
    print(f"  記録      : {BASE / 'petcam.log'}")
    print("=" * 58)
    return 0


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "install":
        return install()
    if cmd == "uninstall":
        return uninstall()
    if cmd == "stop":
        return stop()
    if cmd == "status":
        return status()
    print(f"知らない指示です: {cmd}")
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
