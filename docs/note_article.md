# 余っていたスマホを、ペットカメラにした（作り方も置いておきます）

猫を留守番させるとき、様子が見たい。
市販のペットカメラを買えば済む話だが、引き出しに使っていないスマホが眠っていた。
カメラもWi-Fiも付いていて、電源につなげば動き続ける。これを使わない手はない。

作ったものがこれです。

- **費用は0円。** クラウドも契約も不要
- **見る側はブラウザだけ。** アプリのインストールは要らない
- **カメラ側もブラウザだけ。** 専用アプリを作らなくていい
- **外出先からも見られる。** しかも自宅をインターネットに公開せずに
- 遅延は0.1〜0.3秒

コードは公開しているので、同じものがそのまま作れます。
**ペットカメラとしても、赤ちゃんや家族の見守りカメラとしても使えます。**

この記事は、その導入手順が中心です。

---

## できること

| | |
|---|---|
| ライブ映像 | 遅延0.1〜0.3秒 |
| 遠隔ON/OFF | 手元からカメラを止める・動かす |
| 音声 | 部屋の音を聞く。手元のボタンでオン/オフ |
| 呼び出し音 | カメラ端末から音を鳴らして反応を見る |
| スナップショット | 見ている画面を保存 |
| 画質切替 | 標準 / 省電力（発熱対策） |
| 画面消灯 | カメラ端末の画面を消したまま配信を続ける |
| 自動復帰 | 映像が止まっても10秒ほどで戻る |

---

## 必要なもの

- **カメラにするAndroidスマートフォン**（Chromeが動けばよい）
- **PC**（Windows / macOS / Linux）。サーバ役
- 両方が同じWi-Fiにつながっていること

iPhoneをカメラにするのは勧めません。画面ロックやアプリ切替でカメラが止まる制約が強いためです。
**見る側はiPhoneでも問題ありません。**

---

## 手順1：PCの準備

### Pythonが入っているか確認する

コマンドプロンプト（またはターミナル）で次を実行します。

```bash
python --version
```

