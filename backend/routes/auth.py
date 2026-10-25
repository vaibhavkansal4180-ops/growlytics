from functools import wraps
from flask import Blueprint, request, jsonify, session
from backend.extensions import db
from backend.models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            # Check Bearer token or authorization header if passed
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                # In this prototype, session ID or user ID can be verified
                try:
                    user_id = int(token)
                except ValueError:
                    pass

        if not user_id:
            return jsonify({
                "success": False,
                "error": "Authentication required. Please log in to access this feature."
            }), 401

        user = User.query.get(user_id)
        if not user:
            session.pop("user_id", None)
            return jsonify({"success": False, "error": "Invalid session. Please log in again."}), 401

        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate user with email and hashed password verification."""
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()

    if not email or not password:
        return jsonify({"success": False, "error": "Email and password are required."}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"success": False, "error": "Invalid credentials. Please verify email and password."}), 401

    session["user_id"] = user.id
    session["user_name"] = user.name
    session["user_role"] = user.role

    return jsonify({
        "success": True,
        "message": f"Welcome back, {user.name}!",
        "user": user.to_dict()
    })


@auth_bp.route("/register", methods=["POST"])
def register():
    """Register a new team member with secure password hashing."""
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()
    role = data.get("role", "Store Manager").strip()

    if not name or not email or not password:
        return jsonify({"success": False, "error": "Name, email, and password are required."}), 400

    if len(password) < 6:
        return jsonify({"success": False, "error": "Password must be at least 6 characters long."}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"success": False, "error": "An account with this email address already exists."}), 409

    user = User(name=name, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    session["user_id"] = user.id
    session["user_name"] = user.name
    session["user_role"] = user.role

    return jsonify({
        "success": True,
        "message": "Account created successfully.",
        "user": user.to_dict()
    }), 201


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Clear session data."""
    session.clear()
    return jsonify({"success": True, "message": "Successfully logged out."})


@auth_bp.route("/me", methods=["GET"])
def get_current_user():
    """Return currently authenticated user profile or unauthenticated state."""
    user_id = session.get("user_id")
    if user_id:
        user = User.query.get(user_id)
        if user:
            return jsonify({
                "authenticated": True,
                "user": user.to_dict()
            })
    return jsonify({
        "authenticated": False,
        "user": None
    })
