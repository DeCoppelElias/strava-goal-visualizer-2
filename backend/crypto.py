from cryptography.fernet import Fernet, InvalidToken


class Crypto:
    def __init__(self, encryption_key: str) -> None:
        key = encryption_key
        try:
            self._fernet = Fernet(key.encode())
        except Exception as e:
            raise RuntimeError(
                "Invalid TOKEN_ENCRYPTION_KEY. " "Expected a valid Fernet key."
            ) from e

    def encrypt(self, plaintext: str) -> str:
        encrypted = self._fernet.encrypt(plaintext.encode())
        return encrypted.decode()

    def decrypt(self, ciphertext: str) -> str:
        try:
            decrypted = self._fernet.decrypt(ciphertext.encode())
            return decrypted.decode()
        except InvalidToken as e:
            raise ValueError("Invalid encrypted token.") from e
