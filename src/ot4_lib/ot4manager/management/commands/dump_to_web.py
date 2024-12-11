import niquests
from django.core.management.base import BaseCommand
from django.core.management import call_command
import json

from ot4_lib.ot4manager.management.commands._common import (
    DATA_FILE,
    ENC_FILE,
    GPGConfig,
    run_cmd,
)


class Command(BaseCommand):
    help = "Export in YAML format, encrypt and upload data to file.io."

    def add_arguments(self, parser):
        parser.add_argument(
            "--ask-pass", action="store_true", help="Prompt for GPG password"
        )

    def handle(self, *args, **options):
        ask_pass = options.get("ask_pass", False)
        if DATA_FILE.exists():
            DATA_FILE.unlink()
        if ENC_FILE.exists():
            ENC_FILE.unlink()
        call_command(
            "dumpdata", format="yaml"
        )
        if ask_pass:
            run_cmd(
                [
                    "gpg",
                    "--symmetric",
                    "--cipher-algo",
                    "AES256",
                    "--armor",
                    "--output",
                    str(ENC_FILE),
                    str(DATA_FILE),
                ]
            )
        else:
            password = GPGConfig().password
            run_cmd(
                [
                    "bash",
                    "-c",
                    f'echo "{password}" | gpg --batch --yes --passphrase-fd 0 '
                    f"--symmetric --cipher-algo AES256 --armor "
                    f"--output {ENC_FILE} {DATA_FILE}",
                ]
            )
        with ENC_FILE.open("rb") as f:
            response = niquests.post("https://file.io", files={"file": f})

        if response.status_code == 200:
            try:
                link = response.json()["link"]
                self.stdout.write(link)
            except (KeyError, json.JSONDecodeError):
                self.stderr.write("Failed to parse file.io response")
                self.stderr.write(response.text)
        else:
            self.stderr.write(
                f"Failed to upload file. Status code: {response.status_code}"
            )
            self.stderr.write(response.text)

        if DATA_FILE.exists():
            DATA_FILE.unlink()
        if ENC_FILE.exists():
            ENC_FILE.unlink()
