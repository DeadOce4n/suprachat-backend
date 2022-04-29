import base64
import json
import subprocess


def check_password_hash(password_hash: str, password: str) -> bool:
    """
    Calls ergo's checkpasswd subcommand via subprocess invocation.
    https://github.com/ergochat/ergo/tree/devel+pwcheck

    Args:
        password_hash: The password hash, taken from the database.
        password: The password to check against the hash, taken from
            the user's input.

    Returns:
        A boolean indicating success or failure.
    """
    payload: str = (
        f"{json.dumps([base64.b64decode(password_hash).decode('utf-8'), password])}\n"
    )

    out = subprocess.run(
        ("/home/oragono/ergo", "checkpasswd"), input=payload.encode("utf-8")
    )

    return not out.returncode
