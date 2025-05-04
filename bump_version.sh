#!/bin/bash

# Files to update
APP_PY="app.py"
LATEST_VERSION="latest_version.txt"
VERSION_INFO="version_info.txt"

# Get the current version from app.py
CURRENT_VERSION=$(grep 'APP_VERSION = "' "$LATEST_VERSION" | cut -d'"' -f2)
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"

# Increment patch version
NEW_PATCH=$((PATCH + 1))
NEW_VERSION="$MAJOR.$MINOR.$NEW_PATCH"
NEW_VERSION_COMMA="$MAJOR, $MINOR, $NEW_PATCH, 0"
NEW_VERSION_DOTTED="$MAJOR.$MINOR.$NEW_PATCH.0"

echo "Updating version to $NEW_VERSION"

# Update app.py
sed -i "s/APP_VERSION = \".*\"/APP_VERSION = \"$NEW_VERSION\"/" "$APP_PY"

# Update latest_version.txt
echo "$NEW_VERSION" > "$LATEST_VERSION"

# Update version_info.txt
sed -i "s/filevers=(.*)/filevers=($NEW_VERSION_COMMA)/" "$VERSION_INFO"
sed -i "s/prodvers=(.*)/prodvers=($NEW_VERSION_COMMA)/" "$VERSION_INFO"
sed -i "s/StringStruct('FileVersion', '.*')/StringStruct('FileVersion', '$NEW_VERSION_DOTTED')/" "$VERSION_INFO"
sed -i "s/StringStruct('ProductVersion', '.*')/StringStruct('ProductVersion', '$NEW_VERSION_DOTTED')/" "$VERSION_INFO"

echo "Version successfully updated to $NEW_VERSION"
