"""手渡し用の手順書を作る（1枚ものの紙 / PDF と テキスト）。

docs/friend_setup.md は細かいところまで書いた版で、読む人には長すぎる。
こちらは「インストールから映像が出るまで」だけに絞った紙。
印刷して渡す、あるいは本文をそのまま貼って送るためのもの。

アドレスとPINは config.json から読む。
手順書に直接書き込まないのは、PINを替えたときに作り直せば済むようにするため。

  python make_handout.py

docs/friend_quickstart.pdf と docs/friend_quickstart.txt ができる。
どちらもPINが入るので、リポジトリには入れない（.gitignore 済み）。
"""

from __future__ import annotations

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
DOCS = HERE / "docs"

# 日本語が出るフォント。Windowsに最初から入っているものを先に探す。
# プロジェクトにフォントを同梱すると数MB増えるので、持たない。
FONT_CANDIDATES = [
    # (正体, 太字)
    (r"C:\Windows\Fonts\YuGothR.ttc", r"C:\Windows\Fonts\YuGothB.ttc"),
    (r"C:\Windows\Fonts\meiryo.ttc", r"C:\Windows\Fonts\meiryob.ttc"),
    (r"C:\Windows\Fonts\msgothic.ttc", r"C:\Windows\Fonts\msgothic.ttc"),
]

# 色は少なめにする。家庭用のプリンタで刷るので、薄い色は飛ぶ。
INK = (0.10, 0.11, 0.13)
ACCENT = (0.12, 0.33, 0.46)
MUTED = (0.42, 0.45, 0.50)
BOXBG = (0.957, 0.965, 0.973)
BOXLINE = (0.78, 0.81, 0.85)


def load_config() -> dict:
    p = HERE / "config.json"
    if not p.exists():
        sys.exit("config.json が見つかりません。先にサーバを一度起動してください。")
    return json.loads(p.read_text(encoding="utf-8"))


def lan_ip() -> str:
    """このパソコンが家のネットワークで使っているアドレス。"""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "192.168.x.x"
    finally:
        s.close()


def ts_host() -> str | None:
    """Tailscale でのこのパソコンの名前。取れなければ None。"""
    try:
        import ts_cert
        return ts_cert.cert_name()
    except Exception:
        return None


# ---------------------------------------------------------------- 文面
def build_text(host: str, port: int, pin: str, lan: str) -> str:
    """紙とテキストで同じ文面を使う。二重に直す手間を作らないため。"""
    pcname = host.split(".")[0]
    return f"""ペットカメラの見かた

留守のあいだ、メルクの様子を見られるようにします。
設定は1回だけ、5分ほどで終わります。
見るのはブラウザなので、専用アプリは要りません。

【用意するものはありません】
新しくアカウントを作る必要はありません。
ふだんお使いの Apple ID か Google アカウントでそのまま進められます。


(1) アプリを入れる

    「Tailscale」を検索してインストール（水色のアイコン・無料）
    iPhone は App Store / Android は Google Play ストア

    ※ この時点ではまだ開かないでください


(2) 送ったリンクを開く

    お送りしたリンクをタップし、「Accept」や「承認」を押す
    サインインを求められたら、ふだんお使いのアカウントを選ぶ
    （iPhone なら Apple / Android なら Google）

    ※ 先にアプリを開いてサインインすると、別のネットワークが
      できてしまい映像が見られません。必ずこの順でお願いします。


(3) アプリを開いて、(2)と同じアカウントでサインインする


(4) 接続スイッチをオンにする

    端末から確認画面が出ます。出るのは最初の1回だけです。
      iPhone 「VPN構成の追加を求めています」→「許可」
      Android「接続リクエスト」→「OK」

    画面の上に小さく VPN と出れば、つながっています。

    ※ アプリの中の「Exit Node」は使いません。触らないでください。

    ★ここで確認してください★
      アプリの画面に {pcname} という名前が見えますか？
      見えないときは、次に進んでも開けません。連絡をください。


(5) ブラウザで次のアドレスを開く

    iPhone は Safari / Android は Chrome

      https://{host}:{port}/viewer


(6) PINを聞かれるので、次の数字を入れる

      {pin}

    長いですが、入力はこの1回だけです。
    映像が出れば完了です。


→ ホーム画面に追加しておくと、次からはタップするだけで開きます。
   iPhone  共有ボタン →「ホーム画面に追加」
   Android 右上のメニュー →「ホーム画面に追加」


────────────────────────────────────

よく使うボタン

  CAMERA ON / OFF   カメラを動かす・止める
  音を聞く          部屋の音を聞く（音が出るまで数秒かかります）
  スナップショット   今映っている画面を写真に残す
  ♪ 音を鳴らす      カメラのある部屋で音が鳴る（反応を見たいときに）
  ライトをつける     カメラ側のライトが点く（3分で自動的に消えます）


ひとつだけお願い

  画面の下にある「設定を開く」の中は触らないでください。
  中の「パソコンの電源」を押すと家のパソコンが止まってしまい、
  こちらが帰るまで映像が見られなくなります。


困ったとき

  画面が黒い             映像のところを1回タップしてください
  映像が止まった          10秒ほど待つと自動で戻ります
  CAMERA OFF と出ている   CAMERA ON を押してください
  ページが開かない        Tailscaleのスイッチがオンか確認してください
  DEVICE OFFLINE と出る   カメラ側のスマホの問題です。連絡をください


2回目以降

  Tailscaleのスイッチがオンになっていることを確認して、
  ホーム画面のアイコンを開くだけです。PINはもう要りません。


通信量は10分見ておよそ100MBです。長く見るときはWi-Fiがおすすめです。
家のWi-Fiにつながっているときは https://{lan}:{port}/viewer でも見られます
（証明書の警告が出ますが、そのまま進んで問題ありません）。

面倒を見ていただいて、ありがとうございます。
"""


