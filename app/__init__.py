import os

from flask import Flask
from sqlalchemy import URL

from app.extensions import db


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        JWT_SECRET=os.environ.get("JWT_SECRET", ""),
        JWT_ISSUER="secure-data-api",
        JWT_AUDIENCE="secure-data-api",
        JWT_TTL_MINUTES=15,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if test_config:
        app.config.update(test_config)

    if len(app.config["JWT_SECRET"]) < 32:
        raise RuntimeError("JWT_SECRET must contain at least 32 characters")

    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        app.config["SQLALCHEMY_DATABASE_URI"] = URL.create(
            "postgresql+psycopg",
            username=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            host=os.environ.get("DB_HOST", "db"),
            port=int(os.environ.get("DB_PORT", "5432")),
            database=os.environ["DB_NAME"],
        )

    db.init_app(app)

    from app.routes import api

    app.register_blueprint(api)

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'"
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    return app
