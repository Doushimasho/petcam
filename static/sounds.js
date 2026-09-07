/* 呼び出し音を、その場で合成する。
   音源ファイルを持たないので配布物が増えず、読み込みの失敗も起きない。

   カメラ端末（実際に鳴らす側）と見る側（試聴する側）の両方が使う。

   音づくりの方針:
   - 立ち上がりをなだらかにする。同じ音量でも、急に鳴る音は驚かせる
   - 単発にせず連続させる。1音だけだと物音に紛れて気づかれない
   - 3種の音は「高さ」と「細かさ」をずらして、聞き分けられるようにする */

const PETCAM_SOUNDS = {
  // やわらかい下降3音。最後だけ長く残してベルらしく響かせる。
  // 高めの音域・中くらいの間隔。普段使い向け。
  chime: {
    type: 'sine',
    notes: [
      [1318.51, 0.00, 0.50],  // ミ
      [1046.50, 0.18, 0.50],  // ド
      [783.99,  0.36, 0.70],  // ソ
      [1318.51, 0.95, 0.50],  // 2回目。1回だと物音に紛れて気づかれない
      [1046.50, 1.13, 0.50],
      [783.99,  1.31, 1.10]
    ]
  },

  // 同じ高さを速く3回。いちばん細かく、気づいてほしいとき用。
  // 最後だけ少し伸ばして、切れ味が出すぎないようにする。
  call: {
    type: 'triangle',
    notes: [
      [880, 0.00, 0.14],
      [880, 0.16, 0.14],
      [880, 0.32, 0.22]
    ]
  },

  // 上って下りて、最後に高く伸ばす短いメロディ。
  // 低い音から始まるので、3種のなかで最も柔らかく聞こえる。
  melody: {
    type: 'sine',
    notes: [
      [523.25,  0.00, 0.30],  // ド
      [659.25,  0.16, 0.30],  // ミ
      [783.99,  0.32, 0.30],  // ソ
      [659.25,  0.50, 0.30],  // ミ
      [1046.50, 0.66, 0.95]   // ド（高）
    ]
  }
};

function createSoundPlayer() {
  let ctx = null;
  let out = null;

  function ensure() {
    if (!ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      try { ctx = new AC(); } catch (e) { return null; }
      // 音は重なって鳴るので、そのまま出すと大きい音量で割れる。
      // 出口で軽く抑えておく。
      try {
        out = ctx.createDynamicsCompressor();
        out.threshold.value = -10;
        out.ratio.value = 12;
        out.attack.value = 0.003;
        out.release.value = 0.25;
        out.connect(ctx.destination);
      } catch (e) {
        out = ctx.destination;
      }
    }
    if (ctx.state === 'suspended') ctx.resume().catch(() => {});
    return ctx;
  }

  /* 鳴らす。成功なら null、鳴らせなければ理由の文字列を返す。 */
  async function play(name, volume) {
    const c = ensure();
    if (!c) return 'この端末では音を鳴らせません';
    if (c.state === 'suspended') {
      try { await c.resume(); } catch (e) {}
    }
    if (c.state !== 'running') {
      // ブラウザは「一度も触られていないページ」に音を出させない
      return 'カメラ端末の画面を一度タップしてください';
    }

    const spec = PETCAM_SOUNDS[name];
    if (!spec) {
      // 黙って別の音に差し替えない。
      // 差し替えると「選んだ音と違う音が鳴る」という分かりにくい形になる。
      return 'この音を知らない画面です。カメラ端末のページを再読み込みしてください';
    }
    const peak = Math.min(Math.max(volume || 0.1, 0.02), 0.85);
    const start = c.currentTime + 0.03;

    for (const [freq, at, dur] of spec.notes) {
      const t0 = start + at;

      const gain = c.createGain();
      gain.gain.setValueAtTime(0.0001, t0);
      gain.gain.exponentialRampToValueAtTime(peak, t0 + 0.03);
      gain.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
      gain.connect(out);

      const osc = c.createOscillator();
      osc.type = spec.type;
      osc.frequency.value = freq;
      osc.connect(gain);
      osc.start(t0);
      osc.stop(t0 + dur + 0.05);

      // わずかに上の音を薄く重ねる。無いと痩せた電子音になる
      const hiGain = c.createGain();
      hiGain.gain.setValueAtTime(0.0001, t0);
      hiGain.gain.exponentialRampToValueAtTime(peak * 0.22, t0 + 0.03);
      hiGain.gain.exponentialRampToValueAtTime(0.0001, t0 + dur * 0.6);
      hiGain.connect(out);

      const hi = c.createOscillator();
      hi.type = 'sine';
      hi.frequency.value = freq * 2;
      hi.connect(hiGain);
      hi.start(t0);
      hi.stop(t0 + dur + 0.05);
    }
    return null;
  }

  return { ensure: ensure, play: play };
}
