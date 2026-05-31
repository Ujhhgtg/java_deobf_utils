#!/usr/bin/env -S uv run --script

import os
import shutil
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
CODING_DIR = HOME / "coding"
UTILS_DIR = CODING_DIR / "java_deobf_utils"
STATE_FILE = ".deobf_state"


def state_path(proj_dir):
    return proj_dir / STATE_FILE


def save_state(proj_dir, step, file_path=None, array_name=None):
    with open(state_path(proj_dir), "w") as f:
        f.write(f"step={step}\n")
        if file_path:
            f.write(f"file_path={file_path}\n")
        if array_name:
            f.write(f"array_name={array_name}\n")


def load_state(proj_dir):
    data = {}
    sp = state_path(proj_dir)
    if sp.exists():
        with open(sp) as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    data[k] = v
    return data


def run_live(cmd, **kwargs):
    """Run a command with stdout/stderr flowing through to the script's terminal."""
    print(f"+ {' '.join(str(c) for c in cmd)}")
    check = kwargs.pop("check", True)
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}", file=sys.stderr)
        if check:
            sys.exit(1)
    return result


def main():
    # --- Inputs ---
    apk_path = input("Enter APK path: ").strip()
    proj_name = input("Enter deobfuscate project name: ").strip()

    apk_file = Path(apk_path).resolve()
    if not apk_file.is_file():
        print(f"Error: APK not found at {apk_file}", file=sys.stderr)
        sys.exit(1)

    proj_dir = CODING_DIR / proj_name

    # --- Fresh or resume? ---
    mode = (
        input("Start from fresh or resume from a step? (fresh/resume): ")
        .strip()
        .lower()
    )
    while mode not in ("fresh", "resume"):
        mode = input("Please enter 'fresh' or 'resume': ").strip().lower()

    if mode == "fresh":
        if proj_dir.exists():
            print(
                f"Error: project directory {proj_dir} already exists. Use resume mode.",
                file=sys.stderr,
            )
            sys.exit(1)
        proj_dir.mkdir(parents=True)
        start_step = 1
    else:
        if not proj_dir.exists():
            print(
                f"Error: project directory {proj_dir} does not exist. Use fresh mode.",
                file=sys.stderr,
            )
            sys.exit(1)
        step_str = input("Enter step number to resume from (1-4): ").strip()
        try:
            start_step = int(step_str)
        except ValueError:
            print("Invalid step number.", file=sys.stderr)
            sys.exit(1)
        if start_step < 1 or start_step > 4:
            print("Step must be between 1 and 4.", file=sys.stderr)
            sys.exit(1)

    os.chdir(proj_dir)

    # Load saved state (if resuming)
    state = load_state(proj_dir)
    file_path = state.get("file_path")
    array_name = state.get("array_name")

    # ===== Step 1: Project setup =====
    if start_step <= 1:
        print("\n--- Step 1: Setting up project directory ---")
        target_apk = proj_dir / "app.apk"
        if not target_apk.exists():
            shutil.copy(str(apk_file), target_apk)
        save_state(proj_dir, 1)

    # ===== Step 2: Run jadx =====
    if start_step <= 2:
        print("\n--- Step 2: Decompiling with jadx ---")
        run_live(
            [
                "jadx",
                "--deobf",
                "--deobf-min",
                "1",
                "--deobf-max",
                "65535",
                "--rename-flags",
                "all",
                "--use-source-name-as-class-name-alias",
                "always",
                "--show-bad-code",
                "-e",
                "app.apk",
            ],
            check=False,
        )
        save_state(proj_dir, 2)

    # ===== Step 3: Symlinks + escape_java =====
    src_main_dir = proj_dir / "app" / "app" / "src" / "main"

    if start_step <= 3:
        print("\n--- Step 3: Symlinks and escape_java ---")
        if not src_main_dir.exists():
            print(f"Error: expected {src_main_dir} from jadx output", file=sys.stderr)
            sys.exit(1)

        os.chdir(src_main_dir)

        # Create symlinks to utils scripts
        for f in ("decrypt_encrypted_strings.py", "escape_java.py"):
            link_path = src_main_dir / f
            if not link_path.exists():
                link_path.symlink_to(UTILS_DIR / f)

        # Run escape_java — capture stdout for parsing, let stderr flow
        print("+ uv run --script ./escape_java.py ./java/")
        result = subprocess.run(
            ["uv", "run", "--script", "./escape_java.py", "./java/"],
            capture_output=True,
            text=True,
        )
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        if result.returncode != 0:
            sys.exit(1)

        output = result.stdout.strip()
        if not output or ";" not in output:
            print(f"Error: unexpected escape_java output: {output!r}", file=sys.stderr)
            sys.exit(1)

        file_path, array_name = output.split(";", 1)
        print(f"Found: {file_path};{array_name}")

        save_state(proj_dir, 3, file_path=file_path, array_name=array_name)
    else:
        # Ensure we're in the right directory for subsequent steps
        os.chdir(src_main_dir)

    # ===== Step 4: Decrypt strings =====
    if start_step <= 4:
        print("\n--- Step 4: Decrypting strings ---")
        if not file_path or not array_name:
            print(
                "Error: file_path or array_name not available from step 3",
                file=sys.stderr,
            )
            sys.exit(1)

        run_live(
            [
                "uv",
                "run",
                "--script",
                "./decrypt_encrypted_strings.py",
                "bulk",
                "./java/",
                file_path,
                "MagicFactory.get",
                array_name,
            ]
        )
        save_state(proj_dir, 4)

    # ===== Summary =====
    print("\n=== Summary ===")
    print(f"  Project:      {proj_name}")
    print(f"  Location:     {proj_dir}")
    print(f"  File:         {file_path}")
    print(f"  Array name:   {array_name}")
    print("Done.")


if __name__ == "__main__":
    main()
