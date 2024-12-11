from django.core.management.base import BaseCommand
from django.core.management import call_command
import subprocess
import sys

from ot4_lib.ot4manager.management.commands._constants import DATA_FILE, ENC_FILE, \
    GPGConfig


def run_cmd(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)
    return result.stdout.strip()

class Command(BaseCommand):
    help = 'Download, decrypt and import YAML data from file.io'

    def add_arguments(self, parser):
        parser.add_argument('--url', required=True, help='file.io download link')
        parser.add_argument('--ask-pass', action='store_true', help='Prompt for GPG password')

    def handle(self, *args, **options):
        if DATA_FILE.exists():
            DATA_FILE.unlink()
        if ENC_FILE.exists():
            ENC_FILE.unlink()

        url = options['url']
        ask_pass = options.get('ask_pass', False)

        # Скачиваем зашифрованный файл
        run_cmd(['curl', '-o', str(ENC_FILE), url])

        # Расшифровка
        if ask_pass:
            run_cmd(['gpg', '--decrypt', '--output', str(DATA_FILE), str(ENC_FILE)])
        else:
            # Автоматический декрипт с использованием пароля из окружения или дефолтного
            password = GPGConfig().password
            run_cmd([
                'bash','-c',
                f'echo \"{password}\" | gpg --batch --yes --passphrase-fd 0 '
                f'--decrypt --output {DATA_FILE} {ENC_FILE}'
            ])

        # Импортируем данные в БД
        call_command('loaddata', str(DATA_FILE))

        # Очистка временных файлов
        if DATA_FILE.exists():
            DATA_FILE.unlink()
        if ENC_FILE.exists():
            ENC_FILE.unlink()
