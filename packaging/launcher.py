"""PyInstaller entry point for the bundled Data Room Organizer launcher."""

from __future__ import annotations

from dataroom.bundled_launcher import main

if __name__ == "__main__":
    raise SystemExit(main())
