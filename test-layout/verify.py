"""Read PE tables without loading DLL code or changing the active keyboard."""
from pathlib import Path
import hashlib
import json
import struct

HERE = Path(__file__).resolve().parent


class PE:
    def __init__(self, path, pointer_size):
        self.path = path
        self.b = path.read_bytes()
        self.ptrsize = pointer_size
        pe = self.u("I", 0x3c)
        assert self.b[pe:pe+4] == b"PE\0\0"
        self.machine = self.u("H", pe+4)
        opt = pe+24
        is64 = self.u("H", opt) == 0x20b
        self.base = self.u("Q" if is64 else "I", opt+(24 if is64 else 28))
        self.entry = self.u("I", opt+16)
        self.subsystem = self.u("H", opt+68)
        dd = opt+(112 if is64 else 96)
        self.imports = self.u("I", dd+8)
        self.relocs = self.u("I", dd+40)
        section = opt+self.u("H", pe+20)
        self.sections = []
        for i in range(self.u("H", pe+6)):
            o = section+i*40
            self.sections.append((self.u("I", o+12), self.u("I", o+16), self.u("I", o+20)))
        export = self.offset(self.u("I", dd))
        names = self.u("I", export+32)
        ordinals = self.u("I", export+36)
        functions = self.u("I", export+28)
        found = []
        for i in range(self.u("I", export+24)):
            n = self.offset(self.u("I", self.offset(names)+i*4))
            name = self.b[n:self.b.index(0, n)].decode("ascii")
            if name == "KbdLayerDescriptor":
                ordinal = self.u("H", self.offset(ordinals)+i*2)
                found.append(self.u("I", self.offset(functions)+ordinal*4))
        assert len(found) == 1, "Missing/ambiguous descriptor export"
        rva = found[0]
        o = self.offset(rva)
        if is64:
            assert self.b[o:o+3] == b"\x48\x8d\x05" and self.b[o+7] == 0xc3
            table = rva+7+self.u("i", o+3)
        else:
            code = self.b[o:o+16]
            # WOW64 returns the __ptr64 result in EDX:EAX.
            if code[:2] == b"\x33\xd2":
                o += 2
            assert self.b[o] == 0xb8, f"Unexpected descriptor: {code.hex()}"
            table = self.u("I", o+1)-self.base
        self.table_rva = table
        self.t = self.offset(table)

    def u(self, fmt, offset):
        return struct.unpack_from("<"+fmt, self.b, offset)[0]

    def offset(self, rva):
        for address, size, offset in self.sections:
            if address <= rva < address+size:
                return offset+rva-address
        raise ValueError(f"Unmapped RVA {rva:x}")

    def pointer(self, offset):
        return self.u("Q" if self.ptrsize == 8 else "I", offset)

    def pointee(self, offset):
        return self.offset(self.pointer(offset)-self.base)

    def records(self, offset, size, sentinel_size=1):
        result = []
        for i in range(4096):
            row = self.b[offset+i*size:offset+(i+1)*size]
            assert len(row) == size
            if not any(row[:sentinel_size]):
                return result
            result.append(row.hex())
        raise ValueError("Missing table terminator")

    def mappings(self):
        p = self.ptrsize
        t = self.t
        modifiers = self.pointee(t)
        maxbits = self.u("H", modifiers+p)
        assert maxbits < 256
        char_desc = self.pointee(t+p)
        chars = []
        for i in range(32):
            d = char_desc+i*p*2
            if self.pointer(d) == 0:
                break
            columns, row_size = self.b[d+p:d+p+2]
            chars.append((columns, row_size, self.records(self.pointee(d), row_size)))
        else:
            raise ValueError("Missing character descriptor terminator")
        scans = self.pointee(t+6*p)
        count = self.b[t+7*p]
        return {
            "modifier_keys": self.records(self.pointee(modifiers), 2),
            "modifier_states": self.b[modifiers+p+2:modifiers+p+3+maxbits].hex(),
            "characters": chars,
            "deadkeys": self.records(self.pointee(t+2*p), 8, 4),
            "scancodes": list(struct.unpack_from("<"+"H"*count, self.b, scans)),
            "e0": self.records(self.pointee(t+8*p), 4),
            "e1": self.records(self.pointee(t+9*p), 4),
            "flags": self.u("I", t+10*p),
            "ligature_counts": list(self.b[t+10*p+4:t+10*p+6]),
            "ligature_pointer": self.pointer(t+(88 if p == 8 else 48)),
        }

    def metadata(self):
        offset = 96 if self.ptrsize == 8 else 52
        return self.u("I", self.t+offset), self.u("I", self.t+offset+4)


def main():
    hashes = json.loads((HERE/"original-sha256.json").read_text())
    for name, digest in hashes.items():
        assert hashlib.sha256((HERE.parent/name).read_bytes()).hexdigest() == digest, name
    print("Original sources, KLC and DLL: SHA-256 unchanged")
    original = PE(HERE.parent/"CMKUKB.dll", 8)
    oldmap = original.mappings()
    print(f"Original DLL: table RVA=0x{original.table_rva:x}; bytes at type/subtype offsets={original.metadata()}")
    binaries = []
    for arch, ptr, machine in (("amd64", 8, 0x8664), ("wow64", 8, 0x14c), ("x86", 4, 0x14c)):
        pe = PE(HERE/"out"/arch/"CMKTST.dll", ptr)
        assert pe.machine == machine and pe.entry == 0 and pe.imports == 0
        assert pe.subsystem == 1 and pe.relocs != 0
        assert pe.metadata() == (4, 0)
        current = pe.mappings()
        assert current["scancodes"][0x3a] == 8
        assert current["scancodes"][0x0e] == 8
        if binaries:
            assert current == binaries[0], "Architecture mapping mismatch"
        binaries.append(current)
        print(f"{arch}: correct PE architecture; native/no-entry/no-imports; type=4 subtype=0; Caps/Backspace=VK_BACK")
    current = binaries[0]
    # Compare every generated character and dead-key table against the supplied
    # installed DLL. Report differences rather than assuming import was lossless.
    for key in oldmap:
        if key == "scancodes":
            differences = [(i, a, b) for i, (a, b) in enumerate(zip(oldmap[key], current[key])) if a != b]
            assert len(oldmap[key]) == len(current[key])
            assert all(i == 0x3a and b == 8 for i, a, b in differences), differences
            print(f"Original DLL scancodes: preserved (allowed Caps change: {differences})")
        else:
            assert oldmap[key] == current[key], f"Original DLL differs in {key}"
            print(f"Original DLL {key}: identical")
    print("PASS: binary mappings preserved across all three builds")


if __name__ == "__main__":
    main()
