#!/usr/bin/env python3
"""
Alembic migration runner script for CI/CD and deployment hooks.
"""
import os
import sys
from alembic import command
from alembic.config import Config

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


def run_migrations():
    ini_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend", "alembic.ini"))
    alembic_cfg = Config(ini_path)
    print(f"Running Alembic migrations with config: {ini_path}")
    try:
        command.upgrade(alembic_cfg, "head")
        print("Alembic migrations applied successfully.")
    except Exception as e:
        print(f"Migration execution note: {e}")


if __name__ == "__main__":
    run_migrations()
