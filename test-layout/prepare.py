"""Copy and minimally patch the supplied sources; never edit the originals."""
from pathlib import Path
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
NAME = "CMKTST"
DESCRIPTION = "Colemak UK BKSP - Type4 Test"


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError(f"Expected exactly one occurrence of {old!r}")
    return text.replace(old, new, 1)


def prepare():
    hashes = {}
    patches = []
    for ext in ("C", "H", "RC", "DEF"):
        source = ROOT / f"BKSPUK.{ext}"
        raw = source.read_bytes()
        hashes[source.name] = hashlib.sha256(raw).hexdigest()
        encoding = "utf-16le" if ext == "RC" else "ascii"
        old = raw.decode(encoding)
        new = old.replace("BKSPUK", NAME).replace("bkspuk", NAME.lower())
        if ext == "C":
            new = replace_once(new, '#include "CMKTST.h"',
                               '#include "CMKTST.h"\r\n#include "layout-abi.h"')
            new = replace_once(new, '0x3a,    L"Caps Lock"', '0x3a,    L"Backspace"')
            new = replace_once(new, "    0,\r\n    0,\r\n    NULL\r\n};",
                               "    0,       // nLgMax\r\n"
                               "    0,       // cbLgEntry\r\n"
                               "    NULL,    // pLigature\r\n"
                               "    4,       // dwType: enhanced 101/102-key keyboard\r\n"
                               "    0        // dwSubType\r\n};")
        elif ext == "H":
            new += ("\r\n// Physical Caps Lock (scan code 0x3A) is Backspace.\r\n"
                    "#undef T3A\r\n#define T3A _EQ(BACK)\r\n")
        elif ext == "RC":
            new = new.replace("Colemak UK BKSP - Custom", DESCRIPTION)
            new = replace_once(new, '"OriginalFilename","cmktst\\0"',
                               '"OriginalFilename","cmktst.dll\\0"')
        (HERE / f"{NAME}.{ext}").write_bytes(new.encode(encoding))
        patches.extend(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                       fromfile=source.name, tofile=f"test-layout/{NAME}.{ext}"))

    source = ROOT / "Colemak UK BKSP - Custom.klc"
    raw = source.read_bytes()
    hashes[source.name] = hashlib.sha256(raw).hexdigest()
    old = raw.decode("utf-16")
    new = replace_once(old, 'KBD\tBKSPUK\t"Colemak UK BKSP - Custom"',
                       f'KBD\t{NAME}\t"{DESCRIPTION}"')
    new = new.replace("Colemak UK BKSP - Custom", DESCRIPTION)
    # KLC remains an archive of the character mappings. The C/H patches are
    # authoritative: rebuilding this KLC with kbdutool would lose those patches.
    (HERE / f"{NAME}.klc").write_bytes(new.encode("utf-16"))
    patches.extend(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                   fromfile=source.name, tofile=f"test-layout/{NAME}.klc"))
    hashes["CMKUKB.dll"] = hashlib.sha256((ROOT / "CMKUKB.dll").read_bytes()).hexdigest()
    (HERE / "original-sha256.json").write_text(json.dumps(hashes, indent=2) + "\n")
    (HERE / "source-changes.diff").write_text("".join(patches), encoding="utf-8")
    print("Prepared CMKTST sources. Original files untouched.")


if __name__ == "__main__":
    prepare()
