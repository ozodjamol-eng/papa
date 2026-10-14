"""CLI: generate an Argon2 hash and random machine credentials locally."""
import getpass,secrets,sys
from argon2 import PasswordHasher

def main():
    if '--hash-password' in sys.argv:
        p=getpass.getpass('New owner password (minimum 14 characters): ')
        if len(p)<14:raise SystemExit('Password too short')
        p2=getpass.getpass('Repeat password: ')
        if p!=p2:raise SystemExit('Passwords do not match')
        print('NEXUS_OWNER_PASSWORD_HASH='+PasswordHasher().hash(p))
    elif '--generate-token' in sys.argv:
        print(secrets.token_urlsafe(36))
    else:raise SystemExit('Usage: python -m nexus_control.setup --hash-password | --generate-token')
if __name__=='__main__':main()
