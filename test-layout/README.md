# Colemak UK Backspace: isolated Windows 11 type-4 test build

The test layout is **CMKTST.dll**, displayed as **Colemak UK BKSP - Type4 Test**.
It is separate from the installed `CMKUKB.dll` (registry key `A0000809`, Layout Id
`00C0`) and from the existing `CMKUK.dll` (`A0010809`, Layout Id `00C1`).
Nothing has been installed, activated, or changed in the Windows registry by this work.

**Deployment target: Windows 11 x64.** The compiler version macros are
`_WIN32_WINNT=0x0A00`, `WINVER=0x0A00`, `NTDDI_VERSION=0x0A000000`, the
Windows 10/11 API baseline. Windows 11 shares NT version 10.0; it does not
use `_WIN32_WINNT=0x0B00`. These flags expose the needed structure fields in
the audited MSKLC headers; they do not turn those old headers into a modern
Windows 11 SDK. This layout uses only the established table ABI and has no
imported APIs. Compatibility still needs the live Windows 11 test below.

## Findings and exact header verification

The actual header used is:

`C:\Program Files (x86)\Microsoft Keyboard Layout Creator 1.4\inc\kbd.h`

SHA-256: `CCC198BC58549FBF1D5552838C67930111C910871E1BFC8A48A67DD7B236CD84`

Its lines 542-598 declare the following structure (comments omitted):

```c
typedef struct tagKbdLayer {
    PMODIFIERS pCharModifiers;
    PVK_TO_WCHAR_TABLE pVkToWcharTable;
    PDEADKEY pDeadKey;
    PVSC_LPWSTR pKeyNames;
    PVSC_LPWSTR pKeyNamesExt;
    WCHAR *KBD_LONG_POINTER *KBD_LONG_POINTER pKeyNamesDead;
    USHORT *KBD_LONG_POINTER pusVSCtoVK;
    BYTE bMaxVSCtoVK;
    PVSC_VK pVSCtoVK_E0;
    PVSC_VK pVSCtoVK_E1;
    DWORD fLocaleFlags;
    BYTE nLgMax;
    BYTE cbLgEntry;
    PLIGATURE1 pLigature;
#if (NTDDI_VERSION >= NTDDI_WINXP)
    DWORD dwType;
    DWORD dwSubType;
#endif
} KBDTABLES, *KBD_LONG_POINTER PKBDTABLES;
```

`KBD_LONG_POINTER` is `__ptr64` when `BUILD_WOW6432` is defined; otherwise it
is empty. `NTDDI_WINXP` is `0x05010000`. `KBD_VERSION` is **1**, and stays 1.
The actual preprocessed structures are saved in `out\<architecture>\CMKTST.i`.
The build uses `/X` and an explicit MSKLC include path, excluding ambient SDK
include directories. `layout-abi.h` asserts the size and **every field offset**
using that header, for each architecture.

| Field | AMD64 / WOW64 offset | Native x86 offset |
|---|---:|---:|
| fLocaleFlags | 80 | 40 |
| nLgMax | 84 | 44 |
| cbLgEntry | 85 | 45 |
| pLigature | 88 | 48 |
| dwType | 96 | 52 |
| dwSubType | 100 | 56 |
| sizeof(KBDTABLES) | 104 | 60 |

The installed `kbdutool.exe` embeds a compiler command with
`_WIN32_WINNT=0x0500` and `WINVER=0x0500`. In these headers, that derives
`NTDDI_VERSION=0x05000000`, excluding the two trailing fields. The newly
exported `.C` also omits their initializers. With a full structure, omitted
static fields would be zero-initialized; with the Windows 2000 structure,
those fields do not exist at all. Merely changing `#define KBD_TYPE 4` does
not fix this: it already equals 4 and controls scan-code macros.

The supplied 2018 `CMKUKB.dll` is byte-for-byte identical to the installed
System32 copy. Its descriptor returns RVA `0x1000`. At offset 96 from that
address are bytes `10 01 11 02 12 04 00 00`, the adjacent `VK_TO_BIT`
modifier entries: Shift/1, Ctrl/2, Alt/4, terminator. The first DWORD is
exactly **0x02110110**, your reported type. This strongly supports an
out-of-bounds interpretation of a truncated KBDTABLES. The next raw DWORD
is **0x00000412**, not the API subtype 2 you reported; the raw inspection
does not establish how your Windows call arrived at 2. It does establish
that this DLL lacks meaningful type/subtype values in those positions.

The exported `.H` has no T3A override and the `.KLC` has no Caps mapping in
its LAYOUT section. Its KEYNAME entry is only a label. The installed DLL
*does* map scan code 0x3A to VK_BACK, so the explicit H patch restores a
mapping that the export did not retain.

