import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


from django.conf import settings


@dataclass
class PgParams:
    name: str
    user: str
    password: str
    host: str
    port: str


def get_pg_params() -> PgParams:
    DEFAULT_DB = settings.MAINDB
    db = settings.DATABASES[DEFAULT_DB]

    return PgParams(
        name=db["NAME"],
        user=db["USER"],
        password=db["PASSWORD"],
        host=db["HOST"],
        port=db["PORT"],
    )


class ManagementPrintHelpers:
    def out(self, msg: str, style=None):
        if msg is None:
            msg = ""
        if style:
            msg = style(msg)
        self.stdout.write(msg)

    def notice(self, msg: str = None):
        self.out(msg, self.style.NOTICE)

    def ok(self, msg: str = None):
        self.out(msg, self.style.SUCCESS)

    def err(self, msg: str = None):
        self.out(msg, self.style.ERROR)


def run_cmd(cmd: list[str], env: dict[str, str] | None = None) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, check=False)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)
    return result.stdout.strip()


@dataclass
class GpgConfig:
    ask_pass: bool = False
    password: str = os.environ.get("DEFAULT_GPG_PASS", "defaultpass")
    home = Path("/tmp/.gnupg")
    plain = Path("/tmp/ot4manager.dump")
    encrypted = Path("/tmp/ot4manager.dump.gpg")
