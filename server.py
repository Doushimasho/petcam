"""ペットカメラ MVP のサーバ。

役割は2つだけ。
  1. カメラ端末と視聴ブラウザを引き合わせる（WebRTCのシグナリング）
  2. 状態（ONLINE / OFFLINE / CAMERA ON / OFF）を視聴側に配る

映像そのものはこのサーバを通らない。スマホとPCが直接つながる。
だからサーバのCPU負荷はほぼゼロで、遅延も最小になる。

通信はブラウザ標準の WebSocket だけを使う。
外部CDNのJavaScriptを読み込まないので、インターネットが無くてもLAN内で動く。
"""
import json
import logging
import logging.handlers
import os
import pathlib
import secrets
import ssl
import sys
import threading
import time
import uuid
from pathlib import Path

from flask import Flask, redirect, render_template, request, session, url_for
import simple_websocket

import make_cert
import ts_cert

BASE = Path(__file__).resolve().parent
CONFIG_FILE = BASE / "config.json"


def load_config() -> dict:
    """設定を読む。無ければ作る。

    PINと秘密鍵はコードに書かない。初回起動時にランダム生成して
    config.json に置く（config.json は .gitignore 済み）。
    """
    defaults = {
        # 12桁。外から届く場所に置くので、6桁では総当たりの的が小さすぎる。
        # 桁数を変えたければ config.json を書き換えればよい（長さの制限はない）。
        "pin": f"{secrets.randbelow(10**12):012d}",
        "secret_key": secrets.token_hex(32),
        "port": 8443,
        # 映像の経路を探すためのサーバ。
        # 自分が外からどう見えているかを教えてもらうだけで、映像は通らない。
        # 家の中だけで使うなら空にしてよい。
        # 誰も見ていない状態がこの秒数続いたら、カメラを止める
        "standby_after_sec": 60,
        "ice_servers": [
            {"urls": "stun:stun.l.google.com:19302"},
            {"urls": "stun:stun.cloudflare.com:3478"},
        ],
    }
    if CONFIG_FILE.exists():
        cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        missing = {k: v for k, v in defaults.items() if k not in cfg}
        if missing:  # 古い設定ファイルに、増えた項目を補う
            cfg.update(missing)
            CONFIG_FILE.write_text(
                json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        return cfg
    cfg = defaults
    CONFIG_FILE.write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return cfg


CONFIG = load_config()

# ---- 見張る区画 --------------------------------------------------------
# ケージの「トイレ」「エサ場」のように、映像の中の決まった場所を見張る。
# 位置は 0〜1 の割合で持つ。解像度や画質を変えても意味が変わらないため。
ZONES_FILE = BASE / "zones.json"


def load_zones() -> list[dict]:
    if not ZONES_FILE.exists():
        return []
    try:
        got = json.loads(ZONES_FILE.read_text(encoding="utf-8"))
        return got if isinstance(got, list) else []
    except ValueError:
        return []


def save_zones(zones: list[dict]) -> None:
    ZONES_FILE.write_text(
        json.dumps(zones, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def clean_zones(raw) -> list[dict] | None:
    """受け取った区画を検算する。おかしければ None。"""
    if not isinstance(raw, list) or len(raw) > 6:
        return None
    out = []
    for z in raw:
        if not isinstance(z, dict):
            return None
        try:
            item = {
                "id": str(z["id"])[:16],
                "name": str(z.get("name", ""))[:20],
                "x": min(max(float(z["x"]), 0.0), 1.0),
                "y": min(max(float(z["y"]), 0.0), 1.0),
                "w": min(max(float(z["w"]), 0.01), 1.0),
                "h": min(max(float(z["h"]), 0.01), 1.0),
            }
        except (KeyError, TypeError, ValueError):
            return None
        out.append(item)
    return out

app = Flask(__name__)
app.config["SECRET_KEY"] = CONFIG["secret_key"]
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True
# 画面のファイルを直したら、サーバを起動し直さなくても反映されるようにする
app.config["TEMPLATES_AUTO_RELOAD"] = True


# ---- 接続の台帳 --------------------------------------------------------
class Peer:
    """WebSocket接続1本ぶん。

    送信は複数のスレッドから起きる（別の接続の担当スレッドが横流しする）。
    フレームが混ざらないよう、送信だけロックで直列化する。
    """

    def __init__(self, sid: str, ws: simple_websocket.Server):
        self.sid = sid
        self.ws = ws
        self.role: str | None = None
        # 画面を開いていても、裏に回っていれば見ていないものとして数える。
        # カメラを動かし続けるかどうかの判断に使う。
        self.watching = True
        self._lock = threading.Lock()

    def send(self, obj: dict) -> None:
        try:
            with self._lock:
                self.ws.send(json.dumps(obj, ensure_ascii=False))
        except Exception:
            pass  # 切れた接続への送信は無視する。切断処理は受信側が行う


_lock = threading.Lock()
peers: dict[str, Peer] = {}
zones: list[dict] = load_zones()
CHIME_MIN_GAP = 1.5  # 音を鳴らす指示の最短間隔（秒）
state = {
    "camera_sid": None,
    "camera": "off",
    "error": None,
    "audio": False,
    "sounds": None,   # カメラ端末が知っている音の名前
    "zoom": None,     # ズームの範囲と現在の倍率（非対応なら None）
    "standby": True,  # 誰も見ていないときカメラを止めるか
    "detect": False,  # 見張りを動かしているか
    "last_chime": 0.0,
}


def snapshot() -> dict:
    with _lock:
        viewers = [p for p in peers.values() if p.role == "viewer"]
        return {
            "t": "state",
            "online": state["camera_sid"] is not None,
            "camera": state["camera"],
            "error": state["error"],
            "audio": state["audio"],
            "sounds": state["sounds"],
            "zoom": state["zoom"],
            "standby": state["standby"],
            "detect": state["detect"],
            "zones": zones,
            "viewers": len(viewers),
            # 実際に画面を見ている人の数。カメラを動かすかどうかはこれで決める
            "watchers": sum(1 for p in viewers if p.watching),
        }


def broadcast_state() -> None:
    msg = snapshot()
    with _lock:
        targets = list(peers.values())
    for p in targets:
        p.send(msg)


def send_to(sid: str, obj: dict) -> None:
    with _lock:
        p = peers.get(sid)
    if p:
        p.send(obj)


# ---- 総当たり対策 ------------------------------------------------------
# PINは6桁しかない。外から届く場所に置くなら、順番に試されたら破られる。
# 試行の速度を落とし、続けて失敗したIPを一定時間締め出す。
FAIL_LIMIT = 5      # この回数続けて外したら締め出す
FAIL_WINDOW = 600   # 失敗を数える期間（秒）
LOCK_BASE = 300     # 最初の締め出し時間（秒）。繰り返すたびに倍、最大1時間

_fail_lock = threading.Lock()
failures: dict[str, dict] = {}


def client_ip() -> str:
    """接続元の識別。

    将来トンネル越しに公開する場合、ここには中継サーバのアドレスしか
    来ない。そのときは中継が付ける転送元ヘッダを見る必要がある。
    ヘッダは詐称できるので、信頼する中継を決めてから読むこと。
    """
    return request.remote_addr or "unknown"


def lock_remaining(ip: str) -> int:
    """締め出しの残り秒。0なら締め出されていない。"""
    now = time.time()
    with _fail_lock:
        rec = failures.get(ip)
        if not rec:
            return 0
        return max(0, int(rec.get("until", 0) - now))


def note_failure(ip: str) -> None:
    now = time.time()
    with _fail_lock:
        rec = failures.setdefault(ip, {"count": 0, "first": now, "until": 0, "locks": 0})
        if now - rec["first"] > FAIL_WINDOW and rec["until"] < now:
            rec.update({"count": 0, "first": now})
        rec["count"] += 1
        if rec["count"] >= FAIL_LIMIT:
            rec["locks"] += 1
            wait = min(LOCK_BASE * (2 ** (rec["locks"] - 1)), 3600)
            rec["until"] = now + wait
            rec["count"] = 0
            rec["first"] = now
            logging.getLogger("werkzeug").warning(
                "PINの入力を続けて外したため %s を %d 秒締め出しました", ip, wait
            )


def clear_failures(ip: str) -> None:
    with _fail_lock:
        failures.pop(ip, None)


# ---- 画面 --------------------------------------------------------------
@app.after_request
def no_cache(resp):
    """古い画面を掴んだままになるのを防ぐ。

    ページを直しても表示が変わらない、という一番わかりにくい詰まり方を避ける。
    """
    # .js は環境によって text/javascript にも application/javascript にもなる。
    # 種類を並べて書くと取りこぼす。中身で判断する。
    ct = resp.mimetype or ""
    if ct.startswith("text/") or "javascript" in ct or "json" in ct:
        resp.headers["Cache-Control"] = "no-store"
    return resp


def authed() -> bool:
    return session.get("auth") is True


@app.route("/")
def index():
    if not authed():
        return redirect(url_for("login"))
    return redirect(url_for("viewer"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    nxt = request.args.get("next")
    nxt = nxt if nxt in ("/camera", "/viewer") else "/viewer"
    ip = client_ip()
    waiting = lock_remaining(ip)

    if request.method == "POST":
        if waiting:
            error = f"入力を続けて外したため、{waiting // 60 + 1}分ほど受け付けません"
        else:
            pin = (request.form.get("pin") or "").strip()[:64]
            # 比較にかかる時間からPINを推測されないようにする
            if secrets.compare_digest(pin, CONFIG["pin"]):
                clear_failures(ip)
                session["auth"] = True
                session.permanent = True
                logging.getLogger("werkzeug").info("%s がログインしました", ip)
                return redirect(nxt)
            note_failure(ip)
            time.sleep(0.7)  # 機械的な総当たりの速度を落とす
            waiting = lock_remaining(ip)
            error = (
                f"入力を続けて外したため、{waiting // 60 + 1}分ほど受け付けません"
                if waiting else "PINが違います"
            )
    elif waiting:
        error = f"入力を続けて外したため、{waiting // 60 + 1}分ほど受け付けません"

    return render_template("login.html", error=error, next=nxt)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/camera")
def camera():
    if not authed():
        return redirect(url_for("login", next="/camera"))
    return render_template(
        "camera.html",
        ice_servers=CONFIG.get("ice_servers", []),
        standby_after_sec=CONFIG.get("standby_after_sec", 60),
    )


@app.route("/viewer")
def viewer():
    if not authed():
        return redirect(url_for("login", next="/viewer"))
    return render_template("viewer.html", ice_servers=CONFIG.get("ice_servers", []))


# ---- シグナリング ------------------------------------------------------
# 映像を持っているのはカメラ側なので、offer はカメラが出す。
# 視聴者が1人増えるたびに、カメラ側がその視聴者専用の接続を1本作る。
RELAY = ("offer", "answer", "ice", "chime_result")


def handle_join(peer: Peer, msg: dict) -> None:
    role = msg.get("role")
    if role not in ("camera", "viewer"):
        return
    peer.role = role
    if role == "camera":
        with _lock:
            state["camera_sid"] = peer.sid
            state["error"] = None
            waiting = [p.sid for p in peers.values() if p.role == "viewer"]
        # 既に見ている人がいれば、その全員へ接続を張りに行かせる
        for v in waiting:
            peer.send({"t": "new_viewer", "sid": v})
    else:
        with _lock:
            cam = state["camera_sid"]
        if cam:
            send_to(cam, {"t": "new_viewer", "sid": peer.sid})
    broadcast_state()


def handle_message(peer: Peer, msg: dict) -> None:
    t = msg.get("t")
    if t == "join":
        handle_join(peer, msg)
    elif t in RELAY:
        to = msg.get("to")
        if not to:
            return
        out = dict(msg)
        out.pop("to", None)
        out["from"] = peer.sid
        send_to(to, out)
    elif t == "set_zones":
        # 見張る場所を決めるのは見る側。カメラ端末には触りに行かせない。
        if peer.role != "viewer":
            return
        cleaned = clean_zones(msg.get("zones"))
        if cleaned is None:
            return
        global zones
        zones = cleaned
        save_zones(zones)
        broadcast_state()
    elif t == "detect":
        # カメラ端末が測った、区画ごとの反応値。見ている人へそのまま配る。
        with _lock:
            if state["camera_sid"] != peer.sid:
                return
            targets = [p for p in peers.values() if p.role == "viewer"]
        out = {"t": "detect", "scores": msg.get("scores"), "busy": msg.get("busy")}
        for v in targets:
            v.send(out)
    elif t == "watching":
        # 画面が手前にあるかどうか。裏に回ったら、見ていない扱いにする。
        if peer.role != "viewer":
            return
        want = bool(msg.get("on"))
        if peer.watching != want:
            peer.watching = want
            broadcast_state()
    elif t == "camera_state":
        with _lock:
            if state["camera_sid"] != peer.sid:
                return
            state["camera"] = msg.get("state", "off")
            state["error"] = msg.get("error")
            state["audio"] = bool(msg.get("audio"))
            got = msg.get("sounds")
            if isinstance(got, list):
                state["sounds"] = [str(x)[:16] for x in got[:10]]
            if "standby" in msg:
                state["standby"] = bool(msg.get("standby"))
            if "detect" in msg:
                state["detect"] = bool(msg.get("detect"))
            z = msg.get("zoom")
            if isinstance(z, dict):
                try:
                    state["zoom"] = {
                        k: float(z[k]) for k in ("min", "max", "step", "value")
                    }
                except (KeyError, TypeError, ValueError):
                    state["zoom"] = None
            else:
                state["zoom"] = None
        broadcast_state()
    elif t == "cmd":
        # 視聴側からカメラ端末への指示。カメラ端末以外へは流さない。
        if peer.role != "viewer":
            return
        action = msg.get("action")
        if action not in (
            "camera_on", "camera_off", "audio_on", "audio_off", "chime", "zoom",
            "standby_on", "standby_off", "detect_on", "detect_off",
        ):
            return
        out = {"t": "cmd", "action": action, "from": peer.sid}
        if action == "zoom":
            try:
                out["value"] = float(msg.get("value"))
            except (TypeError, ValueError):
                return
        if action == "chime":
            # 連打で鳴らし続けられないようにする。
            # 相手はペットや子どものいる部屋なので、鳴らしすぎは害になる。
            now = time.time()
            with _lock:
                too_soon = now - state["last_chime"] < CHIME_MIN_GAP
                if not too_soon:
                    state["last_chime"] = now
            if too_soon:
                # 黙って捨てると「押したのに反応が無い」に見えるので返事をする
                peer.send({
                    "t": "chime_result",
                    "ok": False,
                    "reason": "少し間を置いてから押してください",
                })
                return
            out["sound"] = str(msg.get("sound", "chime"))[:16]
            try:
                vol = float(msg.get("volume", 0.15))
            except (TypeError, ValueError):
                vol = 0.15
            out["volume"] = min(max(vol, 0.02), 0.85)
        with _lock:
            cam = state["camera_sid"]
        if cam:
            send_to(cam, out)
    elif t == "sync":
        # 接続を張り直したいときに双方から呼ぶ。
        # カメラ側なら「今いる視聴者全員」を、視聴者側なら「自分」をカメラへ知らせる。
        #
        # force は「今の映像接続は壊れているので作り直せ」という申告。
        # これを伝えないと、カメラ側が「もう繋がっている」と判断して
        # 作り直しを見送り、映像が戻らないまま固まる。
        force = bool(msg.get("force"))
        if peer.role == "camera":
            with _lock:
                waiting = [p.sid for p in peers.values() if p.role == "viewer"]
            for v in waiting:
                peer.send({"t": "new_viewer", "sid": v, "force": force})
        elif peer.role == "viewer":
            with _lock:
                cam = state["camera_sid"]
            if cam:
                send_to(cam, {"t": "new_viewer", "sid": peer.sid, "force": force})
    elif t == "diag":
        # 映像がつながらないときの原因調べ。
        # どんな経路の候補を出し合ったのかを記録に残す。
        text = str(msg.get("text", ""))[:200]
        logging.getLogger("werkzeug").info(
            "[診断 %s/%s] %s", peer.role or "?", peer.sid[:6], text
        )
    elif t == "ping":
        peer.send({"t": "pong"})


def on_close(peer: Peer) -> None:
    with _lock:
        peers.pop(peer.sid, None)
        was_camera = state["camera_sid"] == peer.sid
        if was_camera:
            state["camera_sid"] = None
            state["camera"] = "off"
            state["error"] = None
            state["audio"] = False
            state["sounds"] = None
            state["zoom"] = None
            state["detect"] = False
        cam = state["camera_sid"]
    if peer.role == "viewer" and cam:
        send_to(cam, {"t": "viewer_left", "sid": peer.sid})
    broadcast_state()


def ws_endpoint():
    if not authed():
        return "", 403
    ws = simple_websocket.Server(request.environ, ping_interval=20)
    peer = Peer(uuid.uuid4().hex[:12], ws)
    with _lock:
        peers[peer.sid] = peer
    peer.send({"t": "welcome", "sid": peer.sid})
    peer.send(snapshot())
    try:
        while True:
            raw = ws.receive()
            if raw is None:
                break
            try:
                msg = json.loads(raw)
            except (ValueError, TypeError):
                continue
            if isinstance(msg, dict):
                handle_message(peer, msg)
    except (simple_websocket.ConnectionClosed, OSError):
        pass
    finally:
        on_close(peer)
    return ""


app.add_url_rule("/ws", "ws", ws_endpoint, websocket=True)


# ---- 起動 --------------------------------------------------------------
def ensure_output() -> bool:
    """コンソールが無い状態でも動くようにする。

    自動起動では画面を出さずに走らせるため、print() の書き込み先が
    存在しない。そのまま呼ぶと例外で落ちるので、捨て先を用意しておく。
    表示したい内容は、画面ではなく記録のほうへ回す。

    画面がある場合は True を返す。
    """
    has_console = sys.stdout is not None and sys.stderr is not None
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
    return has_console


def disable_console_quick_edit() -> None:
    """黒い画面の「選択モード」を無効にする。

    Windowsのコンソールはクリックすると選択モードに入り、その間は
    出力が止まる。出力が止まると、書き込もうとしたプログラム自体も止まる。
    つまり黒い画面をうっかりクリックしただけで、カメラが無反応になる。
    常設カメラとしては事故なので、最初から選択できないようにしておく。

    （文字をコピーしたいときは 右クリック → 編集 → 範囲指定 を使う）
    """
    if os.name != "nt":
        return
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-10)  # STD_INPUT_HANDLE
        mode = wintypes.DWORD()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return
        quick_edit, extended = 0x0040, 0x0080
        kernel32.SetConsoleMode(handle, (mode.value & ~quick_edit) | extended)
    except Exception:
        pass  # コンソールが無い環境では何もしない


def route_access_log_to_file() -> pathlib.Path:
    """通信の記録を、黒い画面ではなくファイルへ書く。

    動作中のサーバが黒い画面へ一切書き込まなくなるので、
    画面側が何かの理由で止まっても、カメラは動き続ける。
    """
    path = BASE / "petcam.log"
    handler = logging.handlers.RotatingFileHandler(
        path, maxBytes=1_000_000, backupCount=2, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    log = logging.getLogger("werkzeug")
    log.handlers.clear()
    log.addHandler(handler)
    log.propagate = False
    return path


def port_in_use(port: int) -> bool:
    """既に別のサーバが同じポートを使っていないか調べる。

    Windows では同じポートに二重にバインドできてしまうことがある。
    そうなると古いほうが応答し続け、直したはずの画面が出ない、という
    最も原因の掴みにくい詰まり方をする。起動時に弾いておく。
    """
    import socket as _s

    with _s.socket(_s.AF_INET, _s.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def read_port() -> int:
    """--port が指定されていればそれを使う。開発中に本番と別ポートで試すため。"""
    argv = sys.argv
    if "--port" in argv:
        i = argv.index("--port")
        if i + 1 < len(argv) and argv[i + 1].isdigit():
            return int(argv[i + 1])
    return CONFIG["port"]


def main() -> None:
    has_console = ensure_output()
    disable_console_quick_edit()
    log_path = route_access_log_to_file()

    def say(text: str = "") -> None:
        """画面があれば画面へ、無ければ記録へ。"""
        if has_console:
            print(text)
        elif text.strip():
            logging.getLogger("werkzeug").info(text.strip())

    port = read_port()
    if port_in_use(port):
        say(f"ポート {port} は既に使われています。")
        say("先に起動しているサーバの黒い画面を × で閉じてから、")
        say("もう一度この起動ファイルを実行してください。")
        say("（止まっている黒い画面は Ctrl+C では閉じないことがあります）")
        sys.exit(1)

    # --http は動作確認用。localhost は HTTPS でなくても
    # ブラウザが安全なコンテキストとして扱うのでカメラが開ける。
    # 他の端末からは見えないよう 127.0.0.1 にだけ待ち受ける。
    if "--http" in sys.argv:
        say("=" * 60)
        say("  PET CAMERA （動作確認モード / このPC内だけ）")
        say("=" * 60)
        say(f"  PIN      : {CONFIG['pin']}")
        say(f"  カメラ   : http://127.0.0.1:{port}/camera")
        say(f"  視聴     : http://127.0.0.1:{port}/viewer")
        say("  ※ スマホからは見えません。実機で使うときは --http を外してください。")
        say("=" * 60)
        app.run(host="127.0.0.1", port=port, threaded=True)
        return

    ip = make_cert.local_ip()

    # Tailscale の正式な証明書が使えるならそちらを使う。
    # 使えなければ、ひとまず自己署名で動き始める。
    #
    # パソコンの電源を入れた直後は、Tailscale がまだ立ち上がっていないことがある。
    # その瞬間に諦めてしまうと、自己署名のまま一日中動き続けることになるので、
    # 下の見張りが用意のできた時点で、動かしたまま差し替える。
    ts = ts_cert.ensure()
    if ts:
        cert, key, ts_name = ts
    else:
        cert, key = make_cert.ensure(ip)
        ts_name = None

    # 証明書を入れ替えられるように、SSLの設定を自分で持つ。
    # こうしておかないと、サーバを止めるまで差し替えられない。
    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_ctx.load_cert_chain(str(cert), str(key))

    log = logging.getLogger("werkzeug")
    ts_cert.start_watch(
        lambda c, k: ssl_ctx.load_cert_chain(str(c), str(k)),
        log,
        have_now=ts_name is not None,
    )

    say("=" * 60)
    say("  PET CAMERA サーバを起動しました")
    say("=" * 60)
    say(f"  PIN            : {CONFIG['pin']}")
    say()
    if ts_name:
        say("  どこからでも（Tailscaleに繋いだ端末）")
        say(f"    スマホ（カメラ）: https://{ts_name}:{port}/camera")
        say(f"    PC（視聴）      : https://{ts_name}:{port}/viewer")
        say()
        say(f"  証明書は正式なものです（残り {ts_cert.days_left():.0f} 日・自動更新）。")
        say("  警告は出ません。上のアドレスを使ってください。")
        say()
        say(f"  ※ 家の中だけで使う場合の直接アドレスは https://{ip}:{port}/")
        say("     こちらは警告が出ます。普段は上のアドレスで統一してください。")
    else:
        say(f"  スマホ（カメラ）: https://{ip}:{port}/camera")
        say(f"  PC（視聴）      : https://{ip}:{port}/viewer")
        say()
        say('  ※ 初回は「接続はプライベートではありません」の警告が出ます。')
        say("     詳細設定 →「安全でないページに移動」で進んでください。")
        say("     自己署名証明書のため出る警告で、LAN内では想定どおりです。")
        if ts_cert.exe():
            say()
            say("  ※ Tailscaleの正式な証明書はまだ取れていません。")
            say("     用意ができ次第、サーバを止めずに自動で切り替えます。")
    say()
    say(f"  記録: {log_path}")
    say("=" * 60)

    app.run(host="0.0.0.0", port=port, ssl_context=ssl_ctx, threaded=True)


if __name__ == "__main__":
    main()