`Python 3.10.0` 以上と表示されればOKです。
「認識されていません」と出たら [python.org](https://www.python.org/downloads/) から入れてください。
Windowsでインストールするときは、最初の画面の
**「Add python.exe to PATH」にチェックを入れる**のを忘れずに。

### コードを取ってくる

```bash
git clone （リポジトリのURL）
cd petcam
```

Gitを使っていない場合は、GitHubのページの緑色の **Code** ボタン →
**Download ZIP** でも構いません。展開したフォルダに移動してください。

### 必要な部品を入れる

```bash
pip install -r requirements.txt
```

入るのは `Flask` `simple-websocket` `cryptography` の3つだけです。
数十秒で終わります。

## 手順2：起動する

Windowsなら `start.bat` をダブルクリック。それ以外は次のとおり。

```bash
python server.py
```

黒い画面に、**PIN**と**アクセスするアドレス**が出ます。

```
============================================================
  PET CAMERA サーバを起動しました
============================================================
  PIN            : 123456789012

  スマホ（カメラ）: https://192.168.x.x:8443/camera
  PC（視聴）      : https://192.168.x.x:8443/viewer
============================================================
```

**この黒い画面は閉じないでください。** 閉じるとカメラも止まります。

初回はWindowsがネットワークの許可を聞いてきます。
**「プライベートネットワーク」にチェックを入れて許可**してください。
ここを許可しないとスマホから繋がりません。

PINは初回起動時にランダムで作られ、コードには書かれていません。

## 手順3：カメラにするスマホを設定する

1. スマホを**PCと同じWi-Fi**につなぐ
2. Chromeで、表示されたアドレスの `/camera` を開く
3. 「接続はプライベートではありません」と警告が出ます
   → **詳細設定 → 安全でないページに移動**
   （自分のPCが出した証明書なので、この警告で合っています。手順5で消えます）
4. PINを入力
5. **CAMERA ON を押して、カメラの使用を許可**

**カメラの許可を求められるのは最初の1回だけ**です。以後は手元から遠隔でON/OFFできます。

### 設置のコツ

常設で問題になるのは発熱と電池です。効くものだけ挙げます。

| | 理由 |
|---|---|
| 電源につなぐ | 必須 |
| 画面の明るさを最低にする | 発熱と電力の主因 |
| ケースを外す | 放熱。長時間だと効きます |
| 通知・着信を切る | 着信画面がページを覆うとカメラが止まる |
| 画面の自動回転をオフ | 映像が回るのを防ぐ |

画面は**1分触らないと自動的に真っ暗になります**（配信は続きます）。
プレビューを描き続けるのが発熱の主因なので、描画だけを止めています。

## 手順4：見る

PCのブラウザで `/viewer` を開き、同じPINを入れる。これだけです。
何台からでも同時に見られます。

## 手順5：外出先から見る

ここが一番の山場ですが、やることは多くありません。

自宅をインターネットに公開するのは避けたいので、**Tailscale**を使います。
自分の端末同士だけを繋ぐ仕組みで、個人利用は無料です。

1. **PC**、**カメラのスマホ**、**見る端末**の3つにTailscaleを入れ、同じアカウントでログイン
2. 管理画面の **DNS → HTTPS Certificates** を有効にする
3. サーバを起動し直す

これだけで、サーバが自動的に**正式なHTTPS証明書**を取得し、

```
https://端末名.ネットワーク名.ts.net:8443/viewer
```

というアドレスで、**家でも外でも同じURL・証明書の警告なし**で使えるようになります。
証明書は90日で切れますが、期限が近づくと自動で取り直します。

家族に見せたい場合は、管理画面の **Users** から招待リンクを送れば、
相手は自分のアカウントのままで参加できます。

---

## 動いているか確かめる

映像以外の部分が壊れていないかを、機械的に確認できます。

```bash
python selftest.py
```

認証、締め出し、状態の伝わり方、遠隔操作、つなぎ直し、音の指示など
26項目を確認します。全部 `OK` になれば、少なくとも壊れてはいません。

## 更新するとき

```bash
git pull
```

サーバを起動し直せば反映されます。
**PINや証明書は `config.json` と `certs/` に入っていて、更新では消えません。**

---

## つまずきやすいのは、この3つです

実際に私が全部踏みました。

**1. カメラのスマホにTailscaleを入れ忘れる**

いちばん分かりにくい詰まり方をします。
状態表示は `DEVICE ONLINE` `CAMERA ON` と正しく出るのに、**映像だけ来ない**。

映像はサーバを通らず端末同士が直接やりとりするので、
サーバに繋がっていても、カメラ本体に届かなければ映りません。

**2. Androidのバッテリー最適化**

設定 → アプリ → Tailscale → バッテリー → **「制限なし」**にしてください。
ここを外さないと、OSが省電力のためにVPNを勝手に切ります。
家では映るのに外出先から繋がらない、という形で出ます。

**3. ゲストネットワークにつないでいる**

端末同士の通信が遮断されているので、そもそも繋がりません。

---

## 作ってみて、詰まったこと

技術的に難しかったのは、実はWebRTCではありませんでした。
**壊れ方が静かなこと**でした。3つだけ紹介します。

### 黒い画面をクリックしたら、サーバが死んだ

スマホから繋がらない。ファイアウォールも許可済み。プロセスも動いている。
なのにPC自身からも繋がらない。

原因は、Windowsのコンソールでした。
**あの黒い画面はクリックすると文字の選択モードに入り、その間は出力が止まる。
出力が止まると、書き込もうとしたプログラム自体も止まる。**

起動メッセージを表示しようとしたところで固まっていました。
いまは選択モードを無効にし、動作中の記録は画面ではなくファイルに書いています。

### バグを直したら、別のバグを作った

接続の申し込みが二重に飛ぶ不具合を直すため、
「すでに接続中の相手には重ねて申し込まない」という判定を入れました。

そのせいで、Wi-Fiが一瞬切れたあと**永久に映像が戻らなくなりました**。
カメラ側の古い接続が、まだ自分を「接続済み」だと思っていたためです。

**片方だけが切断に気づいている状態は、普通に起きます。**
にもかかわらず、自分の見え方を根拠に相手の要求を却下していました。

いまは、相手が「壊れている」と言ってきたら自分の状態に関わらず作り直します。
さらに、**映像が実際に進んでいるかを2秒ごとに確認する見張り**を付けました。
状態表示は当てになりません。信用できるのは実際の動きだけでした。

### 選んだ音と、違う音が鳴る

呼び出し音を3種類にしたのに、メロディを選ぶとチャイムが鳴る。
手元の試聴では正しく鳴るのに、部屋のスマホからは違う音が出ました。

カメラ側の画面が古いままで、新しく増えた音を知らなかったのが原因です。
JavaScriptがキャッシュされていたこと、そして
**知らない音を黙って既定の音に差し替えていたこと**が重なっていました。

いまは差し替えず、「その音を知らない画面です」と理由を返します。

> 代わりのもので黙って済ませると、壊れていることが見えなくなる。

---

## まとめ

作りながら学んだことを3つ挙げるなら、これになります。

> 自分の状態を根拠に、相手の要求を却下してはいけない。
>
> スイッチは、使う人が手を伸ばせる場所に置く。
>
> 代わりのもので黙って済ませない。

どれも当たり前のことなのに、動くものを作っている最中はきれいに見落とします。

余っているスマホが引き出しにあるなら、試してみてください。
費用はかかりませんし、うまくいかなくてもスマホは元に戻ります。

**リポジトリ：（ここにURL）**

READMEに、この記事より詳しい手順とトラブル対応をまとめてあります。

---
---

# (English) Turning a Spare Phone into a Pet Camera

I wanted to check on my cat while away from home. Instead of buying a pet camera,
I used an Android phone that had been sitting unused in a drawer.

- **Free.** No cloud service, no subscription
- **Viewers only need a browser.** No app to install
- **The camera phone only needs a browser too.** No app to build
- **Works from outside your home** without exposing your house to the internet
- Latency is 0.1–0.3 seconds

The code is open source, so you can build the same thing.
It works as a **pet camera or a baby/family monitor**.

## What it does

| | |
|---|---|
| Live video | 0.1–0.3s latency |
| Remote on/off | Start and stop the camera from your phone or PC |
| Audio | Listen to the room. Toggled remotely |
| Chime | Play a sound from the camera phone to get their attention |
| Snapshot | Save the current frame |
| Quality | Standard / Power-saving |
| Screen off | The camera phone goes dark while still streaming |
| Auto-recovery | If video stalls, it reconnects itself in about 10 seconds |

## What you need

- **An Android phone** to act as the camera (Chrome is all it needs)
- **A PC** (Windows / macOS / Linux) to run the server
- Both on the same Wi-Fi

Do not use an iPhone as the camera. iOS stops the camera when the screen locks
or you switch apps. **Viewing on an iPhone is fine.**

## Step 1: Prepare the PC

Check that Python is installed:

```bash
python --version
```

You need 3.10 or newer. If it is missing, get it from
[python.org](https://www.python.org/downloads/).
On Windows, check **"Add python.exe to PATH"** on the first installer screen.

Get the code:

```bash
git clone （repository URL）
cd petcam
pip install -r requirements.txt
```

Only three packages are installed: `Flask`, `simple-websocket`, `cryptography`.

## Step 2: Start the server

On Windows, double-click `start.bat`. Otherwise:

```bash
python server.py
```

A console window shows your **PIN** and the **addresses to open**:

```
============================================================
  PET CAMERA server started
============================================================
  PIN            : 123456789012

  Phone (camera) : https://192.168.x.x:8443/camera
  PC (viewer)    : https://192.168.x.x:8443/viewer
============================================================
```

**Leave this window open.** Closing it stops the camera.

The first time, your OS will ask for network permission.
On Windows, **check "Private networks" and allow it** — otherwise your phone
cannot reach the PC.

The PIN is generated randomly on first run. It is not in the source code.

## Step 3: Set up the camera phone

1. Connect the phone to **the same Wi-Fi as the PC** (not a guest network)
2. Open the `/camera` address in Chrome
3. You will see "Your connection is not private"
   → **Advanced → Proceed** (this warning is expected; step 5 removes it)
4. Enter the PIN
5. **Press CAMERA ON and allow camera access**

**You only grant camera permission once.** After that you can turn the camera
on and off remotely.

### Placement tips

Heat and battery are what actually cause trouble:

| | Why |
|---|---|
| Keep it plugged in | Required |
| Lowest screen brightness | The main source of heat and power draw |
| Remove the case | Helps it stay cool over long periods |
| Silence notifications | An incoming call covers the page and stops the camera |
| Lock screen rotation | Keeps the picture the right way up |

The screen goes black after 1 minute without touch, **while streaming continues**.
Drawing the preview is the main power cost, so only the drawing stops.

## Step 4: View it

Open `/viewer` in a browser, enter the same PIN. That is all.
Any number of people can watch at once.

## Step 5: Watch from outside your home

This is the part that sounds hard but is not.

Rather than exposing your home to the internet, use **Tailscale** — it connects
only your own devices to each other, and it is free for personal use.

1. Install Tailscale on **the PC**, **the camera phone**, and **the device you
   will watch from**, signing in with the same account
2. In the admin console, enable **DNS → HTTPS Certificates**
3. Restart the server

The server then obtains a **real HTTPS certificate** automatically, and you get
an address like:

```
https://your-pc-name.your-network.ts.net:8443/viewer
```

**The same URL works at home and away, with no certificate warning.**
Certificates expire after 90 days but renew themselves before that.

To let a family member watch, send them an invite from the **Users** page.
They join with their own account.

## Checking that it works

```bash
python selftest.py
```

This checks 26 things — authentication, lockout, state propagation, remote
commands, reconnection, chime delivery. Video itself can only be tested on a
real device.

## Updating

```bash
git pull
```

Restart the server. **Your PIN and certificates live in `config.json` and
`certs/`, and are not touched by updates.**

## The three things that trip people up

I hit all of them.

**1. Forgetting to install Tailscale on the camera phone**

This fails in the most confusing way possible. The status shows
`DEVICE ONLINE` and `CAMERA ON` correctly, but **no video arrives.**

Video does not travel through the server — the two devices talk directly.
Reaching the server is not enough; the viewer must reach the camera phone.

**2. Android battery optimisation**

Settings → Apps → Tailscale → Battery → **"Unrestricted"**.
Otherwise Android quietly kills the VPN to save power. It works at home and
fails from outside.

**3. Being on a guest network**

Guest networks block device-to-device traffic, so nothing connects.

## What was actually hard

Not WebRTC. **The failures were quiet ones.**

**Clicking the console window killed the server.** On Windows, clicking a
console window puts it into selection mode, which blocks output — and blocks
the program trying to write it. The server froze while printing its startup
message. Selection mode is now disabled and logs go to a file.

**Fixing one bug created another.** I added a rule to avoid duplicate connection
offers. That rule then refused legitimate reconnections, so a brief Wi-Fi drop
left the video dead forever — the camera side still believed it was connected.
**One side always notices a disconnect before the other.** Now a peer that
reports being broken is always believed, and a watchdog checks whether video is
actually advancing rather than trusting status flags.

**The wrong sound played.** Choosing "melody" played the chime instead. The
camera page was running an older version that did not know the new sound, and
it silently substituted the default. JavaScript was also being cached because
the no-cache rule matched `application/javascript` but the files were served as
`text/javascript`. It now returns an error instead of substituting.

Three lessons:

> Never reject a peer's request based on your own view of the state.
>
> Put the switch where the person using it can reach it.
>
> Never silently substitute something else.

## Try it

If you have a spare phone in a drawer, it costs nothing to try, and the phone
goes back to normal afterwards.

**Repository: （URL here）**

The README has more detail than this article, including troubleshooting.

Licensed under MIT.
