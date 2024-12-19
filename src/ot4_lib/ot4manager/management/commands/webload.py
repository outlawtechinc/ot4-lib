import os

from django.core.management.base import BaseCommand

from ._common import GpgConfig
from ._common import ManagementPrintHelpers
from ._common import get_pg_params
from ._common import run_cmd


g = GpgConfig()


def get_url_last_six_chars(url: str) -> str:
    # Remove all non-ASCII and non-printable chars from the URL before taking last 6
    url_cleaned = "".join(ch for ch in url if 32 <= ord(ch) <= 126)
    return url_cleaned[-6:]


class Command(BaseCommand, ManagementPrintHelpers):
    help = "Download, decrypt and restore a full PostgreSQL database dump from file.io"
    keep_file = False

    def add_arguments(self, parser):
        parser.add_argument("url", help="file.io download link to the encrypted dump")
        parser.add_argument(
            "--ask-pass",
            action="store_true",
            help="Prompt for GPG password",
        )
        parser.add_argument(
            "--keep",
            action="store_true",
            default=False,
            help="Do not remove the decrypted file after loading",
        )
        parser.add_argument(
            "--noinput",
            action="store_true",
            help="Do not prompt for confirmation",
        )

    def handle(self, *args, **options):
        self.keep_file = options.get("keep", False)
        noinput = options.get("noinput", False)
        url = options["url"]
        ask_pass = options.get("ask_pass", False)

        if not noinput:
            self.confirm_destructive_actions(url)

        try:
            self.run_import_process(url, ask_pass)
        except Exception as e:
            self.err(f"Error occurred: {e}")
            raise
        finally:
            self.cleanup()

    def confirm_destructive_actions(self, url: str):
        last_six = get_url_last_six_chars(url)
        self.err("WARNING: THIS WILL DESTROY AND RECREATE THE DATABASE.")
        self.err(
            "TO CONFIRM, PLEASE ENTER THE LAST 6 CHARACTERS OF THE URL EXACTLY AS SHOWN BELOW:",
        )
        self.err(f"LAST 6 CHARS: {last_six}")
        user_input = input("CONFIRM (LAST 6 CHARS): ")
        if user_input != last_six:
            self.err("Confirmation failed. Aborting.")
            raise SystemExit(1)

    def run_import_process(self, url: str, ask_pass: bool):
        self.notice("Starting full database import...")
        self.out(
            f"Settings: plain_file={g.plain.absolute()}, encrypted_file={g.encrypted.absolute()}"
        )
        pg = self.ensure_port_string(get_pg_params())
        env = {"PGPASSWORD": pg.password, **os.environ}
        self.cleanup()
        self.download_dump(url)
        self.decrypt_dump(ask_pass)
        self.recreate_database(pg, env)
        self.restore_dump(pg, env)
        self.ok("Import process completed.")

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

    def download_dump(self, url: str):
        self.notice(f"Downloading encrypted dump from {url}...")
        run_cmd(["curl", "-f", "-o", str(g.encrypted), url])
        self.ok("Encrypted dump downloaded.")

    def decrypt_dump(self, ask_pass: bool):
        self.notice("Decrypting dump with GPG...")
        if ask_pass:
            run_cmd(["gpg", "--decrypt", "--output", str(g.plain), str(g.encrypted)])
        else:
            password = GpgConfig().password
            run_cmd(
                [
                    "bash",
                    "-c",
                    f'echo "{password}" | gpg --batch --yes --passphrase-fd 0 --decrypt --output {g.plain} {g.encrypted}',
                ],
            )
        self.ok("Dump decrypted.")

    def recreate_database(self, pg, env):
        self.notice("Recreating database...")
        run_cmd(
            [
                "psql",
                "-U",
                pg.user,
                "-h",
                pg.host,
                "-p",
                pg.port,
                "-d",
                "postgres",
                "-c",
                f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{pg.name}' AND pid <> pg_backend_pid();",
            ],
            env=env,
        )
        run_cmd(
            ["dropdb", "-U", pg.user, "-h", pg.host, "-p", pg.port, pg.name],
            env=env,
        )
        run_cmd(
            ["createdb", "-U", pg.user, "-h", pg.host, "-p", pg.port, pg.name],
            env=env,
        )
        self.ok("Database recreated.")

    def restore_dump(self, pg, env):
        self.notice("Restoring dump (pg_restore)...")
        run_cmd(
            [
                "pg_restore",
                "--no-owner",
                "--no-acl",
                "-U",
                pg.user,
                "-h",
                pg.host,
                "-p",
                pg.port,
                "-d",
                pg.name,
                str(g.plain),
            ],
            env=env,
        )
        self.ok("Database restored successfully.")

    def cleanup(self):
        if not self.keep_file:
            self.notice("Cleaning up temporary files...")
            g.plain.unlink(missing_ok=True)
            g.encrypted.unlink(missing_ok=True)
            self.ok("Temporary files removed.")
