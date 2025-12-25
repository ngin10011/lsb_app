# cli.py
import click
from sqlalchemy import text
from flask import current_app
from lsb_app.extensions import db
from seed import seed_data
from pathlib import Path
import shutil

def wipe_dir_contents(path: Path) -> int:
    """
    Löscht den Inhalt eines Ordners (Dateien + Unterordner), lässt den Ordner selbst bestehen.
    Gibt Anzahl gelöschter Einträge (top-level) zurück.
    """
    path.mkdir(parents=True, exist_ok=True)

    deleted = 0
    for p in path.iterdir():
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
        deleted += 1
    return deleted


def register_cli(app):
    @app.cli.command("dev-reset")
    def dev_reset():
        """
        Dev-Datenbank komplett leeren, Migrationen ausführen und Seed-Daten anlegen.
        ⚠️ Nur für Development gedacht!
        """
        if not app.debug and not app.config.get("TESTING", False):
            click.echo("❌ dev-reset ist nur im Debug-/Test-Modus erlaubt.")
            raise click.Abort()

        # --- Dateien/Ordner in instance leeren ---
        instance = Path(app.instance_path)  # .../lsb_app/lsb_app/instance
        anschreiben_dir = instance / "exports" / "anschreiben"
        postversand_dir = instance / "exports" / "postversand"
        invoices_dir = instance / "invoices"
        # logs_dir = instance / "logs"  # optional

        click.echo("🧹 Leere instance-Verzeichnisse ...")
        n1 = wipe_dir_contents(anschreiben_dir)
        n2 = wipe_dir_contents(postversand_dir)
        n3 = wipe_dir_contents(invoices_dir)
        # n4 = wipe_dir_contents(logs_dir)
        click.echo(f"✅ exports/anschreiben geleert ({n1} Einträge).")
        click.echo(f"✅ exports/psotversand geleert ({n2} Einträge)")
        click.echo(f"✅ invoices geleert ({n3} Einträge).")
        # click.echo(f"✅ logs geleert ({n4} Einträge).")

        click.echo("⚠️ Dropping schema 'public' (alle Tabellen, Daten, etc.) ...")

        db.session.execute(text("DROP SCHEMA IF EXISTS public CASCADE;"))
        db.session.execute(text("CREATE SCHEMA public;"))
        db.session.execute(text("GRANT ALL ON SCHEMA public TO public;"))
        db.session.execute(text("GRANT ALL ON SCHEMA public TO postgres;"))
        db.session.commit()

        click.echo("✅ Schema neu erstellt. Führe Migrationen aus ...")

        from flask_migrate import upgrade
        upgrade()

        click.echo("✅ Migrationen ausgeführt. Lege Seed-Daten an ...")
        seed_data()

        click.echo("🎉 Fertig! Dev-DB ist zurückgesetzt und mit Testdaten befüllt.")

    @app.cli.command("dev-seed")
    def dev_seed():
        """Nur Seed-Daten einfügen, ohne Schema-Reset/Migrationen."""
        if not app.debug and not app.config.get("TESTING", False):
            click.echo("❌ dev-seed ist nur im Debug-/Test-Modus erlaubt.")
            raise click.Abort()

        click.echo("🌱 Füge Seed-Daten hinzu ...")
        seed_data()
        click.echo("✅ Seed-Daten hinzugefügt.")

    @app.cli.command("dev-wipe")
    def dev_wipe():
        """
        Löscht alle Tabelleninhalte im public-Schema (TRUNCATE),
        setzt IDs zurück, lässt das Schema aber stehen.
        """
        if not app.debug and not app.config.get("TESTING", False):
            click.echo("❌ dev-wipe ist nur im Debug-/Test-Modus erlaubt.")
            raise click.Abort()

        click.echo("🧹 Leere alle Tabellen im Schema 'public' ...")

        db.session.execute(text("""
        DO
        $$
        DECLARE
            stmt text;
        BEGIN
            SELECT
                'TRUNCATE TABLE '
                || string_agg(quote_ident(tablename), ', ')
                || ' RESTART IDENTITY CASCADE'
            INTO stmt
            FROM pg_tables
            WHERE schemaname = 'public'
              AND tablename <> 'alembic_version';

            IF stmt IS NOT NULL THEN
                EXECUTE stmt;
            END IF;
        END;
        $$;
        """))
        db.session.commit()

        click.echo("✅ Alle Tabellen im public-Schema geleert.")
