# lsb_app/__init__.py
import os
from flask import Flask
from dotenv import load_dotenv
from lsb_app.extensions import db, csrf

def create_app():
    load_dotenv()

    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    # Konfiguration
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-key")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(app.instance_path, "site.db")
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

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





    @app.cli.command("init-db")
    def init_db_command():
        from lsb_app import models  # Models registrieren
        db.create_all()
        print("Datenbank initialisiert.")

    return app
