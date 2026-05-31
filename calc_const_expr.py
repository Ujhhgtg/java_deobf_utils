#!/usr/bin/env -S uv run --script

# /// script
# dependencies = []
# ///

import argparse
import os
import re

PATTERN = (
    r"\(\(long\)\s*([-]?\d+)[lL]?\)\s*\^\s*(?:\(\s*([-]?\d+)[lL]?\s*\)|([-]?\d+)[lL]?)"
)


def process_content(content):
    def replacer(match):
        try:
            val1 = int(match.group(1))
            # Group 2 is the value if parens were present, Group 3 if bare
            val2_str = match.group(2) if match.group(2) is not None else match.group(3)
            val2 = int(val2_str)

            result = val1 ^ val2
            return f"{result}L"
        except (ValueError, IndexError, TypeError):
            return match.group(0)

    return re.sub(PATTERN, replacer, content)


def process_file(file_path):
    """Reads, processes, and overwrites a single file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        new_content = process_content(content)

        if new_content != content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Updated: {file_path}")
        else:
            print(f"No changes: {file_path}")
    except Exception as e:
        print(f"Error processing {file_path}: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Inline constant long XOR expressions in Java files."
    )

    # Mutually exclusive group: either a directory or a single file
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("directory", nargs="?", help="Directory to search recursively")
    group.add_argument("--single", help="Specific Java file to process")

    args = parser.parse_args()

    if args.single:
        if args.single.endswith(".java"):
            process_file(args.single)
        else:
            print("Error: Target must be a .java file.")
    else:
        for root, _, files in os.walk(args.directory):
            for file in files:
                if file.endswith(".java"):
                    process_file(os.path.join(root, file))


if __name__ == "__main__":
    main()
