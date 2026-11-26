"""Install collection overrides into a compatible checkout; no hardware is opened."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lerobot_checkout", type=Path)
    parser.add_argument("--check", action="store_true", help="Validate without changing files")
    args = parser.parse_args()
    package = Path(__file__).resolve().parent
    target = args.lerobot_checkout.resolve()
    manifest = json.loads((package / "manifest.json").read_text())
    pending = []
    for name, expected in manifest["files"].items():
        source = package / "overrides" / name
        destination = target / name
        if digest(source) != expected["modified_sha256"]:
            raise SystemExit(f"Package checksum mismatch: {name}")
        if not destination.is_file():
            raise SystemExit(f"Missing target: {destination}")
        current = digest(destination)
        if current == expected["modified_sha256"]:
            print(f"Already installed: {name}")
        elif current == expected["base_sha256"]:
            pending.append((source, destination, name))
        else:
            raise SystemExit(f"Refusing to overwrite unexpected local changes: {destination}")
    backup = target / ".eight-streams-backup"
    for _, _, name in pending:
        if (backup / name).exists():
            raise SystemExit(f"Backup already exists; preserve/review it before installing: {backup / name}")
    if args.check:
        print(f"Compatible: {len(pending)} files would be installed. No changes made.")
        return
    for source, destination, name in pending:
        saved = backup / name
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(destination, saved)
        shutil.copy2(source, destination)
        print(f"Installed: {name}")
    print("Complete. Original files, if changed, are in " + str(backup))


if __name__ == "__main__":
    main()
