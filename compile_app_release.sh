#!/bin/bash

set -e  # Stop on first error
./bump_version.sh  # Ensure version is bumped before building
git add latest_version.txt version_info.txt app.py
git commit -m "Bump version to $(cat latest_version.txt)"
git push origin main
# 2. Read version
VERSION=$(cat latest_version.txt)
echo "📦 Building SVNManager version $VERSION"

# 3. Clean previous builds
rm -rf build/ dist/ SVNManager.spec

# 4. Build as a folder (onedir), not a single self-extracting EXE.
#    Onefile builds unpack Oracle/Python DLLs into %TEMP% and AVG flags that as malware.
./compile_app.sh

find_signtool() {
    if command -v signtool.exe >/dev/null 2>&1; then
        command -v signtool.exe
        return
    fi
    if command -v signtool >/dev/null 2>&1; then
        command -v signtool
        return
    fi
    local found=""
    found=$(ls "/c/Program Files (x86)/Windows Kits/10/bin/"*/x64/signtool.exe 2>/dev/null | sort | tail -n 1 || true)
    echo "$found"
}

sign_exe() {
    local exe="$1"
    local signtool_bin
    signtool_bin=$(find_signtool)

    if [ -z "$signtool_bin" ]; then
        echo "⚠️ signtool not found. Skipping Authenticode signing."
        echo "   Unsigned EXEs are much more likely to be flagged by AVG/SmartScreen."
        echo "   Install the Windows SDK, or ask IT for CyFrame's code-signing certificate."
        return
    fi

    if [ -n "$SIGN_PFX" ]; then
        echo "🔏 Signing $exe with PFX certificate..."
        if [ -n "$SIGN_PASSWORD" ]; then
            "$signtool_bin" sign /fd SHA256 /td SHA256 /tr http://timestamp.digicert.com \
                /f "$SIGN_PFX" /p "$SIGN_PASSWORD" "$exe"
        else
            "$signtool_bin" sign /fd SHA256 /td SHA256 /tr http://timestamp.digicert.com \
                /f "$SIGN_PFX" "$exe"
        fi
        echo "✅ Signed $exe"
    elif [ -n "$SIGN_SUBJECT" ]; then
        echo "🔏 Signing $exe with certificate '$SIGN_SUBJECT' from the Windows store..."
        "$signtool_bin" sign /fd SHA256 /td SHA256 /tr http://timestamp.digicert.com \
            /n "$SIGN_SUBJECT" "$exe"
        echo "✅ Signed $exe"
    else
        echo "⚠️ No code-signing certificate configured. AVG may still flag the download."
        echo "   Set SIGN_PFX (+ optional SIGN_PASSWORD) or SIGN_SUBJECT, then rebuild."
        echo "   Example: export SIGN_SUBJECT='CyFrame'"
    fi
}

sign_exe "dist/SVNManager/SVNManager.exe"

echo "📦 Creating dist/SVNManager.zip"
rm -f dist/SVNManager.zip
if command -v powershell.exe >/dev/null 2>&1; then
    powershell.exe -NoProfile -Command "Compress-Archive -Path 'dist\\SVNManager' -DestinationPath 'dist\\SVNManager.zip' -Force"
elif command -v zip >/dev/null 2>&1; then
    (cd dist && zip -r SVNManager.zip SVNManager)
else
    echo "❌ Need powershell.exe or zip to package the onedir build"
    exit 1
fi

# 5. Create a Git tag if it doesn't exist
if git rev-parse "$VERSION" >/dev/null 2>&1; then
    echo "✅ Git tag $VERSION already exists"
else
    echo "🏷️ Creating Git tag $VERSION"
    git tag "$VERSION"
    git push origin "$VERSION"
fi

# 6. Create a GitHub Release manually with curl

# You need a GitHub personal access token with "repo" rights
# Save it once in environment: export GH_TOKEN=your_token_here
if [ -z "$GH_TOKEN" ]; then
    echo "❌ GH_TOKEN is not set. Do: export GH_TOKEN=your_token_here"
    exit 1
fi

REPO="CArchambault00/SVNManager"   # <== CHANGE THIS TO YOUR REPO

echo "🚀 Creating GitHub Release $VERSION"

CREATE_RESPONSE=$(curl -s -X POST \
    -H "Authorization: token $GH_TOKEN" \
    -H "Content-Type: application/json" \
    "https://api.github.com/repos/$REPO/releases" \
    -d @- <<EOF
{
  "tag_name": "$VERSION",
  "target_commitish": "main",
  "name": "SVN Manager $VERSION",
  "body": "Auto release for version $VERSION\n\nDownload SVNManager.zip, extract it, and run SVNManager.exe from inside the extracted SVNManager folder.\n\nDo not copy the .exe somewhere else by itself — it needs the other files in that folder.\n\nSettings (svn_config.json / svn_profiles.json) are stored in %APPDATA%\\\\SVNManager.\nFirst update: if prompted, pick the folder that already has your old JSON files (or extract/run once next to them). After that, extract new releases anywhere — including Downloads — and your settings will still load.\n\nThis is distributed as a folder (zip) instead of a single EXE so antivirus software is less likely to flag it.",
  "draft": false,
  "prerelease": false
}
EOF
)

UPLOAD_URL=$(echo "$CREATE_RESPONSE" | grep upload_url | cut -d '"' -f 4 | cut -d '{' -f 1)

if [ -z "$UPLOAD_URL" ]; then
    echo "❌ Failed to create GitHub release. Response:"
    echo "$CREATE_RESPONSE"
    exit 1
fi

# 7. Upload the zip (onedir folder). Do not upload a onefile EXE — AVG flags those.

echo "📤 Uploading dist/SVNManager.zip to GitHub Release"

curl -s --data-binary @"dist/SVNManager.zip" \
    -H "Authorization: token $GH_TOKEN" \
    -H "Content-Type: application/zip" \
    "$UPLOAD_URL?name=SVNManager.zip"

echo "✅ Build and Release Completed Successfully!"
echo "ℹ️ After releasing, submit dist/SVNManager/SVNManager.exe to AVG if it is still flagged:"
echo "   https://www.avg.com/en-us/false-positive-file-form"
