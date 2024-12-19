import json
import os

import niquests
from django.core.management.base import BaseCommand
from ._common import GpgConfig
from ._common import ManagementPrintHelpers
from ._common import get_pg_params
from ._common import run_cmd

g = GpgConfig()


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
            self.setup_gnupg()
            self.run_export_process(ask_pass)
        except Exception as e:
            self.err(f"Error occurred: {e}")
            raise
        finally:
            self.cleanup()
            if self.uploaded_link:
                self.ok()
                self.out(self.uploaded_link)

    def setup_gnupg(self):
        # Ensure GNUPG home directory
        if not g.home.exists():
            g.home.mkdir(mode=0o700, exist_ok=True)
        else:
            g.home.chmod(0o700)

    def run_export_process(self, ask_pass: bool):
        self.notice("Starting full database export...")
        self.out(
            f"Settings: plain_file={g.plain.absolute()}, encrypted_file={g.encrypted.absolute()}"
        )
        pg = self.ensure_port_string(get_pg_params())
        env = {"PGPASSWORD": pg.password, "GNUPGHOME": str(g.home), **os.environ}

        self.cleanup()
        self.dump_database(pg, env)
        self.encrypt_dump(ask_pass, env)
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
                str(g.plain),
            ],
            env=env,
        )
        self.ok("Database dump created.")

    def encrypt_dump(self, ask_pass: bool, env):
        self.notice("Encrypting dump with GPG...")
        if ask_pass:
            run_cmd(
                [
                    "gpg",
                    "--homedir",
                    str(g.home),
                    "--symmetric",
                    "--cipher-algo",
                    "AES256",
                    "--armor",
                    "--output",
                    str(g.encrypted),
                    str(g.plain),
                ],
                env=env,
            )
        else:
            run_cmd(
                [
                    "bash",
                    "-c",
                    f'echo "{g.password}" | gpg --batch --yes --homedir "{g.home}" --passphrase-fd 0 --symmetric --cipher-algo AES256 --armor --output {g.encrypted} {g.plain}',
                ],
                env=env,
            )
        self.ok("Dump encrypted.")

    def upload_dump(self):
        self.notice("Uploading encrypted dump to file.io...")
        with g.encrypted.open("rb") as f:
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
        g.plain.unlink(missing_ok=True)
        g.encrypted.unlink(missing_ok=True)
