# Security Notice

## False Positive Antivirus Detection

If your antivirus software flags `SVNManager.exe` as a potential threat, this is a **false positive**. This is a common issue with applications built using PyInstaller.

### Why This Happens
- PyInstaller bundles Python code into a single executable
- The self-extracting nature can trigger antivirus heuristics
- The executable is not code-signed (requires expensive certificate)

### Verification Steps
1. **Check the file hash** against the official release
2. **Download only from official GitHub releases**: https://github.com/CArchambault00/SVNManager/releases
3. **Scan with multiple antivirus engines** using VirusTotal.com

### Whitelist Instructions
To use SVNManager, you may need to:
1. Add `SVNManager.exe` to your antivirus whitelist/exclusions
2. Temporarily disable real-time protection during installation
3. Contact your IT department if in a corporate environment

### Source Code
The complete source code is available in this repository for security review.

## Reporting Security Issues
If you discover a legitimate security vulnerability, please report it privately to the repository owner.
