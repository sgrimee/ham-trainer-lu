"""Manage course learner accounts from the command line (specs/LEARN.md §6.1).

    python -m app.learners list
    python -m app.learners add "Léa"
    python -m app.learners delete "Léa"

Uses the same database as the app (`ATTEMPTS_DB`, default var/attempts.db), so
it works inside the container: `docker exec <container> python -m app.learners
add "…"`. It needs no admin password -- shell access is its own protection.
Deleting removes the learner's progress too, with no confirmation prompt.
"""
from __future__ import annotations

import argparse
import sys

from .store import AccountExists, Store


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.learners", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="list accounts")
    add = sub.add_parser("add", help="add an account")
    add.add_argument("name", help="display name, as shown in the /learn dropdown")
    delete = sub.add_parser("delete", help="delete an account and all its progress")
    delete.add_argument("name", help="display name of the account to delete")
    args = parser.parse_args(argv)

    store = Store()
    if args.command == "list":
        for a in store.accounts():
            print(f"{a['display_name']}\t{a['id']}\t{a['created_at']}")
        return 0
    if args.command == "add":
        try:
            store.create_account(args.name)
        except AccountExists as e:
            print(f"already exists: {e}", file=sys.stderr)
            return 1
        except ValueError as e:
            print(f"invalid name: {e}", file=sys.stderr)
            return 1
        print(f"added: {' '.join(args.name.split())}")
        return 0
    account = store.account_by_name(args.name)
    if account is None:
        print(f"no such learner: {args.name}", file=sys.stderr)
        return 1
    store.delete_account(account["id"])
    print(f"deleted: {account['display_name']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
