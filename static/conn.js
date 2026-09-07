/* サーバとの WebSocket 接続。切れたら自動でつなぎ直す。
   ブラウザ標準の WebSocket だけを使う（外部ライブラリなし）。 */
class Conn {
  constructor(role) {
    this.role = role;
    this.sid = null;
    this.ws = null;
    this.handlers = {};
    this.retry = 0;
    this.closed = false;
  }

  on(type, fn) { this.handlers[type] = fn; return this; }

  emit(type, data) {
    const fn = this.handlers[type];
    if (fn) fn(data);
  }

  start() {
    const url = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws';
    let ws;
    try {
      ws = new WebSocket(url);
    } catch (e) {
      this.scheduleRetry();
      return;
    }
    this.ws = ws;

    ws.onopen = () => {
      this.retry = 0;
      this.send({ t: 'join', role: this.role });
      this.emit('open');
    };

    ws.onmessage = (ev) => {
      let msg;
      try { msg = JSON.parse(ev.data); } catch (e) { return; }
      if (msg.t === 'welcome') { this.sid = msg.sid; }
      this.emit(msg.t, msg);
    };

    ws.onclose = () => {
      this.ws = null;
      this.emit('close');
      this.scheduleRetry();
    };

    ws.onerror = () => { try { ws.close(); } catch (e) {} };
  }

  scheduleRetry() {
    if (this.closed) return;
    // 1秒から始めて最大10秒まで間隔を広げる
    const wait = Math.min(1000 * Math.pow(1.6, this.retry++), 10000);
    setTimeout(() => this.start(), wait);
  }

  send(obj) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(obj));
      return true;
    }
    return false;
  }
}
