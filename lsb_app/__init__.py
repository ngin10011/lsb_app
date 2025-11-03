# lsb_app/__init__.py
import os
from flask import Flask
from dotenv import load_dotenv
from lsb_app.extensions import db, csrf

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
    app.config["COMPANY_ADDRESS"] = os.getenv("COMPANY_ADDRESS", "")
    app.config["COMPANY_PHONE"] = os.getenv("COMPANY_PHONE", "")
    app.config["COMPANY_EMAIL"] = os.getenv("COMPANY_EMAIL", "")
    app.config["BANK_IBAN"] = os.getenv("BANK_IBAN", "")
    app.config["BANK_BIC"] = os.getenv("BANK_BIC", "")
    app.config["TAX_NUMBER"] = os.getenv("TAX_NUMBER", "")

    # Für Jinja verfügbar machen: {{ config.BANK_IBAN }} usw.
    @app.context_processor
    def inject_config():
        return dict(config=app.config)

    # Extensions
    db.init_app(app)
    csrf.init_app(app)

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

    from lsb_app.blueprints.invoices import bp as invoices_bp
    app.register_blueprint(invoices_bp, url_prefix="/invoices")





    @app.cli.command("init-db")
    def init_db_command():
        from lsb_app import models  # Models registrieren
        db.create_all()
        print("Datenbank initialisiert.")

    return app
