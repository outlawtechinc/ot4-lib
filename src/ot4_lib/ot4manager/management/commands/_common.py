import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

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
