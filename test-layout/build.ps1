[CmdletBinding()]
param([string]$Msklc = 'C:\Program Files (x86)\Microsoft Keyboard Layout Creator 1.4')
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$inc = Join-Path $Msklc 'inc'
$bin = Join-Path $Msklc 'bin\i386'
# /X excludes ambient INCLUDE paths: these are the headers we actually audited.
$common = @('/nologo','/TC','/X',"/I$inc",'/DWIN32_LEAN_AND_MEAN',
    '/DNOSERVICE','/DNOMCX','/DNOIME','/D_WIN32_WINNT=0x0A00',
    '/DWINVER=0x0A00','/DNTDDI_VERSION=0x0A000000',
    '/Zp8','/Gz','/GS-','/O1','/W3','/WX')

function Invoke-Checked([string]$Exe, [string[]]$Arguments) {
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Exe failed ($LASTEXITCODE)" }
}

Push-Location $PSScriptRoot
try {
    foreach ($arch in @('amd64','wow64','x86')) {
        $out = Join-Path $PSScriptRoot "out\$arch"
        New-Item -ItemType Directory -Path $out -Force | Out-Null
        $compilerBin = $bin
        $machine = 'X86'
        $subsystem = '/SUBSYSTEM:NATIVE,5.0'
        $extra = @()
        if ($arch -eq 'amd64') {
            $compilerBin = Join-Path $bin 'amd64'
            $machine = 'X64'
            $subsystem = '/SUBSYSTEM:NATIVE,5.02'
        } elseif ($arch -eq 'wow64') {
            $extra = @('/DBUILD_WOW6432','/D_WOW6432_')
        }
        $cl = Join-Path $compilerBin 'cl.exe'
        $link = Join-Path $compilerBin 'link.exe'
        Push-Location $out
        try {
            # Save the compiler's effective header definition for review.
            Invoke-Checked $cl ($common + $extra + @('/P','..\..\CMKTST.C'))
            Invoke-Checked $cl ($common + $extra + @('/c','/showIncludes','/FoCMKTST.obj','..\..\CMKTST.C'))
            Invoke-Checked (Join-Path $bin 'rc.exe') @('/r',"/i$inc",'/foCMKTST.res','..\..\CMKTST.RC')
            Invoke-Checked $link @('/nologo','/DLL','/NOENTRY','/NODEFAULTLIB',
                "/MACHINE:$machine",$subsystem,'/RELEASE','/STACK:0x40000,0x1000',
                '/OPT:REF','/OPT:ICF','/MERGE:.rdata=.data','/MERGE:.text=.data',
                '/MERGE:.edata=.data','/MERGE:.bss=.data','/SECTION:.data,RE',
                '/DEF:..\..\CMKTST.DEF','/OUT:CMKTST.dll','/MAP:CMKTST.map',
                'CMKTST.obj','CMKTST.res')
            if (-not (Test-Path -LiteralPath 'CMKTST.dll')) { throw 'Missing DLL' }
        } finally { Pop-Location }
    }
} finally { Pop-Location }
Write-Host 'Built amd64, WOW64, and native x86 variants. Nothing installed.'
