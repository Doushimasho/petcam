# 余っていたスマホが、ペットカメラになりました（作り方も置いておきます）

猫を留守番させるとき、様子が見たい。
市販のペットカメラを買えばいいのですが、引き出しに使っていないスマホが眠っていました。
カメラもWi-Fiも付いていて、電源につなげば動き続けます。これを使うことにしました。

できたものは、こんな具合です。

- **費用は0円**。月額も契約もありません
- **見る側はブラウザだけ**。アプリを入れる必要がありません
- **外出先からも見られます**。しかも自宅をインターネットに公開せずに
- 映像の遅れは0.2秒くらい。ほぼリアルタイムです

**ペットカメラとしても、赤ちゃんや家族の見守りカメラとしても使えます。**

作り方をぜんぶ公開しているので、同じものが作れます。
この記事はその手順です。**パソコンに詳しくなくても大丈夫なように書きました。**

---

# やることは、4つだけです

**① パソコンでファイルを開いて、起動する**（10分）
**② スマホでページを開いて、カメラを許可する**（5分）
**③ 見る**（1分）
**④ 外出先からも見られるようにする**（15分）

**③まで終われば、家の中ではもう使えます。**
④は必要になってからで大丈夫です。あとからいつでもできます。

失敗してもスマホやパソコンが壊れることはありません。
うまくいかなければ、ファイルを消すだけで元に戻ります。

---

# 用意するもの

- **余っているAndroidスマートフォン**（カメラになります）
- **パソコン**（WindowsでもMacでも大丈夫）
- 両方が**同じWi-Fi**につながっていること
- スマホ用の充電ケーブル（つなぎっぱなしにします）

古いスマホで大丈夫です。SIMカードが入っていなくても、Wi-Fiにつながれば動きます。

**カメラにするのはAndroidにしてください。**
iPhoneをカメラにすると、画面が消えたときにカメラも止まってしまいます。
**見るほうはiPhoneでも問題ありません。**

---

# ① パソコンの準備（10分）

## 1-1. Pythonを入れる

このカメラはPythonという言語で動いています。まずそれを入れます。

