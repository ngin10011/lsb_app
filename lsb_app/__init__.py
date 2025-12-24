# lsb_app/__init__.py
import os
from flask import Flask
from flask_migrate import Migrate
from dotenv import load_dotenv
from lsb_app.extensions import db, csrf
import logging
from logging.handlers import RotatingFileHandler
from cli import register_cli


migrate = Migrate(compare_type=True, render_as_batch=True)

def create_app():
    load_dotenv()

    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    # Basis-Konfiguration
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-key")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(app.instance_path, "site.db")
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Sensitive Business-Daten
    app.config["COMPANY_NAME"] = os.getenv("COMPANY_NAME", "NAME_NICHT_GESETZT")
    app.config["COMPANY_ROLE"] = os.getenv("COMPANY_ROLE", "")
    app.config["COMPANY_ADDRESS"] = os.getenv("COMPANY_ADDRESS", "")
    app.config["COMPANY_PHONE"] = os.getenv("COMPANY_PHONE", "")
    app.config["COMPANY_EMAIL"] = os.getenv("COMPANY_EMAIL", "")
    app.config["BANK_IBAN"] = os.getenv("BANK_IBAN", "")
    app.config["BANK_BIC"] = os.getenv("BANK_BIC", "")
    app.config["TAX_NUMBER"] = os.getenv("TAX_NUMBER", "")

    # openrouteservice
    app.config["STARTADRESSE"] = os.getenv("STARTADRESSE", "")
    app.config["ORS_API_KEY"] = os.getenv("ORS_API_KEY", "")

    app.config["NOMINATIM_URL"] = os.getenv("NOMINATIM_URL", "https://nominatim.openstreetmap.org/search")
    app.config["NOMINATIM_USER_AGENT"] = os.getenv("NOMINATIM_USER_AGENT", "LSBayern/1.0 (info@example.com)")

    # Mail-Konfiguration (SMTP)
    app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER", "smtp.mail.de")
    app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", "587"))
    app.config["MAIL_USE_TLS"] = os.getenv("MAIL_USE_TLS", "1") == "1"
    app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME", "")
    app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD", "")
    app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_DEFAULT_SENDER", app.config["MAIL_USERNAME"])
    app.config["MAIL_IMAP_SERVER"] = os.getenv("MAIL_IMAP_SERVER", "")
    app.config["MAIL_IMAP_PORT"] = int(os.getenv("MAIL_IMAP_PORT", "993"))
    app.config["MAIL_IMAP_FOLDER"] = os.getenv("MAIL_IMAP_FOLDER", "Rechnungen")

    # YNAB-Konfiguration
    app.config["YNAB_ACCESS_TOKEN"] = os.getenv("YNAB_ACCESS_TOKEN", "")
    app.config["YNAB_BUDGET_ID"] = os.getenv("YNAB_BUDGET_ID", "")





    # Für Jinja verfügbar machen: {{ config.BANK_IBAN }} usw.
    @app.context_processor
    def inject_config():
        return dict(config=app.config)

    # Extensions
    db.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    # Blueprints registrieren
    from lsb_app.blueprints.patients import bp as patients_bp
    app.register_blueprint(patients_bp, url_prefix="/patients")

    from lsb_app.blueprints.tb import bp as tb_bp
    app.register_blueprint(tb_bp, url_prefix="/tb")

    from lsb_app.blueprints.debug import bp as debug_bp
    app.register_blueprint(debug_bp, url_prefix="/debug")

    from lsb_app.blueprints.home.routes import bp as home_bp
    app.register_blueprint(home_bp)

    from lsb_app.blueprints.addresses import bp as addresses_bp
    app.register_blueprint(addresses_bp, url_prefix="/addresses")

    from lsb_app.blueprints.auftraege import bp as auftraege_bp
    app.register_blueprint(auftraege_bp, url_prefix="/auftraege")

    from lsb_app.blueprints.institute import bp as institute_bp
    app.register_blueprint(institute_bp, url_prefix="/institute")

    from lsb_app.blueprints.angehoerige import bp as angehoerige_bp
    app.register_blueprint(angehoerige_bp, url_prefix="/angehoerige")

    from lsb_app.blueprints.behoerden import bp as behoerden_bp
    app.register_blueprint(behoerden_bp, url_prefix="/behoerden")

    from lsb_app.blueprints.rechnungen import bp as rechnungen_bp
    app.register_blueprint(rechnungen_bp, url_prefix="/rechnungen")

    from lsb_app.blueprints.verlauf import bp as verlauf_bp
    app.register_blueprint(verlauf_bp)

    from lsb_app.blueprints.zahlungen import bp as zahlungen_bp
    app.register_blueprint(zahlungen_bp, url_prefix="/zahlungen")

    from lsb_app.blueprints.tests import bp as tests_bp
    app.register_blueprint(tests_bp, url_prefix="/tests")


    # Logging konfigurieren
    _configure_logging(app)


    # CLI-Kommandos (z. B. flask dev-reset)
    register_cli(app)

    return app

def _configure_logging(app: Flask) -> None:
    log_dir = os.path.join(app.instance_path, "logs")
    os.makedirs(log_dir, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d %(message)s"
    )

    def _rot(path: str, level: int) -> RotatingFileHandler:
        h = RotatingFileHandler(
            os.path.join(log_dir, path),
            maxBytes=2 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        h.setLevel(level)
        h.setFormatter(formatter)
        return h

    debug_handler = _rot("debug.log", logging.DEBUG)   # DEBUG+
    app_handler   = _rot("app.log", logging.INFO)      # INFO+
    err_handler   = _rot("error.log", logging.ERROR)   # ERROR+

    root = logging.getLogger()
    for h in root.handlers[:]:
        root.removeHandler(h)

    # Root-Level: entscheidet, was überhaupt durchkommt
    root.setLevel(logging.DEBUG if app.debug else logging.INFO)

    # Handler immer
    root.addHandler(app_handler)
    root.addHandler(err_handler)

    # Debug-Handler nur in Development
    if app.debug:
        root.addHandler(debug_handler)

        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        console.setFormatter(formatter)
        root.addHandler(console)

    app.logger.handlers = []
    app.logger.propagate = True
    app.logger.setLevel(root.level)

    app.logger.info("Logging initialisiert (debug=%s).", app.debug)


