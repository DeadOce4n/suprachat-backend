import os
from signal import SIGTERM
from subprocess import Popen, run


class Ircd:
    def __init__(self, path):
        self.path = path
        try:
            os.remove(os.path.join(self.path, "ircd.db"))
        except FileNotFoundError:
            pass
        run(
            (
                os.path.join(self.path, "ergo"),
                "initdb",
                "--conf",
                os.path.join(self.path, "ircd.yaml"),
                "--quiet",
            )
        )

    def __enter__(self):
        self.p = Popen(
            [
                os.path.join(self.path, "ergo"),
                "run",
                "--conf",
                os.path.join(self.path, "ircd.yaml"),
            ]
        )

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.p.send_signal(SIGTERM)