**[python.org](https://www.python.org/downloads/) を開いて、黄色い「Download Python」ボタンを押します。**

ダウンロードしたファイルを開くと、インストール画面が出ます。

> **ここだけ注意してください。**
> 最初の画面の下のほうに **「Add python.exe to PATH」** というチェック欄があります。
> **必ずチェックを入れてから** 「Install Now」を押してください。
>
> ここを飛ばすと、あとの手順で動きません。

すでにPythonが入っている方は、この手順は飛ばして大丈夫です。
入っているか分からなければ、入れてしまって構いません。壊れることはありません。

## 1-2. ファイルをダウンロードする

**[https://github.com/Doushimasho/petcam](https://github.com/Doushimasho/petcam) を開きます。**

1. ページの右のほうにある**緑色の「Code」ボタン**を押します
2. 出てきたメニューの一番下、**「Download ZIP」**を押します
3. ダウンロードされたZIPファイルを**右クリック → 「すべて展開」**
4. 展開先を **`C:\petcam`** にすると、あとが分かりやすいです

展開したフォルダを開いて、中に `start.bat` というファイルがあればOKです。

## 1-3. 起動する

**`start.bat` をダブルクリックするだけです。**

初回は「必要な部品を用意しています」と出て、1分ほど待ちます。
そのあと黒い画面にこう表示されます。

```
============================================================
  PET CAMERA サーバを起動しました
============================================================
  PIN            : 123456789012

  スマホ（カメラ）: https://192.168.1.5:8443/camera
  PC（視聴）      : https://192.168.1.5:8443/viewer
============================================================
```

**この2つをメモしてください。**

- **PIN**（12桁の数字）
- **アドレス**（`https://192.168.〇〇〇` の部分。人によって数字が違います）

> **黒い画面は閉じないでください。**
> 閉じるとカメラも止まります。使っている間は開いたままにしておきます。
> 邪魔なら最小化して大丈夫です。

### Windowsから確認を求められたら

初回だけ「このアプリの機能のいくつかがブロックされました」という窓が出ます。

**「プライベートネットワーク」にチェックを入れて、「アクセスを許可する」を押してください。**

ここを許可しないと、スマホからつながりません。

### Macをお使いの場合

Macには `start.bat` は使えません。かわりに「ターミナル」を開いて、
展開したフォルダで次の2行を**1行ずつ**実行してください。

```
pip3 install -r requirements.txt
```

```
python3 server.py
```

---

# ② スマホの設定（5分）

カメラにするAndroidスマホで作業します。

## 2-1. 同じWi-Fiにつなぐ

パソコンと**同じWi-Fi**につないでください。

「ゲスト用」と書かれたWi-Fiは使えません。機器どうしがつながらない設定になっています。

## 2-2. Chromeでアドレスを開く

さきほどメモしたアドレスの、**うしろに `/camera` が付いたほう**を開きます。

```
https://192.168.1.5:8443/camera
```

数字の部分はご自分のものに置き換えてください。

## 2-3. 警告が出るので、進みます

**「接続はプライベートではありません」**という赤い警告が出ます。

これは正常です。あなたのパソコンが作った証明書なので、
外部の認証局に登録されていないだけです。

**「詳細設定」→「192.168.〇〇〇 にアクセスする（安全ではありません）」** を押して進んでください。

（この警告は、手順④まで進めば出なくなります）

## 2-4. PINを入れる

メモした12桁の数字を入力します。長いですが、**入力するのはこの1回だけ**です。

## 2-5. カメラを許可する

**「CAMERA ON」ボタンを押します。**

「カメラへのアクセスを許可しますか」と聞かれるので、**「アプリの使用中のみ許可」**を選びます。

自分の部屋が映れば成功です。

> **カメラの許可を聞かれるのは、この1回だけです。**
> 次からは、手元のパソコンやスマホから遠隔でON/OFFできます。

## 2-6. 置く

ペットの見える場所に置いて、**充電ケーブルをつなぎます。**

長く使うと熱が問題になるので、次をやっておくと安心です。

| やること | なぜ |
|---|---|
| 画面の明るさを一番暗くする | 熱と電池の一番の原因です |
| ケースを外す | 熱が逃げやすくなります |
| 通知や着信を切る | 着信画面が出るとカメラが止まります |
| 画面の自動回転をオフ | 映像が横向きになるのを防ぎます |

**画面は1分さわらないと自動的に真っ暗になります。**
カメラは止まりません。映像を映し続けるのが一番電気を使うので、
表示だけをやめる仕組みにしてあります。さわればまた表示されます。

---

# ③ 見る（1分）

パソコンのブラウザで、今度は**うしろが `/viewer` のアドレス**を開きます。

```
https://192.168.1.5:8443/viewer
```

同じように警告を抜けて、同じPINを入れます。

映像が出れば完成です。**ここまでで、家の中では使えるようになりました。**

## 使えるボタン

| ボタン | できること |
|---|---|
| CAMERA ON / OFF | カメラを動かす・止める |
| 音を聞く | 部屋の音が聞こえます |
| スナップショット | 今の画面を写真に保存します |
| ♪ 音を鳴らす | **カメラ側のスマホから音が鳴ります**。反応を見たいときに |

音は3種類（チャイム／呼びかけ／メロディ）、音量は2段階から選べます。
**選ぶと手元でも同じ音が鳴る**ので、どんな音か確かめてから送れます。

何台からでも同時に見られます。家族それぞれのスマホから見ても大丈夫です。

---

# ④ 外出先からも見られるようにする（15分）

ここまでは家の中だけです。外からも見たい場合はもう一手間かかります。

**自宅をインターネットに公開するのは避けたい**ので、
**Tailscale** という無料の仕組みを使います。
自分の持っている端末どうしだけをつなぐもので、外部からは一切見えません。

## 4-1. 3つの端末にTailscaleを入れる

**この3つ全部に入れて、同じアカウントでログインします。**

1. **パソコン**（[tailscale.com](https://tailscale.com/) からダウンロード）
2. **カメラにしているスマホ**（Google Playで「Tailscale」）
3. **外出先で見るスマホ**（App Store / Google Play）

アカウントはGoogleアカウントでそのまま作れます。

> **カメラにしているスマホを忘れないでください。**
> ここを忘れると、状態は「ONLINE」と出るのに映像だけ来ない、
> という一番分かりにくい状態になります。

## 4-2. Androidの設定を1つ変える

カメラにしているAndroidで、

**設定 → アプリ → Tailscale → バッテリー → 「制限なし」**

にしてください。ここを変えないと、Androidが節電のために勝手に接続を切ります。
家では映るのに外出先だけ映らない、という形で出ます。

## 4-3. 証明書を有効にする

Tailscaleの管理画面（[login.tailscale.com](https://login.tailscale.com/)）を開いて、

**左のメニューの「DNS」→ 下のほうの「HTTPS Certificates」→ 有効にする**

## 4-4. 起動し直す

黒い画面を閉じて、もう一度 `start.bat` をダブルクリックします。

すると、新しいアドレスが表示されます。

```
https：//〇〇〇.〇〇〇.ts.net:8443/viewer
```

**このアドレスなら、家の中でも外出先でも同じように使えます。**
しかも**証明書の警告がもう出ません。**

カメラ側のスマホも、この新しいアドレスで開き直してください
（PINとカメラの許可をもう一度だけ聞かれます）。

## 家族にも見せたい場合

**招待リンク**を送れば、相手は自分のアカウントのまま参加できます。
あなたのアカウント情報を教える必要はありません。

作り方は2分です。

1. [login.tailscale.com](https://login.tailscale.com/) を開く
2. 左メニューの **Users**
3. **Invite external users** を押す
4. **Copy invite link** のタブを選ぶ
5. 権限は **Member** でよい
6. **Generate & copy invite link** を押す

コピーされたリンクをLINEなどで送れば完了です。
相手はリンクを開いて、自分のGoogleかAppleのアカウントでサインインするだけです。

---

# うまくいかないとき

**スマホでページが開かない**
- パソコンとスマホが同じWi-Fiにいますか（ゲスト用Wi-Fiは使えません）
- Windowsの許可の窓で「プライベートネットワーク」を許可しましたか
- アドレスの数字は、黒い画面に出ているものと同じですか

**「CAMERA ON」なのに映像が黒いまま**
- カメラ側のスマホで、他のアプリに切り替わっていませんか
- 外出先からの場合、**カメラ側のスマホにTailscaleが入っていますか**
- iPhoneで見ていて「タップして再生」と出たら、映像の部分を1回タップしてください

**映像が途中で止まった**
- **10秒ほど待つと自動で戻ります。** 何もしなくて大丈夫です

**黒い画面が固まった／閉じてしまった**
- もう一度 `start.bat` をダブルクリックすれば戻ります

**「ポート 8443 は既に使われています」と出る**
- 前の黒い画面がまだ残っています。全部閉じてから起動し直してください

---

# AIを使っている方へ

ClaudeやChatGPTを使っている方は、**AIに手伝ってもらったほうが早いかもしれません。**

リポジトリに `AI_SETUP.md` というファイルを置いてあります。
これをAIに読ませると、あなたの環境に合わせて対話しながら進めてくれます。

Claude Codeのように**パソコンを操作できるAI**なら、こう頼むだけです。

```
https://github.com/Doushimasho/petcam の AI_SETUP.md を読んで、
ペットカメラの導入を手伝ってください。
```

つまずきやすい点や、やってはいけないこと（PINを外に出さない等）も
そのファイルに書いてあるので、AIがそこを外しません。

---

# 作ってみて、詰まったこと

技術的に難しかったのは、実は映像の仕組みではありませんでした。
**壊れ方が静かなこと**でした。3つだけ紹介します。

## 黒い画面をクリックしたら、サーバが止まった

スマホからつながらない。設定は合っている。プログラムも動いている。
なのにパソコン自身からもつながらない。

原因はWindowsの黒い画面でした。
**あの画面はクリックすると文字の選択モードに入り、その間は表示が止まります。
表示が止まると、表示しようとしていたプログラムごと止まります。**

いまは選択モードを無効にして、記録も画面ではなくファイルに書くようにしました。

## バグを直したら、別のバグを作った

接続の申し込みが二重になる不具合を直すため、
「すでにつながっている相手には申し込まない」という判定を入れました。

そのせいで、Wi-Fiが一瞬切れたあと**映像が永久に戻らなくなりました。**
カメラ側が、まだ自分は「つながっている」と思い込んでいたからです。

**切断に気づくのは、いつも片方が先です。**
自分の見え方を理由に、相手の「壊れています」を却下してはいけませんでした。

いまは、映像が実際に進んでいるかを2秒ごとに見張っています。
状態表示は当てになりません。信じられるのは実際の動きだけでした。

## 選んだ音と、違う音が鳴った

呼び出し音でメロディを選んだのに、部屋のスマホからはチャイムが鳴る。
手元の試聴では正しく鳴るのに。

カメラ側の画面が古いままで、新しく増えた音を知らなかったのが原因でした。
そして**知らない音を、黙って別の音に差し替えていた**のが一番よくありませんでした。

いまは差し替えず「その音を知りません」と返します。

---

# まとめ

作りながら学んだことを3つ挙げるなら、これになります。

> 自分の状態を理由に、相手の要求を却下してはいけない。
>
> スイッチは、使う人が手を伸ばせる場所に置く。
>
> 代わりのもので黙って済ませない。

どれも当たり前のことなのに、作っている最中はきれいに見落とします。

引き出しに使っていないスマホがあるなら、試してみてください。
お金はかかりませんし、うまくいかなくてもスマホは元どおりです。

**リポジトリ：https://github.com/Doushimasho/petcam**

もっと詳しい手順とトラブル対応は、リポジトリの README にまとめてあります。
ライセンスはMITなので、自由に使ったり改造したりしていただけます。

---
---

# (English) A Spare Phone Became a Pet Camera

I wanted to check on my cat while I was out. Instead of buying a pet camera,
I used an old Android phone that had been sitting in a drawer.

- **Free.** No subscription, no cloud account
- **Viewers only need a browser.** Nothing to install
- **Works from outside your home** without exposing your house to the internet
- About 0.2 seconds of delay

It works as a **pet camera or a baby/family monitor**.
Everything is open source, so you can build the same thing.
**This guide assumes you are not a developer.**

---

## There are only 4 steps

**① Download and start it on your PC** (10 min)
**② Open a page on the phone and allow the camera** (5 min)
**③ Watch** (1 min)
**④ Make it work from outside your home** (15 min)

**After ③ it already works inside your home.**
Step ④ can wait until you need it.

Nothing here can damage your phone or PC. If it does not work out,
delete the folder and everything is back to normal.

## What you need

- **A spare Android phone** (this becomes the camera)
- **A PC** (Windows or Mac)
- Both on **the same Wi-Fi**
- A charging cable for the phone

An old phone is fine. It does not need a SIM card, only Wi-Fi.

**Use Android for the camera.** On iPhone the camera stops when the screen
locks. **Watching on an iPhone is completely fine.**

---

## ① Prepare the PC (10 min)

### 1-1. Install Python

Open [python.org](https://www.python.org/downloads/) and press the yellow
**Download Python** button, then run the installer.

> **One thing matters here.**
> On the first installer screen there is a checkbox called
> **"Add python.exe to PATH"**. **Tick it** before pressing "Install Now".
> Skipping it will break the later steps.

If you already have Python, skip this. If you are not sure, installing it
again is harmless.

### 1-2. Download the files

Open [github.com/Doushimasho/petcam](https://github.com/Doushimasho/petcam).

1. Press the green **Code** button
2. Choose **Download ZIP**
3. Right-click the ZIP → **Extract All**
4. Extracting to `C:\petcam` keeps things simple

You should see a file called `start.bat` inside.

### 1-3. Start it

**Just double-click `start.bat`.**

The first run takes about a minute while it sets itself up. Then you will see:

```
============================================================
  PET CAMERA server started
============================================================
  PIN            : 123456789012

  Phone (camera) : https://192.168.1.5:8443/camera
  PC (viewer)    : https://192.168.1.5:8443/viewer
============================================================
```

**Write down the PIN and the address.** The numbers differ for everyone.

> **Do not close this black window.** Closing it stops the camera.
> Minimising it is fine.

If Windows asks about network access, **tick "Private networks" and allow it**.
Without this your phone cannot reach the PC.

**On a Mac**, `start.bat` does not apply. Open Terminal in the extracted folder
and run these two lines, one at a time:

```
pip3 install -r requirements.txt
```

```
python3 server.py
```

---

## ② Set up the phone (5 min)

1. Connect the phone to **the same Wi-Fi** (not a guest network)
2. In Chrome, open the address ending in **`/camera`**
3. You will see **"Your connection is not private"**. This is expected —
   the certificate was made by your own PC.
   Press **Advanced → Proceed**. (Step ④ removes this warning)
4. Enter the PIN. It is long, but **only this once**
5. Press **CAMERA ON** and choose **"While using the app"** when asked for
   camera permission

**You are only asked for camera permission once.** After that you can turn the
camera on and off remotely.

Then place the phone where it can see your pet and **keep it plugged in**.

| Do this | Why |
|---|---|
| Lowest screen brightness | The biggest cause of heat and battery drain |
| Remove the case | Helps it stay cool |
| Silence notifications | An incoming call covers the page and stops the camera |
| Lock screen rotation | Keeps the picture upright |

**The screen goes black after 1 minute without touch, but streaming continues.**
Drawing the preview is what costs power, so only the drawing stops.
Touch it and it comes back.

---

## ③ Watch (1 min)

On your PC, open the address ending in **`/viewer`**, clear the same warning,
and enter the same PIN.

If you see video, you are done. **It now works inside your home.**

| Button | What it does |
|---|---|
| CAMERA ON / OFF | Start and stop the camera |
| Listen | Hear the room |
| Snapshot | Save the current frame |
| ♪ Play sound | **Plays a sound from the camera phone** to get their attention |

Three sounds (chime / call / melody) and two volumes.
**Picking a sound also plays it on your own device**, so you can hear it before
sending it into the room.

Any number of people can watch at the same time.

---

## ④ Watch from outside your home (15 min)

Rather than exposing your home to the internet, use **Tailscale** — a free
service that connects only your own devices to each other. Nothing is visible
from outside.

### 4-1. Install Tailscale on three devices

**All three, signed in with the same account:**

1. **Your PC** (from [tailscale.com](https://tailscale.com/))
2. **The camera phone**
3. **The phone you will watch from**

You can sign in with a Google account.

> **Do not forget the camera phone.**
> If you do, the status will say `ONLINE` and `CAMERA ON` but no video will
> arrive — the most confusing failure of all.

### 4-2. Change one Android setting

On the camera phone:
**Settings → Apps → Tailscale → Battery → "Unrestricted"**

Otherwise Android silently kills the connection to save power. It works at home
and fails from outside.

### 4-3. Enable certificates

In the Tailscale admin console ([login.tailscale.com](https://login.tailscale.com/)):
**DNS → HTTPS Certificates → enable**

### 4-4. Restart

Close the black window and double-click `start.bat` again.
You now get an address like:

```
https://your-pc.your-network.ts.net:8443/viewer
```

**This one address works both at home and away, with no certificate warning.**
Open the camera phone on this new address too (it will ask for the PIN and
camera permission once more).

To let a family member watch, send them an **invite link**. It takes 2 minutes:

1. Open [login.tailscale.com](https://login.tailscale.com/)
2. Go to **Users** in the left menu
3. Press **Invite external users**
4. Choose the **Copy invite link** tab
5. **Member** is the right role
6. Press **Generate & copy invite link**

Send them that link. They open it and sign in with **their own** Google or Apple
account — you never share your credentials.

---

## If something does not work

**The phone cannot open the page**
- Are both devices on the same Wi-Fi? (Guest networks do not work)
- Did you allow "Private networks" in the Windows prompt?

**"CAMERA ON" but the picture is black**
- Did the camera phone switch to another app?
- From outside: **is Tailscale installed on the camera phone?**
- On iPhone, if it says "tap to play", tap the video once

**The video froze**
- **Wait about 10 seconds. It reconnects by itself.**

**"Port 8443 is already in use"**
- An older black window is still running. Close them all and start again.

---

## Using an AI assistant

If you use Claude or ChatGPT, letting the AI walk you through it may be faster.

The repository contains a file called `AI_SETUP.md`. Give it to your AI and it
will guide you through setup for your specific machine.

With an AI that can operate your computer, such as Claude Code, just ask:

```
Read AI_SETUP.md from https://github.com/Doushimasho/petcam
and help me set up the pet camera.
```

That file also lists the common pitfalls and the things the AI must not do,
such as sharing your PIN.

---

## What was actually hard

Not the video. **The failures were quiet ones.**

**Clicking the console window killed the server.** On Windows, clicking a
console window puts it into selection mode, which stops output — and stops the
program trying to write it.

**Fixing one bug created another.** A rule to avoid duplicate connection offers
also refused legitimate reconnections, so a brief Wi-Fi drop left the video dead
forever. **One side always notices a disconnect before the other.** The viewer
now checks whether video is actually advancing rather than trusting status.

**The wrong sound played.** The camera page was an older version that did not
know the new sound, and silently substituted the default one. It now returns an
error instead.

Three lessons:

> Never reject a peer's request based on your own view of the state.
>
> Put the switch where the person using it can reach it.
>
> Never silently substitute something else.

## Try it

If you have a spare phone in a drawer, it costs nothing, and the phone goes back
to normal afterwards.

**Repository: https://github.com/Doushimasho/petcam**

The README has more detail. Licensed under MIT — use and modify it freely.
