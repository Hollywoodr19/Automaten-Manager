# Python Script zum Generieren sicherer Passwörter
import secrets
import string

def generate_password(length=24):
    alphabet = string.ascii_letters + string.digits + "!@#$%&*"
    password = ''.join(secrets.choice(alphabet) for i in range(length))
    return password

def generate_secret_key():
    return secrets.token_hex(32)

print(f"Neues Passwort: {generate_password()}")
print(f"Neuer Secret Key: {generate_secret_key()}")