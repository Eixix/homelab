#!/usr/bin/env python3
"""Create private configuration without printing credentials or overwriting a game."""
import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile
from urllib.parse import urlsplit
from game import make_game, previous_pin_game


def password_hash(password):
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return f'scrypt${salt}${digest}'


def install_config(directory, content):
    if len(content)>1024*1024:raise ValueError('Konfiguration ist zu groß.')
    config=json.loads(content)
    parsed=urlsplit(config['origin'])
    if parsed.scheme!='https' or not parsed.netloc or parsed.path or parsed.query or parsed.fragment or parsed.username:
        raise ValueError('Konfiguration benötigt eine HTTPS-Origin.')
    algorithm,salt,digest=config['password_hash'].split('$')
    if algorithm!='scrypt' or len(bytes.fromhex(salt))!=16 or len(bytes.fromhex(digest))!=64:
        raise ValueError('Ungültiger Passworthash.')
    roles=config['roles']
    if sorted(roles.values())!=['a','b'] or any(len(bytes.fromhex(token))!=32 for token in roles):
        raise ValueError('Ungültige Rollenkennungen.')
    if config['game']['schema']!=2 or len(config['game']['stages'])!=5:
        raise ValueError('Ungültige Spielversion.')
    directory=Path(directory)
    target=directory/'config.json'
    if target.exists():
        current=json.loads(target.read_text())
        if current==config:return False
        previous=json.loads(json.dumps(config))
        previous['game']=previous_pin_game(config['game'])
        if current!=previous:
            raise ValueError('Vorhandene Spielkonfiguration weicht ab; sie wird nicht überschrieben.')
        os.umask(0o077)
        with tempfile.NamedTemporaryFile(mode='w',dir=directory,delete=False) as staged:
            temporary=Path(staged.name)
            json.dump(config,staged,ensure_ascii=False,indent=2)
            staged.write('\n')
        os.replace(temporary,target)
        return True
    os.umask(0o077)
    directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    with tempfile.NamedTemporaryFile(mode='w',dir=directory,delete=False) as staged:
        temporary=Path(staged.name)
        json.dump(config,staged,ensure_ascii=False,indent=2)
        staged.write('\n')
    try:
        os.link(temporary,target)
    finally:
        temporary.unlink()
    return True


def main():
    parser = argparse.ArgumentParser(description='Privates Hochzeitsspiel einrichten')
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--origin', default='https://cupweddinggift.betz.coffee', help='Kanonische HTTPS-Origin für lokale und entfernte Bereitstellung')
    parser.add_argument('--personalize', type=Path)
    parser.add_argument('--generate-password', action='store_true', help='Zufälliges Passwort in privater password.txt speichern')
    parser.add_argument('--install-config', action='store_true', help='Private Konfiguration vom Deploy-Workflow über stdin übernehmen')
    args = parser.parse_args()
    if args.install_config:
        try:install_config(args.directory,sys.stdin.buffer.read(1024*1024+1))
        except (ValueError,KeyError,TypeError) as error:parser.error(str(error))
        print('Private Spielkonfiguration geprüft und bereitgestellt.')
        return
    parsed = urlsplit(args.origin)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.path or parsed.query or parsed.fragment or parsed.username:
        parser.error('Die Adresse muss eine HTTPS-Origin ohne Pfad sein.')
    if args.directory.exists():
        parser.error('Das Ziel existiert bereits. Bestehende Spiele werden nicht überschrieben.')
    password = secrets.token_urlsafe(24) if args.generate_password else getpass.getpass('Gemeinsames Passwort (mindestens 16 Zeichen): ')
    if len(password) < 16 or (not args.generate_password and password != getpass.getpass('Passwort wiederholen: ')):
        parser.error('Passwörter stimmen nicht überein oder sind zu kurz.')
    personal = json.loads(args.personalize.read_text()) if args.personalize else None
    game = make_game(personal)
    tokens = {role: secrets.token_urlsafe(32) for role in ('a','b')}
    config = dict(origin=args.origin, password_hash=password_hash(password),
                  roles={hashlib.sha256(token.encode()).hexdigest(): role for role, token in tokens.items()}, game=game)
    os.umask(0o077)
    args.directory.mkdir(parents=True, mode=0o700)
    (args.directory / 'config.json').write_text(json.dumps(config, ensure_ascii=False, indent=2)+'\n')
    links = '\n'.join(f"{game['names'][role]}: {args.origin}/{role}/{tokens[role]}" for role in tokens)
    (args.directory / 'links.txt').write_text(links+'\n')
    if args.generate_password:
        (args.directory / 'password.txt').write_text(password+'\n')
    print(f"Konfiguration und persönliche Links wurden in {args.directory} gespeichert. Keine Zugangsdaten wurden ausgegeben.")


if __name__ == '__main__':
    main()
