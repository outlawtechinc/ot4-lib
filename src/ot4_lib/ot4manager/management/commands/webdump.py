import json
import os

import niquests
from django.core.management.base import BaseCommand
from ._common import DATA_FILE
from ._common import ENC_FILE
from ._common import GPGConfig

from ._common import ManagementPrintHelpers
from ._common import get_pg_params
from ._common import run_cmd


class Command(BaseCommand, ManagementPrintHelpers):
    help = "Create a full PostgreSQL database dump, encrypt it and upload to file.io"
    uploaded_link = None

    def add_arguments(self, parser):
        parser.add_argument(
            "--ask-pass", action="store_true", help="Prompt for GPG password"
        )

    def handle(self, *args, **options):
        ask_pass = options.get("ask_pass", False)
        try:
            self.run_export_process(ask_pass)
        except Exception as e:
            self.err(f"Error occurred: {e}")
            raise
        finally:
            self.cleanup()
            if self.uploaded_link:
                self.ok()
                self.out(self.uploaded_link)

    def run_export_process(self, ask_pass: bool):
        self.notice("Starting full database export...")
        self.out(
            f"Settings: plain_file={DATA_FILE.absolute()}, encrypted_file={ENC_FILE.absolute()}"
        )
        pg = self.ensure_port_string(get_pg_params())
        env = {"PGPASSWORD": pg.password, **os.environ}
        self.cleanup()
        self.dump_database(pg, env)
        self.encrypt_dump(ask_pass)
        self.upload_dump()
        self.ok("Export process completed.")

    def ensure_port_string(self, pg):
        if not isinstance(pg.port, str):
            pg = pg.__class__(
                name=pg.name,
                user=pg.user,
                password=pg.password,
                host=pg.host,
                port=str(pg.port),
            )
        return pg

    def dump_database(self, pg, env):
        self.notice("Creating database dump (pg_dump)...")
        run_cmd(
            [
                "pg_dump",
                "-Fc",
                "-U",
                pg.user,
                "-h",
                pg.host,
                "-p",
                pg.port,
                "-d",
                pg.name,
                "-f",
                str(DATA_FILE),
            ],
            env=env,
        )
        self.ok("Database dump created.")

    def encrypt_dump(self, ask_pass: bool):
        self.notice("Encrypting dump with GPG...")
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
                    f'echo "{password}" | gpg --batch --yes --passphrase-fd 0 --symmetric --cipher-algo AES256 --armor --output {ENC_FILE} {DATA_FILE}',
                ]
            )
        self.ok("Dump encrypted.")

    def upload_dump(self):
        self.notice("Uploading encrypted dump to file.io...")
        with ENC_FILE.open("rb") as f:
            response = niquests.post("https://file.io", files={"file": f})
        if response.status_code == 200:
            try:
                link = response.json()["link"]
                self.uploaded_link = link
                self.ok(f"Upload successful: {link}")
            except (KeyError, json.JSONDecodeError):
                self.err("Failed to parse file.io response")
                self.stderr.write(response.text)
        else:
            self.err(f"Failed to upload file. Status code: {response.status_code}")
            self.stderr.write(response.text)

    def cleanup(self):
        self.notice("Cleaning up temporary files...")
        DATA_FILE.unlink(missing_ok=True)
        ENC_FILE.unlink(missing_ok=True)
