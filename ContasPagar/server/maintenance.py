"""Administrative maintenance from the provider shell, with API process stopped."""
import argparse
import getpass
import os
from pathlib import Path
from app.database.connection import Database
from app.services.backup import BackupService
from server.security import Security


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['reset-password', 'restore'])
    parser.add_argument('target', help='E-mail existente ou caminho do backup')
    args = parser.parse_args()
    root = Path(os.environ.get('CONTASPAGAR_SERVER_DIR', '/var/data/contaspagar'))
    if not (root / 'contas_pagar.sqlite3').exists():
        raise SystemExit('Banco não encontrado. Verifique CONTASPAGAR_SERVER_DIR.')
    # Never race a live server while restoring/recovering access.
    import fcntl
    with open(root / 'server.lock', 'a+b') as guard:
        try:
            fcntl.flock(guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('Pare o processo da API antes da manutenção.')
        if args.action == 'reset-password':
            security = Security(root / 'acessos.sqlite3', '', '')
            user = next((u for u in security.users() if u['email'] == args.target.lower()), None)
            if not user:
                raise SystemExit('Usuário não encontrado.')
            password = getpass.getpass('Nova senha (mínimo 12 caracteres): ')
            if password != getpass.getpass('Repita a senha: '):
                raise SystemExit('As senhas não conferem.')
            security.update(user['id'], password, True)
            print('Acesso recuperado; sessões anteriores revogadas.')
        else:
            db = Database(root / 'contas_pagar.sqlite3')
            if input('Digite RESTAURAR para substituir os dados financeiros: ') != 'RESTAURAR':
                raise SystemExit('Cancelado.')
            previous = BackupService(db).restore(args.target)
            import uuid
            db.set_setting('online_revision', str(uuid.uuid4()))
            db.set_setting('online_day', '')
            db.set_setting('server_backup_day', '')
            db.engine.dispose()
            print('Restaurado. Cópia anterior:', previous)


if __name__ == '__main__':
    main()
