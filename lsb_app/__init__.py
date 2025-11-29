# lsb_app/__init__.py
import os
from flask import Flask
from flask_migrate import Migrate
from dotenv import load_dotenv
from lsb_app.extensions import db, csrf
import logging
from logging.handlers import RotatingFileHandler

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

    log_dir = os.path.join(app.instance_path, "logs")
    os.makedirs(log_dir, exist_ok=True)

    # Logging-Verzeichnis
    log_dir = os.path.join(app.instance_path, "logs")
    os.makedirs(log_dir, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d %(message)s"
    )

    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    app.logger.addHandler(file_handler)

    error_handler = RotatingFileHandler(
        os.path.join(log_dir, "error.log"),
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    app.logger.addHandler(error_handler)

    if app.debug:
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        console.setFormatter(formatter)
        app.logger.addHandler(console)

    app.logger.setLevel(logging.INFO)
    app.logger.info("LSB-App initialisiert. Logging aktiv.")

    return app
