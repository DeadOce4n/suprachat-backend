import hashlib
import bcrypt
import base64


def check_password_hash(password_hash: str, password: str) -> bool:
    password_to_check = hashlib.sha3_512(password.encode("utf-8")).digest()
    stored_hash = base64.b64decode(password_hash.encode("utf-8"))
    return bcrypt.checkpw(password_to_check, stored_hash)
