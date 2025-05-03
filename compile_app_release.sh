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

# 4. Build the executable
pyinstaller --onefile --noconsole --icon=SVNManagerIcon.ico     --collect-all oracledb  --collect-all tkinterdnd2    --recursive-copy-metadata oracledb     --hidden-import=*     --hidden-import=secrets     --hidden-import=uuid     --hidden-import=getpass     --hidden-import=threading     --hidden-import=socket     --hidden-import=platform     --hidden-import=time     --hidden-import=decimal     --hidden-import=datetime     --hidden-import=collections     --hidden-import=base64     --hidden-import=weakref     --hidden-import=warnings     --hidden-import=oracledb.base_impl     --hidden-import=oracledb.thick_impl     --hidden-import=oracledb.thin_impl --hidden-import=asyncio --name=SVNManager --version-file=version_info.txt --add-data "instantclient_12_1/*;instantclient_12_1"  app.py

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
  "body": "Auto release for version $VERSION",
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

# 7. Upload the compiled EXE

echo "📤 Uploading dist/SVNManager.exe to GitHub Release"

curl -s --data-binary @"dist/SVNManager.exe" \
    -H "Authorization: token $GH_TOKEN" \
    -H "Content-Type: application/octet-stream" \
    "$UPLOAD_URL?name=SVNManager.exe"

echo "✅ Build and Release Completed Successfully!"
