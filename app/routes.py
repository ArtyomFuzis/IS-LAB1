from datetime import datetime, timedelta, timezone
from functools import wraps
from html import escape

import bcrypt
import jwt
from flask import Blueprint, current_app, g, jsonify, request
from jwt import InvalidTokenError

from app.extensions import db
from app.models import Data, User


api = Blueprint("api", __name__)


def escape_json(value):
    if isinstance(value, str):
        return escape(value, quote=True)
    if isinstance(value, list):
        return [escape_json(item) for item in value]
    if isinstance(value, dict):
        return {
            escape(str(key), quote=True): escape_json(item)
            for key, item in value.items()
        }
    return value


def serialize_data(item):
    return {
        "id": item.id,
        "name": escape(item.name, quote=True),
        "description": escape(item.description, quote=True),
        "extra_fields": escape_json(item.extra_fields),
    }


def require_auth(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        authorization = request.headers.get("Authorization", "")
        scheme, separator, token = authorization.partition(" ")

        if scheme.lower() != "bearer" or not separator or not token:
            return jsonify({"error": "authentication required"}), 401

        try:
            claims = jwt.decode(
                token,
                current_app.config["JWT_SECRET"],
                algorithms=["HS256"],
                issuer=current_app.config["JWT_ISSUER"],
                audience=current_app.config["JWT_AUDIENCE"],
                options={"require": ["exp", "iat", "sub"]},
            )
            g.user_id = int(claims["sub"])
        except (InvalidTokenError, TypeError, ValueError):
            return jsonify({"error": "invalid or expired token"}), 401

        return view(*args, **kwargs)

    return wrapped


@api.get("/health")
def health():
    return jsonify({"status": "ok"})


@api.post("/auth/login")
def login():
    if not request.is_json:
        return jsonify({"error": "content type must be application/json"}), 415

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "invalid request body"}), 400

    login_name = payload.get("login")
    password = payload.get("password")
    if (
        not isinstance(login_name, str)
        or not isinstance(password, str)
        or not login_name
        or not password
    ):
        return jsonify({"error": "login and password are required"}), 400

    user = db.session.scalar(db.select(User).where(User.username == login_name))
    password_matches = False

    if user:
        try:
            password_matches = bcrypt.checkpw(
                password.encode("utf-8"), user.password_hash.encode("utf-8")
            )
        except (TypeError, ValueError):
            password_matches = False

    if not password_matches:
        return jsonify({"error": "invalid login or password"}), 401

    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(user.id),
            "iat": now,
            "exp": now + timedelta(minutes=current_app.config["JWT_TTL_MINUTES"]),
            "iss": current_app.config["JWT_ISSUER"],
            "aud": current_app.config["JWT_AUDIENCE"],
        },
        current_app.config["JWT_SECRET"],
        algorithm="HS256",
    )

    return jsonify(
        {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": current_app.config["JWT_TTL_MINUTES"] * 60,
        }
    )


@api.get("/api/data")
@require_auth
def get_data():
    items = db.session.scalars(db.select(Data).order_by(Data.id)).all()
    return jsonify([serialize_data(item) for item in items])


@api.post("/api/data")
@require_auth
def create_data():
    if not request.is_json:
        return jsonify({"error": "content type must be application/json"}), 415

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "invalid request body"}), 400

    allowed_fields = {"name", "description", "extra_fields"}
    if set(payload) - allowed_fields:
        return jsonify({"error": "unknown fields"}), 400

    name = payload.get("name")
    description = payload.get("description")
    extra_fields = payload.get("extra_fields", {})

    if not isinstance(name, str) or not name.strip() or len(name) > 255:
        return (
            jsonify(
                {"error": "name must be a non-empty string of at most 255 characters"}
            ),
            400,
        )
    if not isinstance(description, str):
        return jsonify({"error": "description must be a string"}), 400

    item = Data(name=name, description=description, extra_fields=extra_fields)
    db.session.add(item)
    db.session.commit()

    return jsonify(serialize_data(item)), 201
