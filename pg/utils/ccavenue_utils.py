import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import binascii


def encrypt(plain_text, working_key):
    """
    CC Avenue AES Encryption (AES-128-CBC)
    """
    iv = b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\x0d\x0e\x0f"
    key = hashlib.md5(working_key.encode('utf-8')).digest()
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted_text = cipher.encrypt(pad(plain_text.encode('utf-8'), AES.block_size))
    return binascii.hexlify(encrypted_text).decode('utf-8')


def decrypt(cipher_text, working_key):
    """
    CC Avenue AES Decryption (AES-128-CBC)
    """
    iv = b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\x0d\x0e\x0f"
    key = hashlib.md5(working_key.encode('utf-8')).digest()
    cipher = AES.new(key, AES.MODE_CBC, iv)
    try:
        decrypted_text = unpad(cipher.decrypt(binascii.unhexlify(cipher_text)), AES.block_size)
        return decrypted_text.decode('utf-8')
    except Exception as e:
        return str(e)


def parse_response(response_string):
    """
    Parse the decrypted CC Avenue response string into a dictionary.
    """
    res = {}
    params = response_string.split('&')
    for param in params:
        pair = param.split('=')
        if len(pair) == 2:
            res[pair[0]] = pair[1]
    return res
