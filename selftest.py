"""サーバの動作をブラウザ抜きで確認する。

  python selftest.py

映像そのものは実機でしか確かめられないが、
「認証」「状態の伝わり方」「シグナリングの中継」はここで確認できる。
本体を直したあとに一度走らせると、壊していないか分かる。
"""
import http.cookiejar
import json
import os
import sys
import threading
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import simple_websocket  # noqa: E402

import server  # noqa: E402

PORT = 8799
BASE = f"http://127.0.0.1:{PORT}"
PIN = server.CONFIG["pin"]
fails: list[str] = []

# どこかで待ち続けたまま終わらない、という止まり方を避ける
watchdog = threading.Timer(
    45, lambda: (print("!! 45秒を過ぎました。どこかで止まっています"), os._exit(2))
)
watchdog.daemon = True
watchdog.start()


def check(name: str, ok: bool, extra: object = "") -> None:
    print(("  OK  " if ok else "  NG  ") + name + ("" if ok else f"   <- {extra}"))
    if not ok:
        fails.append(name)


def login(pin: str) -> tuple[str, str]:
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    body = urllib.parse.urlencode({"pin": pin}).encode()
    res = opener.open(BASE + "/login", body)
    return res.geturl(), "; ".join(f"{c.name}={c.value}" for c in jar)


def connect(cookie: str) -> simple_websocket.Client:
    return simple_websocket.Client(
        f"ws://127.0.0.1:{PORT}/ws", headers={"Cookie": cookie}
    )


def wait_for(client, kind: str, timeout: float = 3.0) -> dict | None:
    """指定した種類のメッセージが来るまで読み飛ばす。"""
    limit = time.time() + timeout
    while time.time() < limit:
        raw = client.receive(timeout=max(0.05, limit - time.time()))
        if raw is None:
            break
        msg = json.loads(raw)
        if msg.get("t") == kind:
            return msg
    return None


