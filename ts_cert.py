"""Tailscale の正式なHTTPS証明書を取り、期限が近づいたら更新する。

自己署名証明書だと、ブラウザに警告が出るだけでなく、
iPhone の Safari では警告を抜けたあとの通信を拒まれることがある。
Tailscale は自分のネットワーク名に対して正式な証明書を無料で出せるので、
使えるならそちらを使う。使えなければ自己署名のままで動く。
"""
import datetime
import json
import os
import subprocess
import threading
from pathlib import Path

BASE = Path(__file__).resolve().parent
CERT_DIR = BASE / "certs"
CERT_FILE = CERT_DIR / "ts-cert.pem"
KEY_FILE = CERT_DIR / "ts-key.pem"

RENEW_BELOW_DAYS = 25      # 残りがこの日数を切ったら更新する
CHECK_EVERY_SEC = 12 * 3600

CANDIDATES = [
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Tailscale" / "tailscale.exe",
    Path("/usr/bin/tailscale"),
    Path("/usr/local/bin/tailscale"),
]


def exe() -> Path | None:
    for p in CANDIDATES:
        if p.exists():
            return p
    return None


def _run(args: list[str], timeout: int = 90) -> tuple[int, str]:
    path = exe()
    if not path:
        return 1, "Tailscale が見つかりません"
    try:
        r = subprocess.run(
            [str(path)] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return 1, str(e)


def hostname() -> str | None:
    """この端末の Tailscale 上の名前（例: mypc.tailXXXX.ts.net）。"""
    code, out = _run(["status", "--json"], timeout=20)
    if code != 0:
        return None
    try:
        name = json.loads(out).get("Self", {}).get("DNSName", "")
    except ValueError:
        return None
    name = name.rstrip(".")
    return name or None


def days_left() -> float:
    if not CERT_FILE.exists():
        return -1.0
    try:
        from cryptography import x509

        cert = x509.load_pem_x509_certificate(CERT_FILE.read_bytes())
        delta = cert.not_valid_after_utc - datetime.datetime.now(datetime.timezone.utc)
        return delta.total_seconds() / 86400
    except Exception:
        return -1.0


def fetch(name: str) -> tuple[bool, str]:
    """証明書を取り直す。既に十分な期限があれば Tailscale 側が何もしない。"""
    CERT_DIR.mkdir(exist_ok=True)
    code, out = _run(
        ["cert", "--cert-file", str(CERT_FILE), "--key-file", str(KEY_FILE), name]
    )
    return code == 0, out.strip()


def ensure() -> tuple[Path, Path, str] | None:
    """使える証明書があれば (証明書, 鍵, 名前) を返す。無ければ None。"""
    if not exe():
        return None
    name = hostname()
    if not name:
        return None
    if days_left() < RENEW_BELOW_DAYS:
        ok, msg = fetch(name)
        if not ok:
            return None
    if not (CERT_FILE.exists() and KEY_FILE.exists()):
        return None
    return CERT_FILE, KEY_FILE, name


def start_renewal(reload_fn, log) -> None:
    """期限が近づいたら勝手に取り直し、動いたまま差し替える。

    サーバを止めずに証明書を入れ替えられるようにしておかないと、
    90日後に突然つながらなくなる。
    """
    name = hostname()
    if not name:
        return

    def loop():
        while True:
            threading.Event().wait(CHECK_EVERY_SEC)
            try:
                left = days_left()
                if left >= RENEW_BELOW_DAYS:
                    continue
                ok, msg = fetch(name)
                if ok:
                    reload_fn()
                    log.info("HTTPS証明書を更新しました（残り %.0f 日だったため）", left)
                else:
                    log.warning("HTTPS証明書の更新に失敗しました: %s", msg)
            except Exception as e:
                log.warning("HTTPS証明書の更新中に問題が起きました: %s", e)

    threading.Thread(target=loop, daemon=True, name="ts-cert-renew").start()


if __name__ == "__main__":
    p = exe()
    print("Tailscale:", p or "見つかりません")
    print("この端末の名前:", hostname() or "取得できません")
    got = ensure()
    if got:
        print(f"証明書: 使えます（残り {days_left():.0f} 日）")
        print(f"  {got[0]}")
    else:
        print("証明書: まだ使えません（管理画面で HTTPS を有効にしてください）")
