# Patch-to-unlock-RAM-on-the-3DS
Patch to unlock RAM on the 3DS for all 3DS games (you need the game's .cia file and an actual 3DS console)
HOW TO EXTRACT THE 0000.XXXXXXXX.app FROM ANY .CIA WITH GODMODE9

Copy your .cia file to the SD card of your 3DS (any folder).
Power on the console holding START to open GodMode9.
Go to [0:] SDCARD and highlight your .cia file. Press A.
Choose “Mount image to drive” (CIA image options).
A virtual drive opens (for example G:). Inside you will see several files: .tmd, .app, etc. The one you need is 0000.XXXXXXXX.app (index 0000). It is the game’s main content and usually the biggest file.
Highlight it and press Y (copy). Go to [0:] SDCARD / gm9 / out (or any folder) and press Y again → “Copy path here”.
If the .app is encrypted: highlight it, press A → “NCCH image options” → “Decrypt file (0:/gm9/out)”. Use the decrypted copy.
Turn the console off, take the SD card out and copy the .app to your PC.
Drag it onto this program. The patched file (name_max.app) is created in the same folder as this program.

Note: the patched .app has an invalid signature, so your console needs custom firmware with signature checks disabled (e.g. Luma3DS) to run it after you put it back into a CIA.
