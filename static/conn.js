/* サーバとの WebSocket 接続。切れたら自動でつなぎ直す。
   ブラウザ標準の WebSocket だけを使う（外部ライブラリなし）。 */
class Conn {
  static PING_MS = 10000;   // 声をかける間隔
  static DEAD_MS = 30000;   // これだけ返事が無ければ切れたとみなす

  constructor(role) {
    this.role = role;
    this.sid = null;
    this.ws = null;
    this.handlers = {};
    this.retry = 0;
    this.closed = false;
    this.lastHeard = 0;
    this.watchTimer = null;
  }

  /* 相手が黙ったことに自分で気づくための見張り。

     パソコンの電源が落ちるとき、接続は正しく閉じられない。
     スマホ側は「切れた」と気づけず、OSのタイムアウト（数分）を待つことになる。
     実際、パソコンを再起動したあとカメラが戻るまで2分かかっていた。

     こちらから定期的に声をかけ、返事が途絶えたら自分から切って繋ぎ直す。 */
  startWatch() {
    clearInterval(this.watchTimer);
    this.lastHeard = Date.now();
    this.watchTimer = setInterval(() => {
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
      /* 画面が裏に回っていると、ブラウザがタイマーを間引く。
         そのまま数えると、黙っているのは相手ではなく自分なのに
         切れたと判断して、繋ぎ直しを延々と繰り返すことになる。 */
      if (typeof document !== 'undefined'
          && document.visibilityState !== 'visible') {
        this.lastHeard = Date.now();
        return;
      }
      if (Date.now() - this.lastHeard > Conn.DEAD_MS) {
        try { this.ws.close(); } catch (e) {}   // onclose が繋ぎ直しを始める
        return;
      }
      this.send({ t: 'ping' });
    }, Conn.PING_MS);
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
      this.startWatch();
      this.emit('open');
    };

    ws.onmessage = (ev) => {
      this.lastHeard = Date.now();
      let msg;
      try { msg = JSON.parse(ev.data); } catch (e) { return; }
      if (msg.t === 'welcome') { this.sid = msg.sid; }
      if (msg.t === 'pong') return;   // 生存確認の返事。ここで止める
      this.emit(msg.t, msg);
    };

    ws.onclose = () => {
      this.ws = null;
      clearInterval(this.watchTimer);
      this.watchTimer = null;
      this.emit('close');
      this.scheduleRetry();
    };

    ws.onerror = () => { try { ws.close(); } catch (e) {} };
  }

  scheduleRetry() {
    if (this.closed) return;
    // 1秒から始めて最大5秒まで間隔を広げる。
    // パソコンが再起動したあと、カメラ端末が戻ってくるのが遅いと
    // 見に行っても「繋がっていません」と出てしまう。
    const wait = Math.min(1000 * Math.pow(1.6, this.retry++), 5000);
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
