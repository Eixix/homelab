#!/usr/bin/env python3
"""Reset one wedding game database without changing its private configuration."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import secrets
import sqlite3


def reset(database, backup_dir):
    os.umask(0o077)
    database=Path(database)
    backup_dir=Path(backup_dir)
    if not database.is_file():
        raise FileNotFoundError(f'Wedding database does not exist: {database}')
    backup_dir.mkdir(parents=True,exist_ok=True,mode=0o700)
    backup=backup_dir/f'wedding-before-reset-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{secrets.token_hex(4)}.sqlite3'
    with sqlite3.connect(database) as db:
        if db.execute('SELECT COUNT(*) FROM progress WHERE id=1').fetchone()[0]!=1:
            raise ValueError('Wedding progress row is missing; no reset performed.')
        with sqlite3.connect(backup) as saved:
            db.backup(saved)
        backup.chmod(0o600)
        db.execute('BEGIN IMMEDIATE')
        db.execute('UPDATE progress SET stage=0,a=0,b=0,version=version+1 WHERE id=1')
        for table in ('runtime','hints','awards'):
            db.execute(f'DELETE FROM {table}')
        db.execute("INSERT OR REPLACE INTO metadata(key,value) VALUES ('reset',?)",(secrets.token_hex(12),))
        db.commit()
    return backup


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Reset wedding game progress and keep a private database backup.')
    parser.add_argument('--db',required=True,type=Path)
    parser.add_argument('--backup-dir',required=True,type=Path)
    args=parser.parse_args()
    print(f'Wedding progress reset. Backup: {reset(args.db,args.backup_dir)}')
