import sys
import argparse
from backend.app.core.database import SessionLocal
from backend.app.services.bootstrap_service import ensure_super_admin_exists
from backend.app.core.logging import logger


def main():
    parser = argparse.ArgumentParser(description="Bootstrap Quizverse Initial Super Administrator")
    parser.add_argument("--email", type=str, help="Super admin email address")
    parser.add_argument("--password", type=str, help="Super admin password")
    parser.add_argument("--name", type=str, help="Super admin full name")
    args = parser.parse_args()

    if not SessionLocal:
        print("ERROR: Database connection not configured. Check DATABASE_URL in environment.")
        sys.exit(1)

    print("Connecting to database...")
    with SessionLocal() as db:
        try:
            admin = ensure_super_admin_exists(
                db=db,
                email=args.email,
                password=args.password,
                full_name=args.name,
            )
            print(f"SUCCESS: Super Administrator provisioned:")
            print(f"  ID: {admin.id}")
            print(f"  Email: {admin.email}")
            print(f"  Super Admin: {admin.is_super_admin}")
            print(f"  Status: {admin.status}")
        except Exception as e:
            print(f"ERROR: Failed to bootstrap super admin: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
