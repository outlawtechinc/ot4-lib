from pathlib import Path
from dataclasses import dataclass
from django.core.management.base import BaseCommand
from django.core.management import call_command
import subprocess
import json
import os
import sys

DATA_FILE = Path('data.yaml')
ENC_FILE = Path('data.yaml.gpg')

@dataclass
class GPGConfig:
    ask_pass: bool = False
    password: str = os.environ.get('DEFAULT_GPG_PASS', 'defaultpass')

def run_cmd(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)
    return result.stdout.strip()

class Command(BaseCommand):
    help = 'Export in YAML format, encrypt and upload data to file.io.'

    def add_arguments(self, parser):
        parser.add_argument('--ask-pass', action='store_true', help='Prompt for GPG password')

    def handle(self, *args, **options):
        ask_pass = options.get('ask_pass', False)
        if DATA_FILE.exists():
            DATA_FILE.unlink()
        if ENC_FILE.exists():
            ENC_FILE.unlink()
        call_command('dumpdata', exclude=['auth.permission','contenttypes'], format='yaml')
        if ask_pass:
            run_cmd([
                'gpg', '--symmetric', '--cipher-algo', 'AES256', '--armor',
                '--output', str(ENC_FILE), str(DATA_FILE)
            ])
        else:
            password = GPGConfig().password
            run_cmd([
                'bash','-c',
                f'echo "{password}" | gpg --batch --yes --passphrase-fd 0 '
                f'--symmetric --cipher-algo AES256 --armor '
                f'--output {ENC_FILE} {DATA_FILE}'
            ])
        curl_out = run_cmd(['curl','-F', f'file=@{ENC_FILE}', 'https://file.io'])
        try:
            link = json.loads(curl_out)['link']
            self.stdout.write(link)
        except Exception:
            self.stderr.write('Failed to parse file.io response')
            self.stderr.write(curl_out)
        if DATA_FILE.exists():
            DATA_FILE.unlink()
        if ENC_FILE.exists():
            ENC_FILE.unlink()