def main() -> int:
    threading.Thread(
        target=lambda: server.app.run(host="127.0.0.1", port=PORT, threaded=True),
        daemon=True,
    ).start()
    time.sleep(1.5)

    print("--- 認証 ---")
    url, _ = login("000000" if PIN != "000000" else "999999")
    check("間違ったPINは弾かれる", "/login" in url, url)
    url, cookie = login(PIN)
    check("正しいPINで入れる", url.endswith("/viewer"), url)
    try:
        simple_websocket.Client(f"ws://127.0.0.1:{PORT}/ws")
        check("未認証のWebSocketは拒否される", False, "つながってしまった")
    except Exception:
        check("未認証のWebSocketは拒否される", True)

    print("--- 総当たり対策 ---")
    wrong = "000000" if PIN != "000000" else "999999"
    for _ in range(server.FAIL_LIMIT):
        login(wrong)
    url, _ = login(wrong)
    check("続けて外すと締め出される", "/login" in url, url)
    body = urllib.request.urlopen(BASE + "/login").read().decode("utf-8")
    check("締め出し中はその旨が出る", "受け付けません" in body)
    url, _ = login(PIN)
    check("締め出し中は正しいPINでも入れない", "/login" in url, url)
    server.clear_failures("127.0.0.1")
    url, cookie = login(PIN)
    check("解除されれば入れる", url.endswith("/viewer"), url)

    print("--- 状態 ---")
    viewer = connect(cookie)
    check("welcomeが来る", json.loads(viewer.receive(timeout=3))["t"] == "welcome")
    st = json.loads(viewer.receive(timeout=3))
    check("カメラ未接続なら OFFLINE", st["online"] is False, st)
    viewer.send(json.dumps({"t": "join", "role": "viewer"}))
    wait_for(viewer, "state")

    cam = connect(cookie)
    cam.receive(timeout=3)
    cam.receive(timeout=3)
    cam.send(json.dumps({"t": "join", "role": "camera"}))
    st = wait_for(viewer, "state")
    check("カメラ接続で ONLINE になる", bool(st and st["online"]), st)

    invite = wait_for(cam, "new_viewer")
    check("カメラへ視聴者が知らされる", invite is not None, invite)
    if invite is None:
        return 1

    cam.send(json.dumps({"t": "camera_state", "state": "on"}))
    st = wait_for(viewer, "state")
    check("CAMERA ON が視聴側へ伝わる", bool(st and st["camera"] == "on"), st)

    cam.send(json.dumps({
        "t": "camera_state", "state": "on", "sounds": ["chime", "call", "melody"]
    }))
    st = wait_for(viewer, "state")
    check(
        "カメラが鳴らせる音の一覧が伝わる",
        bool(st and st.get("sounds") == ["chime", "call", "melody"]),
        st,
    )

    print("--- 遠隔操作 ---")
    viewer.send(json.dumps({"t": "cmd", "action": "camera_off"}))
    cmd = wait_for(cam, "cmd")
    check("CAMERA OFF の指示がカメラへ届く", bool(cmd and cmd["action"] == "camera_off"), cmd)
    viewer.send(json.dumps({
        "t": "cmd", "action": "chime", "sound": "melody", "volume": 0.65
    }))
    cmd = wait_for(cam, "cmd")
    check("音を鳴らす指示が種類と音量ごと届く",
          bool(cmd and cmd.get("sound") == "melody" and abs(cmd.get("volume", 0) - 0.65) < 0.01),
          cmd)
    viewer.send(json.dumps({"t": "cmd", "action": "chime", "sound": "melody"}))
    res = wait_for(viewer, "chime_result", timeout=2.0)
    check("続けて押すと抑えられ、その旨が返る",
          bool(res and res.get("ok") is False), res)
    viewer.send(json.dumps({"t": "cmd", "action": "reboot"}))
    check("知らない指示は無視される", wait_for(cam, "cmd", timeout=1.0) is None)
    cam.send(json.dumps({"t": "cmd", "action": "camera_off"}))
    check("カメラ側からの指示は流れない", wait_for(cam, "cmd", timeout=1.0) is None)

    print("--- 見張る区画 ---")
    # 実際に使っている区画設定を壊さないよう、控えを取って最後に戻す
    zones_file = server.ZONES_FILE
    saved = zones_file.read_text(encoding="utf-8") if zones_file.exists() else None
    try:
        viewer.send(json.dumps({"t": "set_zones", "zones": [
            {"id": "litter", "name": "トイレ", "x": 0.1, "y": 0.6, "w": 0.3, "h": 0.3}
        ]}))
        st = wait_for(viewer, "state")
        check("区画の指定が保存され、全員へ配られる",
              bool(st and st.get("zones") and st["zones"][0]["id"] == "litter"), st)
        check("区画がファイルに残る", zones_file.exists())

        before = len(st["zones"]) if st and st.get("zones") else 0
        viewer.send(json.dumps({"t": "set_zones", "zones": [{"id": "x"}]}))
        check("欠けた区画は受け付けない",
              wait_for(viewer, "state", timeout=1.0) is None)
        cam.send(json.dumps({"t": "set_zones", "zones": []}))
        check("カメラ側からは区画を変えられない",
              wait_for(viewer, "state", timeout=1.0) is None)

        cam.send(json.dumps({
            "t": "detect", "scores": {"litter": 42.5}, "busy": {"litter": True}
        }))
        got = wait_for(viewer, "detect")
        check("反応値が視聴側へ届く",
              bool(got and got["scores"]["litter"] == 42.5 and got["busy"]["litter"]),
              got)
        viewer.send(json.dumps({"t": "detect", "scores": {"litter": 1}}))
        check("視聴側からの反応値は流れない",
              wait_for(viewer, "detect", timeout=1.0) is None)

        viewer.send(json.dumps({"t": "cmd", "action": "detect_on"}))
        cmd = wait_for(cam, "cmd")
        check("見張りの開始指示がカメラへ届く",
              bool(cmd and cmd["action"] == "detect_on"), cmd)
    finally:
        if saved is None:
            zones_file.unlink(missing_ok=True)
        else:
            zones_file.write_text(saved, encoding="utf-8")
        server.zones = server.load_zones()

    print("--- 自動スタンバイ ---")
    viewer.send(json.dumps({"t": "watching", "on": False}))
    st = wait_for(viewer, "state")
    check("画面を裏に回すと見ている人が減る",
          bool(st and st.get("watchers") == 0 and st.get("viewers") == 1), st)
    viewer.send(json.dumps({"t": "watching", "on": True}))
    st = wait_for(viewer, "state")
    check("戻すと見ている人に数え直される",
          bool(st and st.get("watchers") == 1), st)
    cam.send(json.dumps({"t": "camera_state", "state": "standby", "standby": True}))
    st = wait_for(viewer, "state")
    check("待機中であることが視聴側へ伝わる",
          bool(st and st.get("camera") == "standby" and st.get("standby") is True), st)
    viewer.send(json.dumps({"t": "cmd", "action": "standby_off"}))
    cmd = wait_for(cam, "cmd")
    check("自動スタンバイの切替がカメラへ届く",
          bool(cmd and cmd["action"] == "standby_off"), cmd)
    cam.send(json.dumps({"t": "camera_state", "state": "on", "standby": False}))
    st = wait_for(viewer, "state")
    check("切ったことが視聴側へ伝わる",
          bool(st and st.get("standby") is False), st)

    print("--- ズーム ---")
    cam.send(json.dumps({
        "t": "camera_state", "state": "on",
        "zoom": {"min": 1, "max": 8, "step": 0.1, "value": 1},
    }))
    st = wait_for(viewer, "state")
    check("ズームの範囲が視聴側へ伝わる",
          bool(st and st.get("zoom") and st["zoom"]["max"] == 8.0), st)
    viewer.send(json.dumps({"t": "cmd", "action": "zoom", "value": 2.5}))
    cmd = wait_for(cam, "cmd")
    check("ズームの指示が倍率ごと届く",
          bool(cmd and cmd["action"] == "zoom" and abs(cmd.get("value", 0) - 2.5) < 0.01),
          cmd)
    viewer.send(json.dumps({"t": "cmd", "action": "zoom", "value": "たくさん"}))
    check("数値でないズーム指示は無視される",
          wait_for(cam, "cmd", timeout=1.0) is None)
    cam.send(json.dumps({"t": "camera_state", "state": "on", "zoom": None}))
    st = wait_for(viewer, "state")
    check("非対応なら zoom は空で伝わる", bool(st and st.get("zoom") is None), st)

    print("--- つなぎ直しの要求 ---")
    viewer.send(json.dumps({"t": "sync", "force": True}))
    inv = wait_for(cam, "new_viewer")
    check("force付きの要求がカメラへ伝わる", bool(inv and inv.get("force") is True), inv)
    viewer.send(json.dumps({"t": "sync"}))
    inv = wait_for(cam, "new_viewer")
    check("force無しの要求は force=False で届く", bool(inv and inv.get("force") is False), inv)

    print("--- シグナリングの中継 ---")
    cam.send(json.dumps({"t": "offer", "to": invite["sid"], "sdp": {"sdp": "X"}}))
    offer = wait_for(viewer, "offer")
    check("offer が視聴側へ届く", bool(offer and offer["sdp"]["sdp"] == "X"), offer)
    check("offer に送信元が付く", bool(offer and offer.get("from")), offer)

    viewer.send(json.dumps({"t": "answer", "to": offer["from"], "sdp": {"sdp": "Y"}}))
    ans = wait_for(cam, "answer")
    check("answer がカメラ側へ戻る", bool(ans and ans["sdp"]["sdp"] == "Y"), ans)

    viewer.send(json.dumps({"t": "ice", "to": offer["from"], "candidate": {"c": "Z"}}))
    ice = wait_for(cam, "ice")
    check("ICE が中継される", bool(ice and ice["candidate"]["c"] == "Z"), ice)

    print("--- 切断 ---")
    cam.close()
    st = wait_for(viewer, "state", timeout=4)
    check("カメラ切断で OFFLINE に戻る", bool(st and st["online"] is False), st)
    check("そのとき CAMERA も OFF に戻る", bool(st and st["camera"] == "off"), st)
    viewer.close()

    print()
    print("結果: " + ("全て通過" if not fails else f"{len(fails)}件 失敗 -> {fails}"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
