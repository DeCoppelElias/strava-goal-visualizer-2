import pytest
from backend.shared.crypto import Crypto
from cryptography.fernet import Fernet


class TestCrypto:
    def test_encrypt_decrypt_returns_original_value(self):
        # Arrange
        key = Fernet.generate_key().decode()
        crypto = Crypto(key)

        token = "secret_strava_refresh_token"  # noqa: S105

        # Act
        encrypted = crypto.encrypt(token)
        decrypted = crypto.decrypt(encrypted)

        # Assert
        assert decrypted == token

    def test_encrypt_does_not_return_plaintext(self):
        # Arrange
        key = Fernet.generate_key().decode()
        crypto = Crypto(key)

        token = "secret_strava_refresh_token"  # noqa: S105

        # Act
        encrypted = crypto.encrypt(token)

        # Assert
        assert encrypted != token

    def test_decrypt_invalid_ciphertext_raises_error(self):
        # Arrange
        key = Fernet.generate_key().decode()
        crypto = Crypto(key)

        invalid_ciphertext = "this-is-not-valid"

        # Act + Assert
        with pytest.raises(ValueError) as exc_info:
            crypto.decrypt(invalid_ciphertext)

        assert str(exc_info.value) == "Invalid encrypted token."

    def test_missing_key_raises_error(self):
        # Act + Assert
        with pytest.raises(RuntimeError) as exc_info:
            Crypto("")

        assert str(exc_info.value) == "Invalid TOKEN_ENCRYPTION_KEY. Expected a valid Fernet key."

    def test_invalid_key_raises_error(self):
        # Arrange
        invalid_key = "not-a-valid-fernet-key"

        # Act + Assert
        with pytest.raises(RuntimeError) as exc_info:
            Crypto(invalid_key)

        assert str(exc_info.value) == "Invalid TOKEN_ENCRYPTION_KEY. Expected a valid Fernet key."

    def test_encrypt_same_value_twice_returns_different_ciphertext(self):
        # Arrange
        key = Fernet.generate_key().decode()
        crypto = Crypto(key)

        token = "same_token"  # noqa: S105

        # Act
        encrypted_1 = crypto.encrypt(token)
        encrypted_2 = crypto.encrypt(token)

        # Assert
        assert encrypted_1 != encrypted_2
        assert crypto.decrypt(encrypted_1) == token
        assert crypto.decrypt(encrypted_2) == token
