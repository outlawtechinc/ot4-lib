import os
from dataclasses import dataclass
from pathlib import Path

DATA_FILE = Path('data.yaml')
ENC_FILE = Path('data.yaml.gpg')


@dataclass
class GPGConfig:
    ask_pass: bool = False
    password: str = os.environ.get('DEFAULT_GPG_PASS', 'defaultpass')
