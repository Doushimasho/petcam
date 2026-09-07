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

RENEW_BELOW_DAYS = 25       # 残りがこの日数を切ったら更新する
CHECK_EVERY_SEC = 12 * 3600 # 証明書を持っているときの見張り間隔
RETRY_SEC = 20              # まだ取れていないときの再挑戦の間隔
RETRY_MAX_SEC = 600         # 再挑戦の間隔の上限

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


def serial() -> int | None:
    """いま手元にある証明書の識別番号。差し替えの要否を判断するのに使う。"""
    if not CERT_FILE.exists():
        return None
    try:
        from cryptography import x509

        return x509.load_pem_x509_certificate(CERT_FILE.read_bytes()).serial_number
    except Exception:
        return None


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


def start_watch(apply_fn, log, have_now: bool = False) -> None:
    """証明書を見張り、必要なら動かしたまま差し替える。

    見張る理由は2つある。

    1. **起動直後はTailscaleがまだ立ち上がっていないことがある。**
       パソコンの電源を入れた直後は特にそうで、その瞬間だけ証明書が取れない。
       そこで諦めると、自己署名のまま一日中動き続けることになる。
       （実際にそれが起きた。ブラウザに警告が出続けていた）

    2. 証明書は90日で切れる。期限が近づいたら取り直す必要がある。

    どちらも「取れたら差し替える」で同じ処理になるので、まとめて見張る。
    サーバを止めずに入れ替えられるので、利用者は何もしなくてよい。
    """
    current = serial() if have_now else None

    def loop():
        nonlocal current
        wait = 0 if current is None else CHECK_EVERY_SEC
        backoff = RETRY_SEC
        while True:
            if wait:
                threading.Event().wait(wait)
            try:
                got = ensure()
            except Exception:
                got = None

            if got:
                found = serial()
                if found is not None and found != current:
                    try:
                        apply_fn(got[0], got[1])
                        first = current is None
                        current = found
                        log.info(
                            "Tailscaleの正式な証明書に切り替えました（%s）" if first
                            else "証明書を新しいものに差し替えました（%s）",
                            got[2],
                        )
                    except Exception as e:
                        log.warning("証明書の差し替えに失敗しました: %s", e)

            if current is None:
                # まだ取れていない。間隔を少しずつ広げながら待つ
                wait = backoff
                backoff = min(backoff * 2, RETRY_MAX_SEC)
            else:
                wait = CHECK_EVERY_SEC
                backoff = RETRY_SEC

    threading.Thread(target=loop, daemon=True, name="ts-cert").start()
