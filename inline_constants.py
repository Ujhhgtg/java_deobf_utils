#!/usr/bin/env -S uv run --script

# /// script
# dependencies = []
# ///

import argparse
import re
from pathlib import Path

# Group 1: Specifically matches a cast like (long) or (int), excluding outer expression parens.
# Group 2: The Class FQN
# Group 3: The Field Name
FIELD_ACCESS_RE = re.compile(
    r"(\(\s*\w+\s*\)\s*)?([a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*\.[a-zA-Z][a-zA-Z0-9_]*)\.([a-zA-Z0-9_]+)"
)


class ConstantResolver:
    def __init__(self, root_dir):
        self.root_dir = Path(root_dir)
        self.cache = {}

    def get_constant_value(self, class_fqn, field_name):
        key = f"{class_fqn}.{field_name}"
        if key in self.cache:
            return self.cache[key]

        rel_path = class_fqn.replace(".", "/") + ".java"
        source_path = self.root_dir / rel_path

        if not source_path.exists():
            return None

        content = source_path.read_text(encoding="utf-8")
        # Matches the literal value assigned to a static field
        val_pattern = rf"static\s+(?:\w+\s+)?{field_name}\s*=\s*([^;]+);"
        match = re.search(val_pattern, content)

        if match:
            value = match.group(1).strip()
            self.cache[key] = value
            return value
        return None

    def process_file(self, file_path):
        content = file_path.read_text(encoding="utf-8")

        def replace_match(match):
            cast_part = match.group(1)
            class_fqn = match.group(2)
            field_name = match.group(3)

            value = self.get_constant_value(class_fqn, field_name)

            if value is not None:
                if cast_part:
                    # Preserve cast and wrap in additional brackets as requested
                    # cast_part.strip() ensures we don't have trailing spaces inside our new parens
                    return f"{cast_part.strip()} {value}"
                return value

            return match.group(0)

        new_content = FIELD_ACCESS_RE.sub(replace_match, content)

        if new_content != content:
            file_path.write_text(new_content, encoding="utf-8")
            print(f"Updated: {file_path}")


def main():
    parser = argparse.ArgumentParser(description="Inline Java static constants.")
    parser.add_argument("target", help="Directory or file to process")
    parser.add_argument("root_dir", help="Root source directory for FQN lookup")
    parser.add_argument(
        "--single", action="store_true", help="Treat target as a single file"
    )

    args = parser.parse_args()
    resolver = ConstantResolver(args.root_dir)

    if args.single:
        files = [Path(args.target)]
    else:
        files = Path(args.target).rglob("*.java")

    for java_file in files:
        if java_file.is_file():
            resolver.process_file(java_file)


if __name__ == "__main__":
    main()