## Exact source changes

`source-changes.diff` records the full changes from your supplied files.
`prepare.py` creates the copies with guarded, exact substitutions.

1. Copy/rename `BKSPUK.C/.H/.RC/.DEF` to `CMKTST.C/.H/.RC/.DEF`.
   Update the C include to `CMKTST.h`; set `LIBRARY CMKTST` in the DEF;
   keep `KbdLayerDescriptor @1`. Change RC description/string 1000 to the
   test name, InternalName to `cmktst (3.40)`, and OriginalFilename to
   `cmktst.dll`. Keep the locale `en-GB` and language `0809`.
2. Append to `CMKTST.H`, after the base kbd.h and existing Colemak overrides:

   ```c
   #undef T3A
   #define T3A _EQ(BACK)
   ```

3. Change only the end of `KbdTables` in `CMKTST.C`:

   ```c
       MAKELONG(KLLF_ALTGR, KBD_VERSION),
       0,       // nLgMax
       0,       // cbLgEntry
       NULL,    // pLigature
       4,       // dwType
       0        // dwSubType
   };
   ```

   These are **five** fields after `fLocaleFlags`: do not put 4 and 0 in
   the ligature slots, change the version, or change structure packing.
4. Change the scan-code 0x3A key-name string to `L"Backspace"`, and include
   `layout-abi.h` after `CMKTST.h` for build-time ABI checks.
5. Rename the archived KLC's KBD identity/description to CMKTST/the test name.
   Its character mappings remain unchanged. The patched C/H files are the
   authoritative build input: the KLC does not represent the metadata fix
   or restored Caps remap. Regenerating C/H with kbdutool requires reapplying
   these patches; using its normal DLL build would reintroduce its old target.

No character rows, dead-key rows, shift states, AltGr flags, or original files
were changed. Caps now produces the same VK_BACK as the normal Backspace key,
including the existing Ctrl+Backspace translation. No global Scancode Map is needed.

## Build commands (ordinary PowerShell, no elevation)

The MSKLC 1.4 compiler, linker and resource compiler installed on this machine
are sufficient. A separate Visual Studio/WDK install is unnecessary for this build.

```powershell
Set-Location 'J:\C\cmkukb'
python .\test-layout\prepare.py
& .\test-layout\build.ps1 *> .\test-layout\build.log
if (-not $?) { throw 'Build failed; inspect test-layout\build.log' }
python .\test-layout\verify.py
if ($LASTEXITCODE -ne 0) { throw 'Verification failed' }
```

`build.ps1` contains the complete executable commands, with checked exit codes.
Critical compiler flags are:

```text
/TC /X /I<MSKLC>\inc /DWIN32_LEAN_AND_MEAN /DNOSERVICE /DNOMCX /DNOIME
/D_WIN32_WINNT=0x0A00 /DWINVER=0x0A00 /DNTDDI_VERSION=0x0A000000
/Zp8 /Gz /GS- /O1 /W3 /WX
```

AMD64 uses `bin\i386\amd64\cl.exe` and its linker. WOW64 uses
`bin\i386\cl.exe` plus `/DBUILD_WOW6432 /D_WOW6432_`. Native x86 uses the
same compiler without those two macros. The linker uses `/DLL /NOENTRY
/NODEFAULTLIB /SUBSYSTEM:NATIVE`, retains relocation information, and merges
the tables and descriptor into a read/execute `.data` section as the MSKLC
toolchain does. Its LNK4254 section-attribute merge warnings are expected;
the final PE section attributes were checked. No runtime libraries are imported.

On this **x64 Windows** machine:

| Build | Destination when installing |
|---|---|
| out\amd64\CMKTST.dll | %SystemRoot%\System32\CMKTST.dll |
| out\wow64\CMKTST.dll | %SystemRoot%\SysWOW64\CMKTST.dll |
| out\x86\CMKTST.dll | Only for System32 on a separate 32-bit Windows system |

Do not substitute the native x86 binary for the special WOW64 binary. These
are x86/x64 builds, not ARM64 builds. Windows 11 deployment uses only AMD64
and WOW64; the native x86 variant is retained for cross-architecture table
verification, not as a 32-bit Windows 11 installation target. The legacy
linker's PE subsystem versions (5.02/5.0) are minimum image-version metadata,
not a requirement to run an older Windows release; there is no reason to
raise them to change GetKeyboardType.

## Validation already performed

