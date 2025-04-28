#!/bin/bash

set -e  # Stop on first error

# Read version
VERSION=$(cat latest_version.txt)
echo "📦 Building SVNManager version $VERSION"

# Clean previous builds
rm -rf build/ dist/ SVNManager.spec

# Build the executable
pyinstaller --onefile --noconsole --icon=SVNManagerIcon.ico \
    --collect-all oracledb \
    --collect-all tkinterdnd2 \
    --recursive-copy-metadata oracledb \
    --hidden-import=* \
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
    app.py

# Check if tag exists
if git rev-parse "$VERSION" >/dev/null 2>&1; then
    echo "✅ Git tag $VERSION already exists"
else
    echo "🏷️ Creating Git tag $VERSION"
    git tag "$VERSION"
    git push origin "$VERSION"
fi

# Create GitHub Release with the compiled app
echo "🚀 Creating GitHub Release $VERSION"
gh release create "$VERSION" "dist/SVNManager.exe" --title "SVN Manager $VERSION" --notes "Auto release for version $VERSION"

echo "✅ Build and release completed!"
