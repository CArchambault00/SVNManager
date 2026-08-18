# Security Notice

## False Positive Antivirus Detection

If AVG, Avast, or another antivirus flags `SVNManager.exe`, it is a **false positive**. The app is a Python GUI packaged with PyInstaller. That packaging style is also used by real malware, so heuristic scanners often treat unsigned Python EXEs as suspicious.

### Why this used to happen more often

Older releases were a single ~120MB `--onefile` executable. At startup that EXE unpacked Python and Oracle Instant Client DLLs into `%TEMP%`, which looks like a malware dropper to AVG.

Current releases are a **folder inside `SVNManager.zip`**. The EXE no longer unpacks itself into a temp directory.

### How to install a new version

1. Download `SVNManager.zip` only from official GitHub releases: https://github.com/CArchambault00/SVNManager/releases
2. Extract the zip
3. Run `SVNManager.exe` from **inside** the extracted `SVNManager` folder
4. Do not copy the `.exe` somewhere else by itself

### If AVG still flags it

1. Submit the file as a false positive (each new unsigned build has a new hash):
   - AVG: https://www.avg.com/en-us/false-positive-file-form
   - Avast: https://www.avast.com/false-positive-file-form
2. Add `SVNManager.exe` (or the whole folder) to AVG exclusions: Menu → Settings → General → Exceptions
3. Scan with multiple engines on [VirusTotal](https://www.virustotal.com/) if you want a second opinion

### Lasting fix: code-sign the EXE

Unsigned downloads from GitHub are the other reason AVG/SmartScreen warn on **download**. A CyFrame (or other OV/EV) code-signing certificate is the durable fix.

The release script will sign automatically when you set one of:

```sh
export SIGN_PFX="C:/path/to/cyframe.pfx"
export SIGN_PASSWORD="..."          # optional if the PFX has no password

# or, if the cert is already in the Windows certificate store:
export SIGN_SUBJECT="CyFrame"
```

Then run `./compile_app_release.sh` as usual.

Ask IT for the company code-signing certificate if you do not have one. After a file is signed, you can also ask AVG to whitelist the **publisher certificate**, so later versions are less likely to be flagged.

### Source Code

The complete source code is available in this repository for security review.

## Reporting Security Issues

If you discover a legitimate security vulnerability, please report it privately to the repository owner.
