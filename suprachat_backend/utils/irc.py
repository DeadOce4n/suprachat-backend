import irctokens, socket


REGISTER_ERRORS = (
    "INVALID_USERNAME",
    "DISALLOWED",
    "ALREADY_REGISTERED",
    "INVALID_EMAIL",
    "USERNAME_EXISTS",
    "INVALID_PASSWORD",
    "UNACCEPTABLE_EMAIL",
    "UNKNOWN_ERROR",
)

VERIFY_ERRORS = ("DISALLOWED", "ALREADY_REGISTERED", "INVALID_CODE", "UNKNOWN_ERROR")


class IRCClient:
    """A basic class for connecting to a server in the localhost and perform
    account registration and verification using the `draft/account-registration`
    IRCv3 capability.
    """

    def __init__(self, webircpass: str, user_ip: str):
        """Inits IRCClient with a connection to the local IRCd"""
        self.webircpass = webircpass
        self.user_ip = user_ip
        self.d = irctokens.StatefulDecoder()
        self.e = irctokens.StatefulEncoder()
        self.s = socket.socket()

    def connect(self, server: str = None, port: int = None) -> bool:
        """
        Connects to the IRC server, hopefully located on the same machine.

        Args:
            server: The hostname or IP address of the IRCd server. Default is
                127.0.0.1
            port: The port on which the IRCd is listening. Default is 6667.

        Returns:
            A boolean indicating success or failure.
        """
        if server is None:
            server = "127.0.0.1"
        if port is None:
            port = 6667
        try:
            self.s.connect((server, port))
            return True
        except ConnectionRefusedError:
            return False

    def __send(self, line):
        """Sends a tokenized command to the IRCd"""
        print(f"> {line.format()}")
        self.e.push(line)
        while self.e.pending():
            self.e.pop(self.s.send(self.e.pending()))

    def register(self, username: str, email: str, passwd: str) -> dict[str, str | bool]:
        """
        Registers a new user using 'draft/account-registration' IRCv3 capability and
        returns a dictionary.

        Args:
            username: The name of the account to register. Must not contain any protocol
                breaking characters.
            email: The email of the account to register, required for verification.
            passwd: The password for the account, must not contain any protocol-breaking
                characters.

        Returns:
            A dict with two keys: 'success' and 'message', which should be used by the
            frontend to validate whether the registration was successful or not. For
            example:

                {'success': True,
                 'message': 'Registered successfully, awaiting verification'}
        """
        self.__send(
            irctokens.build(
                "WEBIRC", [self.webircpass, "*", self.user_ip, self.user_ip, "secure"]
            )
        )
        self.__send(irctokens.build("CAP", ["LS", "302"]))
        self.__send(irctokens.build("NICK", [username]))
        self.__send(irctokens.build("USER", [username, "*", "*", username]))

        while True:
            lines = self.d.push(self.s.recv(1024))
            if lines is None:
                self.s.close()
                return {"success": False, "message": "Disconnected from IRC server."}

            for line in lines:
                if line.command == "PING":
                    to_send = irctokens.build("PONG", [line.params[0]])
                    self.__send(to_send)
                elif line.command == "ERROR" and "incorrect password" in line.params[0]:
                    self.s.close()
                    return {"success": False, "message": "Wrong WebIRC password."}
                elif line.command == "CAP" and "ACK" not in line.params:
                    for param in line.params:
                        if "draft/account-registration" in param:
                            to_send = irctokens.build(
                                "CAP", ["REQ", "draft/account-registration"]
                            )
                            self.__send(to_send)
                elif line.command == "CAP" and "ACK" in line.params:
                    self.__send(irctokens.build("REGISTER", ["*", email, passwd]))
                    self.__send(irctokens.build("CAP", ["END"]))
                elif line.command == "FAIL" and line.params[1] in REGISTER_ERRORS:
                    return {
                        "success": False,
                        "message": f"Registration error: {line.params[3]}",
                    }
                elif line.command == "001":
                    self.__send(irctokens.build("QUIT"))
                    self.s.close()
                    return {
                        "success": True,
                        "message": "Registered successfully, awaiting verification.",
                    }

    def verify(self, username: str, code: str) -> dict[str, str | bool]:
        """
        Verifies a previously registered user with the verification code sent
        to its email and returns a dictionary.

        Args:
            username: The name of the account to verify.
            code: The verification code sent to the user's email.

        Returns:
            A dict with two keys: 'success' and 'message', which should be used
            by the frontend to validate whether the verification was successful
            or not. For example:

                {'success': 'True',
                 'message': 'Verification successful.'}
        """
        self.__send(
            irctokens.build(
                "WEBIRC", [self.webircpass, "*", self.user_ip, self.user_ip, "secure"]
            )
        )
        self.__send(irctokens.build("CAP", ["LS", "302"]))
        self.__send(irctokens.build("NICK", [username]))
        self.__send(irctokens.build("USER", [username, "*", "*", username]))
        self.__send(irctokens.build("VERIFY", [username, code]))

        while True:
            lines = self.d.push(self.s.recv(1024))
            if lines is None:
                self.s.close()
                return {"success": False, "message": "Disconnected from IRC server."}

            for line in lines:
                print(f"< {line.format()}")
                if line.command == "VERIFY" and "SUCCESS" in line.params:
                    self.__send(irctokens.build("QUIT"))
                    self.s.close()
                    return {"success": True, "message": "Verification successful."}
                elif line.command == "FAIL":
                    print(line.params)
                    self.__send(irctokens.build("QUIT"))
                    self.s.close()
                    return {
                        "success": False,
                        "message": f"Verification error: {line.params[2]}",
                    }