# ---------------------------------------------------------------- PDF
def pick_fonts() -> tuple[str | None, str | None]:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    for reg, bold in FONT_CANDIDATES:
        if not (pathlib.Path(reg).exists() and pathlib.Path(bold).exists()):
            continue
        try:
            pdfmetrics.registerFont(TTFont("JP", reg, subfontIndex=0))
            pdfmetrics.registerFont(TTFont("JP-B", bold, subfontIndex=0))
            return "JP", "JP-B"
        except Exception:
            continue
    return None, None


# 英数字でできた塊は、途中で割らずにひとまとまりで送る。
# これが無いと「Google」が「Goo / gle」のように割れて読めなくなる。
LATIN = set(
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    "./:-_?=&@+#%~"
)
# 行頭に置くと見栄えが悪い文字は、前の行に残す
NO_HEAD = "。、）」』・？！ー"


def tokens(s: str) -> list[str]:
    """英数字の塊を1つ、それ以外は1文字ずつに分ける。"""
    out: list[str] = []
    buf = ""
    for ch in s:
        if ch in LATIN:
            buf += ch
            continue
        if buf:
            out.append(buf)
            buf = ""
        out.append(ch)
    if buf:
        out.append(buf)
    return out


def wrap(s: str, font: str, size: float, avail: float) -> list[str]:
    """日本語は単語の区切りが無いので、幅を見て送る。

    区切りの単位は tokens() が決める。英数字だけ塊のまま扱い、
    和文は1文字ずつ。URLのように1つで1行に入らないものだけ、
    最後の手段として文字単位で割る。
    """
    from reportlab.pdfbase import pdfmetrics
    if not s:
        return [""]
    out: list[str] = []
    cur = ""
    for tok in tokens(s):
        if pdfmetrics.stringWidth(cur + tok, font, size) <= avail:
            cur += tok
            continue
        if tok in NO_HEAD and cur:
            out.append(cur + tok)
            cur = ""
            continue
        if cur:
            out.append(cur)
            cur = ""
        # 塊そのものが1行に入らない（長いURLなど）。ここだけは割る
        while pdfmetrics.stringWidth(tok, font, size) > avail and len(tok) > 1:
            cut = len(tok)
            while cut > 1 and pdfmetrics.stringWidth(
                    tok[:cut], font, size) > avail:
                cut -= 1
            out.append(tok[:cut])
            tok = tok[cut:]
        cur = tok
    if cur:
        out.append(cur)
    return out


