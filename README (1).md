# 3DS RAM Unlock Patcher

A small Windows tool that patches the **memory mode** of a Nintendo 3DS game's main content file (`0000.XXXXXXXX.app`, extracted from a `.CIA`) for both **Old 3DS** and **New 3DS** consoles.

Drag the `.app` onto the window, and the patched copy (`<name>_max.app`) is written **next to the program**. Your original file is never modified.

- Dark theme (black background, cyan borders, white text)
- Languages: **English, Español, Português** (buttons at the top)
- **F1** opens a built-in guide on extracting the `.app` from a `.CIA` with GodMode9
- Single-file `.exe`, nothing to install

---

## Table of contents

1. [What it does](#what-it-does)
2. [Quick start](#quick-start)
3. [Getting the `.app` from a `.CIA` with GodMode9](#getting-the-app-from-a-cia-with-godmode9)
4. [Using the program](#using-the-program)
5. [Building the `.exe`](#building-the-exe)
6. [How the patch works](#how-the-patch-works)
7. [After patching: putting the file back into a CIA](#after-patching-putting-the-file-back-into-a-cia)
8. [Troubleshooting](#troubleshooting)
9. [Project files](#project-files)
10. [Disclaimer](#disclaimer)

---

## What it does

Every 3DS title's main content is an NCCH container. Inside it, the **Extended Header (ExHeader)** declares how much memory the title requests and which system mode it runs in. This tool edits those fields in two places of the ExHeader (the process info and the access-descriptor limits), then recomputes the ExHeader hash stored in the NCCH header so the file stays internally consistent.

| Console | Field changed | New value |
|---|---|---|
| Old 3DS | system mode (high nibble of ExHeader byte `0x0E`) | `3` |
| New 3DS | New3DS system mode (low nibble of ExHeader byte `0x0D`) | `1` (124 MB) |

The values are exactly the ones used by the original `max.py` script this tool is based on. If you want different modes, change `OLD_MODE` and `NEW_MODE` near the top of `RAM_Unlock_3DS.py`.

> The meaning of each mode value is documented on 3dbrew (ExHeader page). Check it there if you plan to use other values.

---

## Quick start

1. Extract `0000.XXXXXXXX.app` from your `.cia` (see the GodMode9 section below, or press **F1** in the program).
2. Copy that `.app` to your PC.
3. Run `3DS_RAM_Unlock.exe`.
4. Drag the `.app` into the window (or click the box to choose it).
5. Find `<name>_max.app` in the same folder as the program. The log in the window shows the full path and the old → new mode values.

---

## Getting the `.app` from a `.CIA` with GodMode9

You need a 3DS with custom firmware and [GodMode9](https://github.com/d0k3/GodMode9) installed. Menu names can differ slightly between GodMode9 versions, so follow what you see on screen if a label is a little different.

1. **Copy the `.cia`** to your 3DS SD card (any folder).
2. **Open GodMode9** by holding **START** while powering on the console.
3. Go to **`[0:] SDCARD`** and highlight your `.cia` file. Press **A**.
4. Choose **"Mount image to drive"** (listed under the CIA image options).
5. A **virtual drive** appears (for example `G:`). Open it. You will see several files, such as `.tmd` and one or more `.app` files:
   - **`0000.XXXXXXXX.app`** is the one you need. Index `0000` is the title's main content, and it is usually the largest file.
   - Other `.app` files (higher indexes) are things like the manual or download-play child, and are **not** what you want.
6. Highlight `0000.XXXXXXXX.app` and press **Y** to copy it. Navigate to **`[0:] SDCARD/gm9/out`** (or any folder you like) and press **Y** again, then choose **"Copy path here"**.
7. **If the `.app` is encrypted**: highlight it, press **A**, then choose **"NCCH image options"** → **"Decrypt file (0:/gm9/out)"**. Use the decrypted copy. This tool needs a **decrypted** file; it will refuse an encrypted one.
8. Turn the console off, take out the SD card, and copy the `.app` to your PC.
9. Continue with [Using the program](#using-the-program).

---

## Using the program

- **Drag & drop** one or more `.app` files onto the window. Each one is processed in order.
- Or click the box / **Choose .app** to pick files with a normal file dialog.
- **Open output folder** opens the folder where results are saved. That is always the folder that contains the program.
- **Language** buttons (top right) switch the whole interface, including the F1 guide.
- **F1** (or the **Help** button) opens/closes the extraction guide. **Esc** also closes it.

Output rules:

- The result is named `<original name>_max.app`, for example `0000.0004abcd_max.app`.
- If that file already exists, a number is added (`_max_2.app`, `_max_3.app`, …) so nothing is overwritten.
- The original `.app` is only read, never written.

Checks done before patching, with a clear message in your language if one fails:

| Message | Meaning |
|---|---|
| File too small | Not a valid `.app` |
| NCCH header not found | Not an NCCH file (wrong file picked, e.g. the `.tmd` or a `.cia`) |
| No ExHeader | The container has nothing to patch |
| Still encrypted | Decrypt it first (step 7 above) |
| Verification failed | The written file did not pass the post-patch check |

After writing the file, the tool re-reads it and verifies both the new mode values and the recalculated hash. If `ctrtool.exe` is bundled, it is also run as an extra, best-effort check, and any lines it prints about the system mode or ExHeader hash are shown in the log. If `ctrtool` is missing or fails, the patch result is unaffected.

---

## Building the `.exe`

You only need this if you are building it yourself. Requirements: **Windows**, **Python 3.10+** from python.org (3.12 is the safest choice; newer versions usually work too).

Put these files in one folder:

```
RAM_Unlock_3DS.py
build_exe.py
ctrtool.exe      (optional, bundled inside the exe)
makerom.exe      (optional, bundled inside the exe)
icon.ico         (optional)
```

Then open a terminal **in that folder** (type `cmd` in the Explorer address bar) and run:

```
python build_exe.py
```

What the script does:

1. Installs/updates `pyinstaller` and `tkinterdnd2` (the drag-and-drop support).
2. Copies `ctrtool.exe` / `makerom.exe` (prefixed names like `abc123-ctrtool.exe` are also found) into a temporary folder.
3. Runs PyInstaller in `--onefile --windowed` mode, collecting `tkinterdnd2` and embedding the tools.
4. Removes the temporary folders and leaves **`3DS_RAM_Unlock.exe`** in the same folder as `build_exe.py`.

A full log is written to `build_log.txt`. If a build fails, the last lines of the error are printed on screen.

Notes:

- Do **not** run it from `C:\Windows\system32` (for example from an administrator terminal opened there). PyInstaller refuses to run in that folder. The script now changes to its own folder automatically, but opening the terminal in the right folder is still the cleanest option.
- Some antivirus programs flag or delete PyInstaller `--onefile` executables. If `3DS_RAM_Unlock.exe` does not appear, add the folder to your antivirus exclusions and build again.
- If `tkinterdnd2` is not available, the program still works; you just click to choose files instead of dragging them.

---

## How the patch works

For readers who want the details. All offsets are from the start of the `.app` file, which is an NCCH container.

1. **Validation**
   - Bytes `0x100–0x103` must be `NCCH`.
   - The ExHeader size field at `0x180` must be `0x400`.
   - The ExHeader must be decrypted: either the *NoCrypto* flag (`0x04` in the flags byte at `0x18F`) is set, or the first bytes of the ExHeader (the application name) are readable text.
2. **Mode fields.** For each of the two base offsets `0x400` and `0x800` (the ARM11 local-system-capabilities block in the ExHeader and its counterpart in the access descriptor limits):
   - byte `base + 0x0E`: high nibble ← Old 3DS mode (`3`), low nibble preserved
   - byte `base + 0x0D`: low nibble ← New 3DS mode (`1`), high nibble preserved
3. **Hash.** The SHA-256 of the first `0x400` bytes of the ExHeader (file range `0x200–0x5FF`) is written to the NCCH header at `0x160–0x17F`.
4. **Write.** The file is copied to the output folder and only the first `0xA00` bytes are rewritten. Large files are never loaded fully into memory.
5. **Verify.** The output header is read back; both mode values and the hash are checked.

The behavior was checked against the original `max.py` script: on the same input, the output is byte-for-byte identical.

---

## After patching: putting the file back into a CIA

This tool only produces the patched `.app`. To use it you still have to put it back into a CIA (for example by building a new CIA with `makerom` and your other content files) and install it on the console.

Important: editing the ExHeader makes the NCCH **signature invalid**. Your console must run custom firmware with **signature checks disabled** (for example Luma3DS with signature patches enabled) for the rebuilt title to launch.

---

## Troubleshooting

**The `.exe` does not appear after building**
Open a terminal in the project folder and run `python build_exe.py` again, then read the text on screen or `build_log.txt`. Typical causes: running from `C:\Windows\system32`, or antivirus deleting the file.

**"not a valid .app (NCCH header not found)"**
You picked the wrong file. Use the `0000.XXXXXXXX.app` from the mounted CIA drive, not the `.cia` or `.tmd`.

**"the .app is still encrypted"**
Decrypt it in GodMode9 (step 7 in the extraction guide) and use the decrypted copy.

**Drag & drop does nothing**
Click the box to choose the file instead. If it keeps happening, rebuild so `tkinterdnd2` is included. Also, dragging from a program running as administrator into a normal-user window is blocked by Windows; run both at the same privilege level.

**The patched game won't start**
Check that signature checks are disabled in your custom firmware, that the CIA was rebuilt correctly, and that the modes you chose are valid for the game.

---

## Project files

| File | Purpose |
|---|---|
| `RAM_Unlock_3DS.py` | The application (GUI and patch logic) |
| `build_exe.py` | Packs everything into a single `.exe` |
| `ctrtool.exe`, `makerom.exe` | Optional third-party tools, bundled into the `.exe` (`ctrtool` is used for an extra check; `makerom` is bundled but not used by the program yet) |
| `max.py` | The original command-line script this patch is based on |

---

## Disclaimer

This tool is intended for use with software you legally own, on hardware you own. It is provided as-is, with no warranty. Modifying game files and system settings can cause crashes or data loss; keep backups of your originals and your SD card contents. This project is not affiliated with or endorsed by Nintendo.
