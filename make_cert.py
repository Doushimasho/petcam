"""自己署名証明書を certs/ に作る。

ブラウザのカメラ取得(getUserMedia)は localhost 以外では HTTPS が必須なので、
LAN内で使うための証明書をここで自前で用意する。
外部サービスもopensslコマンドも使わない（cryptographyパッケージだけで完結する）。
"""
import datetime
import ipaddress
import socket
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

BASE = Path(__file__).resolve().parent
CERT_DIR = BASE / "certs"
CERT_FILE = CERT_DIR / "cert.pem"
KEY_FILE = CERT_DIR / "key.pem"


def local_ip() -> str:
    """このPCがLAN内で名乗っているIPv4アドレスを取る。

    外に送信はしない。OSに「その宛先ならどのNICを使うか」を聞くだけ。
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def build(ip: str) -> None:
    CERT_DIR.mkdir(exist_ok=True)

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "petcam-local")])

    # SAN に載っていないアドレスでアクセスすると、警告を突破しても
    # ブラウザが安全なコンテキストとして扱わずカメラが開けないことがある。
    alt = [
        x509.DNSName("localhost"),
        x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
    ]
    if ip != "127.0.0.1":
        alt.append(x509.IPAddress(ipaddress.ip_address(ip)))

    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=825))
        .add_extension(x509.SubjectAlternativeName(alt), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )

    KEY_FILE.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    CERT_FILE.write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def ensure(ip: str) -> tuple[Path, Path]:
    """証明書が無い、またはIPが変わっていたら作り直す。"""
    if CERT_FILE.exists() and KEY_FILE.exists():
        try:
            cert = x509.load_pem_x509_certificate(CERT_FILE.read_bytes())
            san = cert.extensions.get_extension_for_class(
                x509.SubjectAlternativeName
            ).value
            ips = {str(v) for v in san.get_values_for_type(x509.IPAddress)}
            expired = cert.not_valid_after_utc < datetime.datetime.now(
                datetime.timezone.utc
            )
            if ip in ips and not expired:
                return CERT_FILE, KEY_FILE
        except Exception:
            pass  # 壊れていたら作り直す
    build(ip)
    return CERT_FILE, KEY_FILE


if __name__ == "__main__":
    ip = local_ip()
    ensure(ip)
    print(f"証明書を作りました: {CERT_FILE}")
    print(f"対象アドレス: {ip}, 127.0.0.1, localhost")
