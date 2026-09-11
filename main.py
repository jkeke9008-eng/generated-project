# Project: SecretKeeper
# Description: A lightweight CLI tool to manage personal cheat‑sheets and knowledge snippets.
#              Store, retrieve, search and delete entries in a local JSON database.
#              No external dependencies beyond the Python standard library.

import json
import sys
import argparse
import textwrap
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional


class KnowledgeError(Exception):
    """Base exception for knowledge base operations."""


class EntryNotFoundError(KnowledgeError):
    """Raised when a requested entry does not exist."""


class DuplicateEntryError(KnowledgeError):
    """Raised when attempting to add an entry with an existing title."""


@dataclass
class Entry:
    """Represents a single knowledge snippet."""
    title: str
    content: str
    tags: List[str] = field(default_factory=list)

    def matches(self, query: str) -> bool:
        """Return True if query matches title, content or tags (case‑insensitive)."""
        lowered = query.lower()
        if lowered in self.title.lower():
            return True
        if lowered in self.content.lower():
            return True
        return any(lowered in tag.lower() for tag in self.tags)


class KnowledgeBase:
    """Handles persistent storage and retrieval of knowledge entries."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """
        Initialise the knowledge base.

        Parameters
        ----------
        db_path: Optional[Path]
            Path to the JSON database file. If None, defaults to
            ``~/.local/share/secret_knowledge.json``.
        """
        self.db_path = db_path or Path.home() / ".local" / "share" / "secret_knowledge.json"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: Dict[str, Entry] = {}
        self._load()

    def _load(self) -> None:
        """Load entries from the JSON file into memory."""
        if not self.db_path.is_file():
            self._entries = {}
            return
        try:
            with self.db_path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
            self._entries = {
                title: Entry(**data) for title, data in raw.items()
            }
        except (json.JSONDecodeError, OSError) as exc:
            raise KnowledgeError(f"Failed to read database: {exc}") from exc

    def _save(self) -> None:
        """Write the current entries to the JSON file."""
        try:
            serialisable = {title: asdict(entry) for title, entry in self._entries.items()}
            with self.db_path.open("w", encoding="utf-8") as f:
                json.dump(serialisable, f, ensure_ascii=False, indent=2)
        except OSError as exc:
            raise KnowledgeError(f"Failed to write database: {exc}") from exc

    def add(self, entry: Entry) -> None:
        """Add a new entry. Raises DuplicateEntryError if title exists."""
        if entry.title in self._entries:
            raise DuplicateEntryError(f"An entry with title '{entry.title}' already exists.")
        self._entries[entry.title] = entry
        self._save()

    def get(self, title: str) -> Entry:
        """Retrieve an entry by title. Raises EntryNotFoundError if missing."""
        try:
            return self._entries[title]
        except KeyError as exc:
            raise EntryNotFoundError(f"No entry found with title '{title}'.") from exc

    def remove(self, title: str) -> None:
        """Delete an entry. Raises EntryNotFoundError if missing."""
        if title not in self._entries:
            raise EntryNotFoundError(f"No entry found with title '{title}'.")
        del self._entries[title]
        self._save()

    def list_titles(self) -> List[str]:
        """Return a sorted list of all entry titles."""
        return sorted(self._entries.keys())

    def search(self, query: str) -> List[Entry]:
        """Return a list of entries matching the query."""
        return [e for e in self._entries.values() if e.matches(query)]


def _format_entry(entry: Entry) -> str:
    """Pretty‑print an entry for console output."""
    header = f"# {entry.title}"
    tags = f"Tags: {', '.join(entry.tags)}" if entry.tags else "Tags: (none)"
    body = textwrap.indent(entry.content.strip(), "  ")
    return f"{header}\n{tags}\n\n{body}"


def _parse_tags(tag_str: Optional[str]) -> List[str]:
    """Convert a comma‑separated tag string into a list."""
    if not tag_str:
        return []
    return [t.strip() for t in tag_str.split(",") if t.strip()]


def _cmd_add(args: argparse.Namespace, kb: KnowledgeBase) -> None:
    content = args.content
    if not content:
        # Read from stdin if no content argument provided
        print("Enter content (Ctrl‑D / Ctrl‑Z to finish):", file=sys.stderr)
        content = sys.stdin.read()
    entry = Entry(title=args.title, content=content, tags=_parse_tags(args.tags))
    try:
        kb.add(entry)
        print(f"Entry '{args.title}' added successfully.")
    except DuplicateEntryError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def _cmd_get(args: argparse.Namespace, kb: KnowledgeBase) -> None:
    try:
        entry = kb.get(args.title)
        print(_format_entry(entry))
    except EntryNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def _cmd_remove(args: argparse.Namespace, kb: KnowledgeBase) -> None:
    try:
        kb.remove(args.title)
        print(f"Entry '{args.title}' removed.")
    except EntryNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def _cmd_list(_: argparse.Namespace, kb: KnowledgeBase) -> None:
    titles = kb.list_titles()
    if not titles:
        print("No entries stored.")
        return
    for idx, title in enumerate(titles, 1):
        print(f"{idx}. {title}")


def _cmd_search(args: argparse.Namespace, kb: KnowledgeBase) -> None:
    results = kb.search(args.query)
    if not results:
        print(f"No entries match '{args.query}'.")
        return
    for entry in results:
        print(_format_entry(entry))
        print("-" * 40)


def build_parser() -> argparse.ArgumentParser:
    """Create the top‑level argument parser."""
    parser = argparse.ArgumentParser(
        prog="secretkeeper",
        description="Manage personal cheat‑sheets and knowledge snippets."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # add
    add_p = subparsers.add_parser("add", help="Add a new entry.")
    add_p.add_argument("title", help="Unique title for the entry.")
    add_p.add_argument("-c", "--content", help="Content of the entry. If omitted, read from stdin.")
    add_p.add_argument("-t", "--tags", help="Comma‑separated list of tags.", default="")

    # get
    get_p = subparsers.add_parser("get", help="Display an entry.")
    get_p.add_argument("title", help="Title of the entry to display.")

    # remove
    rm_p = subparsers.add_parser("remove", help="Delete an entry.")
    rm_p.add_argument("title", help="Title of the entry to delete.")

    # list
    subparsers.add_parser("list", help="List all entry titles.")

    # search
    search_p = subparsers.add_parser("search", help="Search entries by keyword.")
    search_p.add_argument("query", help="Search term (matches title, content, or tags).")

    return parser


def main(argv: Optional[List[str]] = None) -> None:
    """Entry point for the SecretKeeper CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    kb = KnowledgeBase()

    try:
        if args.command == "add":
            _cmd_add(args, kb)
        elif args.command == "get":
            _cmd_get(args, kb)
        elif args.command == "remove":
            _cmd_remove(args, kb)
        elif args.command == "list":
            _cmd_list(args, kb)
        elif args.command == "search":
            _cmd_search(args, kb)
        else:
            parser.error(f"Unknown command '{args.command}'.")
    except KnowledgeError as exc:
        print(f"Fatal error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()