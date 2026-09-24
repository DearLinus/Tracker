#!/usr/bin/env python3
"""Generate a Fernet key for encrypting record counts."""

from cryptography.fernet import Fernet

if __name__ == "__main__":
    print(Fernet.generate_key().decode())
