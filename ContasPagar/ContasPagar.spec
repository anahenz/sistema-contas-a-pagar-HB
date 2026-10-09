# Build on Windows: python -m PyInstaller --clean --noconfirm ContasPagar.spec
from pathlib import Path
root = Path(SPECPATH)
a = Analysis([str(root / 'main.py')], pathex=[str(root)],
    binaries=[], datas=[(str(root / 'app' / 'assets'), 'app/assets')],
    hiddenimports=['sqlalchemy.dialects.sqlite', 'reportlab.pdfbase._fontdata_enc_winansi'],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='ContasPagar',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, disable_windowed_traceback=False, icon=str(root / 'app' / 'assets' / 'app.ico'))
