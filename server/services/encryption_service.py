"""
Encryption Service
==================
Secure password encryption using Fernet symmetric encryption.
Replaces insecure base64 encoding.
"""

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional


class PasswordEncryption:
    """
    Secure password encryption service.
    """
    
    _cipher = None
    
    @classmethod
    def _get_cipher(cls) -> Fernet:
        """
        Get or create the Fernet cipher.
        
        Returns:
            Fernet cipher instance
        """
        if cls._cipher is None:
            # Get or generate encryption key
            encryption_key = os.getenv("ENCRYPTION_KEY")
            
            if not encryption_key:
                # Generate a key from a secret + salt
                secret = os.getenv("SECRET_KEY", "farmtopeople-default-secret")
                salt = os.getenv("ENCRYPTION_SALT", "ftp-salt-2025").encode()
                
                # Derive a key from the secret
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
                cls._cipher = Fernet(key)
            else:
                cls._cipher = Fernet(encryption_key.encode())
        
        return cls._cipher
    
    @classmethod
    def encrypt_password(cls, password: str) -> str:
        """
        Encrypt a password securely.
        
        Args:
            password: Plain text password
            
        Returns:
            Encrypted password string
        """
        if not password:
            return ""
        
        cipher = cls._get_cipher()
        encrypted = cipher.encrypt(password.encode())
        return encrypted.decode('utf-8')
    
    @classmethod
    def decrypt_password(cls, encrypted_password: str) -> Optional[str]:
        """
        Decrypt a password.
        
        Args:
            encrypted_password: Encrypted password string
            
        Returns:
            Decrypted password or None if decryption fails
        """
        if not encrypted_password:
            return None
        
        try:
            cipher = cls._get_cipher()
            decrypted = cipher.decrypt(encrypted_password.encode())
            return decrypted.decode('utf-8')
        except Exception as e:
            print(f"⚠️ Decryption failed: {e}")
            
            # Try legacy base64 decoding as fallback
            try:
                legacy = base64.b64decode(encrypted_password).decode('utf-8')
                print(f"⚠️ Using legacy base64 decoding - please re-encrypt!")
                return legacy
            except:
                return None
    
    @classmethod
    def migrate_from_base64(cls, base64_password: str) -> str:
        """
        Migrate from base64 to proper encryption.
        
        Args:
            base64_password: Base64 encoded password
            
        Returns:
            Properly encrypted password
        """
        try:
            # Decode base64
            plain_password = base64.b64decode(base64_password).decode('utf-8')
            # Re-encrypt properly
            return cls.encrypt_password(plain_password)
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            return base64_password  # Return original if migration fails


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.
    
    Returns:
        Base64 encoded encryption key
    """
    key = Fernet.generate_key()
    return key.decode('utf-8')


def test_encryption():
    """
    Test the encryption service.
    """
    print("\n🔐 Testing Password Encryption...")
    
    # Test password
    test_password = "MyS3cur3P@ssw0rd!"
    
    # Encrypt
    encrypted = PasswordEncryption.encrypt_password(test_password)
    print(f"  Original: {test_password}")
    print(f"  Encrypted: {encrypted[:20]}... (length: {len(encrypted)})")
    
    # Decrypt
    decrypted = PasswordEncryption.decrypt_password(encrypted)
    
    if decrypted == test_password:
        print(f"  ✅ Encryption/Decryption successful")
        return True
    else:
        print(f"  ❌ Decryption failed!")
        return False


if __name__ == "__main__":
    # Generate a new key for .env file
    print("\n🔑 New encryption key for .env file:")
    print(f"ENCRYPTION_KEY={generate_encryption_key()}")
    
    # Test encryption
    test_encryption()