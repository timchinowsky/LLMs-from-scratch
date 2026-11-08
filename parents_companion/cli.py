import argparse
import os
from pathlib import Path
import sys

from .config import Settings
from .store import Store


def main():
    parser = argparse.ArgumentParser(description="Parents Companion synthetic development server")
    parser.add_argument("--config", help="Path to a TOML configuration file")
    parser.add_argument("command", choices=["serve", "backup"])
    parser.add_argument("--output", help="New backup destination; never overwrites a file")
    args = parser.parse_args()
    try:
        settings = Settings.load(args.config)
    except (ValueError, TypeError, OSError):
        parser.error("Invalid configuration; see config.example.toml (values omitted for privacy)")
    os.umask(0o077)
    if args.command == "backup":
        if not args.output:
            parser.error("backup requires --output")
        destination = Path(args.output)
        if destination.exists() or not (settings.data_dir / "companion.sqlite3").exists():
            parser.error("Backup needs an existing database and a new output path")
        store = Store(settings.data_dir / "companion.sqlite3")
        try:
            store.backup(destination)
        finally:
            store.close()
        print("Consistent backup written with a fresh database instance ID")
        return
    import uvicorn
    from .app import create_app

    print("Synthetic mode only. No microphone or paid API is used.", file=sys.stderr)
    print("Access tokens are in the protected data directory credentials.json.", file=sys.stderr)
    uvicorn.run(create_app(settings), host="127.0.0.1", port=8765, access_log=False)


if __name__ == "__main__":
    main()
