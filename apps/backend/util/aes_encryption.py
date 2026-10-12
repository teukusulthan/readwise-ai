import json, base64

from config.base import settings

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from loguru import logger


def encrypt_aes_data(data, secret_key: str = settings.ENC_SECRET):
    if isinstance(data, str) == False:
        data = json.dumps(data)
    cipher = AES.new(secret_key.encode(), AES.MODE_ECB)
    data = data.encode()
    while len(data) % 16 != 0:
        data += b' '
    encrypted_text = cipher.encrypt(data)
    return base64.b64encode(encrypted_text).decode()

def decrypt_aes_data(encrypted_text, secret_key: str = settings.ENC_SECRET):
    try:
        cipher = AES.new(secret_key.encode(), AES.MODE_ECB)
        encrypted_text = base64.b64decode(encrypted_text)
        decrypted_text = cipher.decrypt(encrypted_text)
        return unpad(decrypted_text, AES.block_size, style='pkcs7').decode() \
            if (len(decrypted_text) % AES.block_size) != 0 else decrypted_text.decode()
    except Exception as e:
        logger.exception("Request failed")
        raise e
    