#!/bin/bash
set -e

# --onedir (not --onefile): a onefile EXE unpacks ~100MB of DLLs into %TEMP% at
# launch. AVG/Avast treat that dropper-like behavior as malware.
# --noupx: UPX-packed binaries are also heavily associated with malware.
# --noconfirm: overwrite dist/ without prompting.

pyinstaller --noconfirm --clean --onedir --noconsole --noupx \
    --icon=SVNManagerIcon.ico \
    --collect-all oracledb \
    --collect-all tkinterdnd2 \
    --recursive-copy-metadata oracledb \
    --hidden-import=secrets \
    --hidden-import=uuid \
    --hidden-import=getpass \
    --hidden-import=threading \
    --hidden-import=socket \
    --hidden-import=platform \
    --hidden-import=time \
    --hidden-import=decimal \
    --hidden-import=datetime \
    --hidden-import=collections \
    --hidden-import=base64 \
    --hidden-import=weakref \
    --hidden-import=warnings \
    --hidden-import=oracledb.base_impl \
    --hidden-import=oracledb.thick_impl \
    --hidden-import=oracledb.thin_impl \
    --hidden-import=asyncio \
    --name=SVNManager \
    --version-file=version_info.txt \
    --add-data "instantclient_12_1/*;instantclient_12_1" \
    --add-data "SVNManagerIcon.ico;." \
    --manifest=manifest.xml \
    app.py

cat > dist/SVNManager/README.txt << 'EOF'
SVN Manager
===========

Run SVNManager.exe from THIS folder.

Do not copy the .exe somewhere else by itself. It needs the other files
in this folder (including the _internal directory) to start.

If antivirus flags SVNManager.exe, that is a false positive caused by
how Python apps are packaged. Download only from official GitHub releases:
https://github.com/CArchambault00/SVNManager/releases
EOF

echo "✅ Build finished: dist/SVNManager/SVNManager.exe"
