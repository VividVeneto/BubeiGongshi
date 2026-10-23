"""Build the supplemental C DLL test double, not a Rust async substitute."""
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build/binding-fixture"
OUT.mkdir(parents=True, exist_ok=True)
vswhere = Path(os.environ["ProgramFiles(x86)"]) / "Microsoft Visual Studio/Installer/vswhere.exe"
install = subprocess.check_output([str(vswhere), "-latest", "-property", "installationPath", "-utf8"], text=True, encoding="utf-8").strip()
vcvars = Path(install) / "VC/Auxiliary/Build/vcvarsall.bat"
command = ('call "' + str(vcvars) + '" x64 >nul && cl /nologo /TC /W4 /WX /std:c11 /LD /I"'
           + str(ROOT / "contracts/include") + '" "' + str(ROOT / "app/test/binding_fixture.c")
           + '" /Fo"' + str(OUT / "fixture.obj") + '" /Fe"' + str(OUT / "fixture.dll") + '"')
command += ' /link ' + ' '.join('/EXPORT:' + name for name in ('fml_abi_version', 'fml_capabilities', 'fml_call', 'fml_submit', 'fml_cancel', 'fml_register_completion', 'fml_free_buffer', 'fml_close_handle'))
result = subprocess.run('cmd.exe /d /s /c "' + command + '"', cwd=OUT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
(OUT / "compile.log").write_bytes(result.stdout)
print(f"fixture compiler exit={result.returncode}; diagnostics retained as raw bytes")
raise SystemExit(result.returncode)