All three builds passed the header size/offset assertions and static PE checks.
`verify.py` reads the exported descriptor and tables directly from the PE file;
it does not load or execute the DLL. It verifies architecture, export,
native subsystem, no entry point/imports, relocations, `(dwType,dwSubType)=(4,0)`
and both Backspace scan codes. It compares the full character, dead-key,
modifier, base scan-code, E0 and E1 tables against the **installed original DLL**,
not just against the generated source. All those mappings are identical in all
three new binaries. Original source/KLC/DLL hashes remain unchanged.

The new layout has **not** been installed or activated here. Live
`GetKeyboardType` results and an RDP connection still require the following
post-installation tests; the binary inspection alone is not that runtime test.

## Install the separate test layout

First retain a working UK or original Colemak layout in the Windows keyboard
list, and verify that Win+Space switches to it. Install only after the build
and verification above succeed. Use **64-bit PowerShell as Administrator**.
The commands below select `A0020809` / Layout Id `00C2` and stop on any collision;
these are separate from the two existing Colemak registrations found here.

```powershell
$ErrorActionPreference = 'Stop'
Set-Location 'J:\C\cmkukb\test-layout'
if (-not [Environment]::Is64BitProcess -or
    $env:PROCESSOR_ARCHITECTURE -ne 'AMD64') { throw 'Use native x64 PowerShell' }
$admin = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $admin.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run as Administrator'
}
$base = 'HKLM:\SYSTEM\CurrentControlSet\Control\Keyboard Layouts'
$key = "$base\A0020809"
$dest64 = Join-Path $env:SystemRoot 'System32\CMKTST.dll'
$destWow = Join-Path $env:SystemRoot 'SysWOW64\CMKTST.dll'
if ((Test-Path -LiteralPath $key) -or (Test-Path -LiteralPath $dest64) -or
    (Test-Path -LiteralPath $destWow)) { throw 'Test identity or DLL already exists; stop' }
$collision = Get-ChildItem -LiteralPath $base | ForEach-Object {
    Get-ItemProperty -LiteralPath $_.PSPath
} | Where-Object { $_.'Layout Id' -eq '00c2' -or $_.'Layout File' -eq 'CMKTST.dll' }
if ($collision) { throw 'Layout Id or filename already registered; stop' }

# Unique backup directory, including the existing installed keyboard registration.
$backup = New-Item -ItemType Directory -Path ('.\backup-' + [guid]::NewGuid().ToString('N'))
reg.exe export 'HKLM\SYSTEM\CurrentControlSet\Control\Keyboard Layouts\A0000809' "$($backup.FullName)\original-layout.reg"
if ($LASTEXITCODE -ne 0) { throw 'Original layout backup failed' }
reg.exe export 'HKCU\Keyboard Layout' "$($backup.FullName)\user-keyboards.reg"
if ($LASTEXITCODE -ne 0) { throw 'User keyboard backup failed' }
Copy-Item -LiteralPath "$env:SystemRoot\System32\CMKUKB.dll" -Destination $backup.FullName

# File.Copy(false) refuses to overwrite an existing file.
[IO.File]::Copy((Resolve-Path '.\out\amd64\CMKTST.dll').Path, $dest64, $false)
[IO.File]::Copy((Resolve-Path '.\out\wow64\CMKTST.dll').Path, $destWow, $false)
New-Item -Path $key -ErrorAction Stop | Out-Null
New-ItemProperty -LiteralPath $key -Name 'Layout File' -PropertyType String -Value 'CMKTST.dll' | Out-Null
New-ItemProperty -LiteralPath $key -Name 'Layout Text' -PropertyType String -Value 'Colemak UK BKSP - Type4 Test' | Out-Null
New-ItemProperty -LiteralPath $key -Name 'Layout Id' -PropertyType String -Value '00c2' | Out-Null
New-ItemProperty -LiteralPath $key -Name 'Layout Display Name' -PropertyType ExpandString -Value '@%SystemRoot%\system32\CMKTST.dll,-1000' | Out-Null
```

If installation stops partway through, stop and inspect the named test files/key;
do not rerun with `-Force`. The rollback below can remove the partial test install.
No existing layout key, default input method, global keyboard type override, or
original DLL is modified. This manual test installation does not create an MSI
entry in Installed apps; use the explicit rollback below.

Sign out and back in if needed. Under Settings > Time & language >
Language & region > English (United Kingdom) > Language options > Keyboards,
add **Colemak UK BKSP - Type4 Test**. UI wording may vary by Windows version.
Use Win+Space to select it without making it the default initially.

## Runtime and RDP test

Run this from an interactive, ordinary x64 PowerShell after installation:

```powershell
Set-Location 'J:\C\cmkukb\test-layout'
& .\check-installed.ps1 -Klid A0020809
```

