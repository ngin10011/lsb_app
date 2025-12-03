# cli.py
import click
from sqlalchemy import text
from flask import current_app
from lsb_app.extensions import db
from seed import seed_data


def register_cli(app):
    @app.cli.command("dev-reset")
    def dev_reset():
        """
        Dev-Datenbank komplett leeren, Migrationen ausführen und Seed-Daten anlegen.
        ⚠️ Nur für Development gedacht!
        """
        # kleine Sicherheit: in PROD lieber abbrechen
        if not app.debug and not app.config.get("TESTING", False):
            click.echo("❌ dev-reset ist nur im Debug-/Test-Modus erlaubt.")
            raise click.Abort()

        click.echo("⚠️ Dropping schema 'public' (alle Tabellen, Daten, etc.) ...")

        # PostgreSQL: Schema public komplett löschen
        db.session.execute(text("DROP SCHEMA IF EXISTS public CASCADE;"))
        db.session.execute(text("CREATE SCHEMA public;"))
        db.session.execute(text("GRANT ALL ON SCHEMA public TO public;"))
        db.session.execute(text("GRANT ALL ON SCHEMA public TO postgres;"))
        db.session.commit()

        click.echo("✅ Schema neu erstellt. Führe Migrationen aus ...")

        # Migrationen hochziehen
        from flask_migrate import upgrade
        upgrade()

        click.echo("✅ Migrationen ausgeführt. Lege Seed-Daten an ...")

        seed_data()

        click.echo("🎉 Fertig! Dev-DB ist zurückgesetzt und mit Testdaten befüllt.")
