"""Create a local application user for the login API."""

import argparse
from getpass import getpass

from app.auth import hash_password
from app.database import Base, SessionLocal, engine
from app.models import User


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a user for the AI/LLM Platform API")
    parser.add_argument("--username", required=True)
    parser.add_argument("--role", choices=("user", "admin", "read_only"), default="user")
    args = parser.parse_args()

    password = getpass("Password (minimum 8 characters): ")
    if len(password) < 8:
        parser.error("password must contain at least 8 characters")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        parser.error("passwords do not match")

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.query(User).filter(User.username == args.username).first():
            parser.error(f"user '{args.username}' already exists")
        db.add(User(username=args.username, password_hash=hash_password(password), role=args.role))
        db.commit()

    print(f"Created {args.role} user '{args.username}'.")


if __name__ == "__main__":
    main()
