"""Command-line interface for ISSN data tools.

Usage:
    python -m issn_unifier download      # Download data from sources
    python -m issn_unifier unify         # Unify downloaded data
    python -m issn_unifier fetch-sibils  # Extract journal fields from SIBiLS
    python -m issn_unifier --help        # Show help
"""

import sys


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        print("Commands:")
        print("  download      Download ISSN data from multiple sources")
        print("  unify         Unify downloaded data into a single dataset")
        print("  fetch-sibils  Extract journal fields from SIBiLS Elasticsearch")
        print()
        print("Run 'python -m issn_unifier <command> --help' for command-specific help.")
        return 0

    command = sys.argv[1]
    # Remove the command from argv so subcommand parsers work correctly
    sys.argv = [f"issn_unifier {command}"] + sys.argv[2:]

    if command == "download":
        from .download import main as download_main

        return download_main() or 0
    elif command == "unify":
        from .unify import main as unify_main

        return unify_main()
    elif command == "fetch-sibils":
        from .sibils_fetch import main as fetch_sibils_main

        return fetch_sibils_main()
    else:
        print(f"Unknown command: {command}")
        print("Run 'python -m issn_unifier --help' for available commands.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
