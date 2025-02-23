#!/bin/bash

# Check if SVN repo path is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <SVN_REPO_PATH> <USERNAME>"
    exit 1
fi

# Check if username is provided
if [ -z "$2" ]; then
    echo "Please provide a username."
    exit 1
fi

SVN_PATH="$1"
USERNAME="$2"

# Run svn status to get lock information
LOCKED_FILES=$(svn status --show-updates --verbose "$SVN_PATH" | awk -v user="$USERNAME" '$0 ~ /O/ && $NF == user {print $(NF-1)}')

# Display results
if [ -n "$LOCKED_FILES" ]; then
    echo "Files locked by $USERNAME:"
    echo "$LOCKED_FILES"
else
    echo "No files locked by $USERNAME."
fi
