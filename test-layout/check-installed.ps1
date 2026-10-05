[CmdletBinding()]
param([ValidatePattern('^[0-9A-Fa-f]{8}$')][string]$Klid = 'A0020809')
$ErrorActionPreference = 'Stop'
# Run interactively after installation. This temporarily activates the test
# layout, reads its values on the SAME native thread, then restores that thread.
# Windows may also expose a newly loaded layout in the session's layout list.
if (-not ('ColemakTestProbe' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Text;
public static class ColemakTestProbe {
    [DllImport("user32.dll")] static extern IntPtr GetKeyboardLayout(uint thread);
    [DllImport("user32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    static extern IntPtr LoadKeyboardLayout(string klid, uint flags);
    [DllImport("user32.dll", SetLastError=true)]
    static extern IntPtr ActivateKeyboardLayout(IntPtr hkl, uint flags);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)]
    static extern bool GetKeyboardLayoutName(StringBuilder name);
    [DllImport("user32.dll")] static extern int GetKeyboardType(int flag);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)]
    static extern uint MapVirtualKeyEx(uint code, uint mapType, IntPtr hkl);
    public static string Run(string klid) {
        IntPtr previous = GetKeyboardLayout(0);
        try {
            IntPtr test = LoadKeyboardLayout(klid, 0);
            if (test == IntPtr.Zero) throw new System.ComponentModel.Win32Exception();
            if (ActivateKeyboardLayout(test, 0) == IntPtr.Zero)
                throw new System.ComponentModel.Win32Exception();
            var name = new StringBuilder(9);
            if (!GetKeyboardLayoutName(name)) throw new Exception("Cannot read KLID");
            int type = GetKeyboardType(0), subtype = GetKeyboardType(1);
            uint caps = MapVirtualKeyEx(0x3A, 3, test);
            uint back = MapVirtualKeyEx(0x0E, 3, test);
            string result = String.Format("KLID={0}; type={1}; subtype={2}; Caps VK=0x{3:X2}; Backspace VK=0x{4:X2}",
                name, type, subtype, caps, back);
            if (!String.Equals(name.ToString(), klid, StringComparison.OrdinalIgnoreCase)
                || type != 4 || subtype != 0 || caps != 8 || back != 8)
                throw new Exception("Unexpected installed layout: " + result);
            return "PASS: " + result;
        } finally {
            if (ActivateKeyboardLayout(previous, 0) == IntPtr.Zero)
                throw new System.ComponentModel.Win32Exception();
        }
    }
}
'@
}
[ColemakTestProbe]::Run($Klid)
