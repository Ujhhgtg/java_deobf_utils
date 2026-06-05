# java_deobf_utils

Tools for deobfuscating WAuxiliary (WeChat Xposed module) Java source code
decompiled by JADX.

## Scripts

### `decrypt_encrypted_strings.py`

Reverses the `MagicFactory.get(long, String[])` obfuscation pattern. WAuxiliary
replaces every string literal with a call to this static method, which in turn
calls into `libwauxv-core.so` via JNI.

**Version B** (pure Python): Implements the original Feistel-like `ab()` mixing
function with hardcoded constants. Works on the `old/` directory without any
external dependencies.

**Version C** (REST API): The native library was rewritten; the algorithm can no
longer be replicated in Python. Instead, the script calls a helper Android app
(WASLDH) that bundles the real native lib and exposes it as a local HTTP server.

```
# single — decrypt one value
uv run decrypt_encrypted_strings.py single 4928230575635957130 \
  --api-url http://192.168.1.100:8080

# bulk — decrypt all MagicFactory.get calls in a directory, replace in-place
uv run decrypt_encrypted_strings.py bulk \
  --api-url http://192.168.1.100:8080 \
  --batch-size 200 \
  p000/ p000/AbstractC3590Ujhhgtgfeyxiexzf.java f11170Ujhhgtgfeyxiexzf

# preflight — collect all unique longs, decrypt in batch, save as lookup file
uv run decrypt_encrypted_strings.py preflight \
  --api-url http://192.168.1.100:8080 \
  --batch-size 200 \
  --output lookup.txt \
  p000/

# Then reuse the lookup for offline bulk deobfuscation:
uv run decrypt_encrypted_strings.py bulk --lookup lookup.txt \
  <directory> <crypt_path> <array_name>
```

The `--batch-size` flag limits how many keys are sent in a single `/decryptBatch`
request, useful if the URL length exceeds server limits.

Version auto-detection: if the string array rows are all 8191 characters wide,
it's version C (API mode); otherwise it's version B (pure Python).

---

### `escape_java.py`

JADX sometimes outputs the massive `String[]` declaration line with raw UTF-8
bytes instead of Java `\uxxxx` escape sequences. `javac` rejects raw non-ASCII
in source files unless the encoding is specified, so this script finds the one
incredibly long line in a directory of `.java` files and re-escapes every
non-ASCII character into proper Java `\uxxxx` (or surrogate-pair) form.

```
uv run escape_java.py <directory>
```

Output: prints the matched file path and variable name to stdout, e.g.:

```
p000/AbstractC3590Ujhhgtgfeyxiexzf.java;f11170Ujhhgtgfeyxiexzf
```

The file is rewritten in-place. The threshold for "incredibly long" defaults to
100,000 characters and can be adjusted via the `LENGTH_THRESHOLD` constant at
the top of the script.