class Sheet:
    """A4に上から順に書いていくだけの、ごく薄い入れもの。

    段組みも図もないので、レイアウト機構は持たない。
    「次の行がはみ出るなら改ページ」だけを見る。
    """

    def __init__(self, path: pathlib.Path, reg: str, bold: str):
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        self.W, self.H = A4
        self.margin = 48.0
        self.reg, self.bold = reg, bold
        self.c = canvas.Canvas(str(path), pagesize=A4)
        self.c.setTitle("ペットカメラの見かた")
        self.y = self.H - self.margin

    @property
    def width(self) -> float:
        return self.W - self.margin * 2

    def space(self, h: float) -> None:
        self.y -= h

    def need(self, h: float) -> None:
        if self.y - h < self.margin + 24:
            self.page_break()

    def page_break(self) -> None:
        self.foot()
        self.c.showPage()
        self.y = self.H - self.margin

    def foot(self) -> None:
        self.c.setFont(self.reg, 7.5)
        self.c.setFillColorRGB(*MUTED)
        self.c.drawCentredString(self.W / 2, self.margin - 16,
                                 "うまくいかないときは、遠慮なく連絡をください")

    def text(self, s: str, size: float = 9.5, font: str | None = None,
             color=INK, indent: float = 0.0, lead: float = 1.55) -> None:
        font = font or self.reg
        avail = self.width - indent
        for para in s.split("\n"):
            for line in wrap(para, font, size, avail):
                self.need(size * lead)
                self.c.setFont(font, size)
                self.c.setFillColorRGB(*color)
                self.c.drawString(self.margin + indent, self.y - size, line)
                self.y -= size * lead

    def pair(self, name: str, desc: str, at: float = 150.0) -> None:
        """左に名前、右に説明。表のかわり。"""
        self.need(16)
        self.c.setFont(self.bold, 9.5)
        self.c.setFillColorRGB(*INK)
        self.c.drawString(self.margin + 6, self.y - 9.5, name)
        self.c.setFont(self.reg, 9.5)
        self.c.setFillColorRGB(*MUTED)
        for i, line in enumerate(wrap(desc, self.reg, 9.5,
                                      self.width - at - 6)):
            if i:
                self.y -= 14
                self.need(16)
            self.c.drawString(self.margin + at, self.y - 9.5, line)
        self.y -= 16

    def rule(self) -> None:
        self.need(10)
        self.c.setStrokeColorRGB(*BOXLINE)
        self.c.setLineWidth(0.6)
        self.c.line(self.margin, self.y - 4, self.W - self.margin, self.y - 4)
        self.y -= 14

    def box(self, lines: list[tuple[str, float, str]], pad: float = 10.0) -> None:
        """枠で囲む。lines は (文字, 大きさ, 'reg'|'bold') の並び。"""
        h = sum(sz * 1.5 for _, sz, _ in lines) + pad * 2
        self.need(h + 6)
        top = self.y
        self.c.setFillColorRGB(*BOXBG)
        self.c.setStrokeColorRGB(*BOXLINE)
        self.c.setLineWidth(0.8)
        self.c.roundRect(self.margin, top - h, self.width, h, 5,
                         stroke=1, fill=1)
        yy = top - pad
        for s, sz, w in lines:
            self.c.setFont(self.bold if w == "bold" else self.reg, sz)
            self.c.setFillColorRGB(*INK)
            self.c.drawCentredString(self.W / 2, yy - sz, s)
            yy -= sz * 1.5
        self.y = top - h - 12

    def save(self) -> None:
        self.foot()
        self.c.save()


