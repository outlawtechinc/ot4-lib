from pathlib import Path
from django.core.management.base import BaseCommand
from django.core.management import call_command
import subprocess
import sys

DATA_FILE = Path('data.yaml')
ENC_FILE = Path('data.yaml.gpg')

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

    def handle(self, *args, **options):
        if DATA_FILE.exists():
            DATA_FILE.unlink()
        if ENC_FILE.exists():
            ENC_FILE.unlink()
        url = options['url']
        run_cmd(['curl','-o',str(ENC_FILE),url])
        run_cmd(['gpg','--decrypt','--output',str(DATA_FILE),str(ENC_FILE)])
        call_command('loaddata', str(DATA_FILE))
        if DATA_FILE.exists():
            DATA_FILE.unlink()
        if ENC_FILE.exists():
            ENC_FILE.unlink()