The probe explicitly loads/activates the named installed layout, performs all
API calls on one native thread, checks KLID, and restores the previous layout
in a finally block. It may leave the newly loaded layout available in the session.
Expected output:

```text
PASS: KLID=A0020809; type=4; subtype=0; Caps VK=0x08; Backspace VK=0x08
```

Then select the test layout in Notepad and check the letter rows
`qwfpgjluy;`, `arstdhneio`, `zxcvbkm`; UK Shift+2 (`"`), Shift+3 (`£`),
the ISO backslash/pipe key, normal Backspace and Caps/Backspace, Ctrl shortcuts,
AltGr characters and dead keys (for example AltGr+physical E gives `ã`,
AltGr+physical F followed by A gives `á`). Check that Caps does not toggle case.
Turn Caps Lock off before switching if it was already on in another layout.

Fully disconnect and reconnect the RDP client with the test layout selected
in that client, because keyboard metadata can be sent during connection setup.
Check the negotiated type/subtype if client/server diagnostics expose them,
then test ordinary typing, Caps/Backspace, AltGr and dead keys remotely.
Matching metadata addresses the invalid-type problem; remote scan-code layout
selection and character handling still need this end-to-end check. A custom
KLID is not automatically a remote Colemak character-map installation.

## Rollback

1. Switch to the original Colemak or standard UK layout with Win+Space.
   Remove **only the test layout** from the English (United Kingdom) keyboard
   list. Restore the prior default if you chose to change it. Close RDP clients.
2. In an elevated x64 PowerShell, remove only the test registration. The guard
   also permits a partial registration created by the commands above:

   ```powershell
   $ErrorActionPreference = 'Stop'
   $path = 'SYSTEM\CurrentControlSet\Control\Keyboard Layouts'
   $parent = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey($path, $true)
   try {
       $test = $parent.OpenSubKey('A0020809')
       if ($test) {
           try {
               $file = $test.GetValue('Layout File')
               $id = $test.GetValue('Layout Id')
               if (($file -and $file -ne 'CMKTST.dll') -or ($id -and $id -ne '00c2')) {
                   throw 'Registration is not the test layout; stop'
               }
               if ($test.SubKeyCount -ne 0) { throw 'Unexpected subkeys; stop' }
           } finally { $test.Dispose() }
           $parent.DeleteSubKey('A0020809', $false)
       }
   } finally { $parent.Dispose() }
   ```

3. Restart Windows to release loaded copies. In elevated **x64** PowerShell,
   delete just these two files after checking their hashes against your build:

   ```powershell
   Set-Location 'J:\C\cmkukb\test-layout'
   $pairs = @(
       @('.\out\amd64\CMKTST.dll', "$env:SystemRoot\System32\CMKTST.dll"),
       @('.\out\wow64\CMKTST.dll', "$env:SystemRoot\SysWOW64\CMKTST.dll")
   )
   foreach ($pair in $pairs) {
       if (Test-Path -LiteralPath $pair[1]) {
           if ((Get-FileHash -LiteralPath $pair[0]).Hash -ne
               (Get-FileHash -LiteralPath $pair[1]).Hash) { throw 'Unexpected DLL; stop' }
           Remove-Item -LiteralPath $pair[1] -ErrorAction Stop
       }
   }
   ```

If a file is still in use, keep a working layout selected and restart again;
do not take ownership of or replace the original/system layouts. The original
layout needs no reinstall because neither its file nor its registration changed.
The backup exports are for recovery/reference, not routine bulk re-import: doing
that could discard unrelated keyboard preference changes made since the backup.

## Microsoft references

- [Operating system versions](https://learn.microsoft.com/en-us/windows/win32/sysinfo/operating-system-version) and [Windows version macros](https://learn.microsoft.com/en-us/cpp/porting/modifying-winver-and-win32-winnt): Windows 11 reports version 10.0, and 0x0A00 is the corresponding WINVER/_WIN32_WINNT baseline.
- [GetKeyboardType](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getkeyboardtype): flag 0 queries type, flag 1 subtype; type 4 denotes an enhanced 101/102-key keyboard, and subtype 0 is valid.
- [Keyboard layout samples](https://learn.microsoft.com/en-us/samples/microsoft/windows-driver-samples/keyboard-layout-samples/): describes the scan-code/character tables and KbdLayerDescriptor model. Its legacy replacement installation example is not used for this separate test layout.
- [Keyboard identifiers](https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/windows-language-pack-default-values?view=windows-11): layouts are registered under HKLM's Keyboard Layouts key.
- [Registry string redirection](https://learn.microsoft.com/en-us/windows/win32/intl/using-registry-string-redirection): documents the resource-reference form used for Layout Display Name.