def build_pdf(path: pathlib.Path, host: str, port: int, pin: str,
              lan: str) -> bool:
    reg, bold = pick_fonts()
    if not reg or not bold:
        return False

    s = Sheet(path, reg, bold)
    pcname = host.split(".")[0]

    s.text("ペットカメラの見かた", 19, bold, ACCENT)
    s.space(4)
    s.text("留守のあいだ、メルクの様子を見られるようにします。"
           "設定は1回だけ、5分ほどで終わります。"
           "見るのはブラウザなので、専用アプリは要りません。", 9.5, reg, MUTED)
    s.space(6)
    s.rule()

    s.text("用意するものはありません", 11, bold, INK)
    s.space(2)
    s.text("新しくアカウントを作る必要はありません。"
           "ふだんお使いの Apple ID か Google アカウントで"
           "そのまま進められます。", 9.5)
    s.space(14)

    steps: list[tuple[str, list[str]]] = [
        ("1   アプリを入れる", [
            "「Tailscale」を検索してインストールします（水色のアイコン・無料）。"
            "iPhone は App Store、Android は Google Play ストアです。",
            "※ この時点ではまだ開かないでください。",
        ]),
        ("2   送ったリンクを開く", [
            "お送りしたリンクをタップし、「Accept」や「承認」を押します。"
            "サインインを求められたら、ふだんお使いのアカウントを選んでください"
            "（iPhone なら Apple、Android なら Google）。",
            "※ 先にアプリを開いてサインインすると、別のネットワークができて"
            "しまい映像が見られません。必ずこの順でお願いします。",
        ]),
        ("3   アプリを開いて、2 と同じアカウントでサインインする", []),
        ("4   接続スイッチをオンにする", [
            "端末から確認画面が出ます。出るのは最初の1回だけです。",
            "　　iPhone 「VPN構成の追加を求めています」→「許可」",
            "　　Android「接続リクエスト」→「OK」",
            "画面の上に小さく VPN と出れば、つながっています。",
            "※ アプリの中の「Exit Node」は使いません。触らないでください。",
            "★ アプリの画面に " + pcname + " という名前が見えるか確認して"
            "ください。見えないときは、次に進んでも開けません。連絡をください。",
        ]),
        ("5   ブラウザで次のアドレスを開く", [
            "iPhone は Safari、Android は Chrome です。",
        ]),
    ]
    for head, body in steps:
        s.need(36)
        s.text(head, 11, bold, ACCENT)
        s.space(3)
        for line in body:
            s.text(line, 9.5, reg, INK, indent=16)
            s.space(2)
        s.space(10)

    s.box([("https://%s:%d/viewer" % (host, port), 12.5, "bold")])

    s.need(40)
    s.text("6   PINを聞かれるので、次の数字を入れる", 11, bold, ACCENT)
    s.space(5)
    s.box([(pin, 19, "bold"),
           ("長いですが、入力はこの1回だけです", 8.5, "reg")])
    s.text("映像が出れば完了です。ホーム画面に追加しておくと、"
           "次からはタップするだけで開きます"
           "（iPhone は共有ボタン →「ホーム画面に追加」、"
           "Android は右上のメニューから）。", 9.5)

    # ここから先は読まなくても使い始められる内容なので、紙を分ける
    s.page_break()

    s.text("よく使うボタン", 13, bold, ACCENT)
    s.space(8)
    for name, desc in [
        ("CAMERA ON / OFF", "カメラを動かす・止める"),
        ("音を聞く", "部屋の音を聞く（音が出るまで数秒かかります）"),
        ("スナップショット", "今映っている画面を写真に残す"),
        ("♪ 音を鳴らす", "カメラのある部屋で音が鳴る（反応を見たいときに）"),
        ("ライトをつける", "カメラ側のライトが点く（3分で自動的に消えます）"),
    ]:
        s.pair(name, desc)
    s.space(12)

    s.text("ひとつだけお願い", 13, bold, ACCENT)
    s.space(5)
    s.text("画面の下にある「設定を開く」の中は触らないでください。"
           "中の「パソコンの電源」を押すと家のパソコンが止まってしまい、"
           "こちらが帰るまで映像が見られなくなります。", 9.5)
    s.space(16)

    s.text("困ったとき", 13, bold, ACCENT)
    s.space(8)
    for sym, fix in [
        ("画面が黒い", "映像のところを1回タップしてください"),
        ("映像が止まった", "10秒ほど待つと自動で戻ります"),
        ("CAMERA OFF と出ている", "CAMERA ON を押してください"),
        ("ページが開かない", "Tailscaleのスイッチがオンか確認してください"),
        ("DEVICE OFFLINE と出る", "カメラ側のスマホの問題です。連絡をください"),
    ]:
        s.pair(sym, fix, at=180.0)
    s.space(12)

    s.text("2回目以降", 13, bold, ACCENT)
    s.space(5)
    s.text("Tailscaleのスイッチがオンになっていることを確認して、"
           "ホーム画面のアイコンを開くだけです。PINはもう要りません。", 9.5)
    s.space(16)

    s.text("通信量は10分見ておよそ100MBです。長く見るときはWi-Fiがおすすめです。\n"
           "家のWi-Fiにつながっているときは https://%s:%d/viewer でも見られます\n"
           "（証明書の警告が出ますが、そのまま進んで問題ありません）。"
           % (lan, port), 9, reg, MUTED)
    s.space(18)
    s.text("面倒を見ていただいて、ありがとうございます。", 10, bold, INK)

    s.save()
    return True


def main() -> None:
    cfg = load_config()
    pin, port = str(cfg["pin"]), int(cfg.get("port", 8443))
    host = ts_host()
    if not host:
        sys.exit("Tailscale の名前が取れませんでした。"
                 "Tailscale が動いているか確認してください。")
    lan = lan_ip()
    DOCS.mkdir(exist_ok=True)

    txt = DOCS / "friend_quickstart.txt"
    txt.write_text(build_text(host, port, pin, lan), encoding="utf-8")
    print("できました: %s" % txt)

    pdf = DOCS / "friend_quickstart.pdf"
    try:
        ok = build_pdf(pdf, host, port, pin, lan)
    except ImportError:
        print("PDFは作れませんでした（reportlab が入っていません）。")
        print("  pip install reportlab")
        print("テキスト版はできているので、そのままでも渡せます。")
        return
    if ok:
        print("できました: %s" % pdf)
    else:
        print("PDFは作れませんでした（日本語フォントが見つかりません）。")
        print("テキスト版をそのまま使ってください。")


if __name__ == "__main__":
    main()
