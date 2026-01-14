import base64
from cryptography.hazmat.primitives import serialization
from pywebpush import Vapid

# Khởi tạo
vapid = Vapid()
vapid.generate_keys()

# Xuất Public Key chuẩn
public_key = base64.urlsafe_b64encode(
    vapid.public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )
).decode('utf-8').strip('=')

# Xuất Private Key chuẩn
private_key = base64.urlsafe_b64encode(
    vapid.private_key.private_bytes(
        encoding=serialization.Encoding.DER, # Dùng DER để tương thích mọi bản
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
).decode('utf-8').strip('=')

print("\n--- COPY 2 CHUỖI NÀY DÁN VÀO SETTINGS.PY ---")
print(f"VAPID_PUBLIC_KEY = '{public_key}'")
print(f"VAPID_PRIVATE_KEY = '{private_key}'")