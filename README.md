# odroid-go-firmware-app-manager
Application firmware manager for OtherCrashOverride/odroid-go-firmware

# Features
* Downloads and installs the latest, or specific, app firmware release from respective GitHub repositories
* Manages app firmware dependencies
* Downloads and installs the current romart archive
* If you already have an SD card setup for ODroid Go, it will keep your existing data and roms by default. In this case, it will only update the app firmwares.

# Prerequisites
* Python 3+ (tested with 3.7)
* SD card with a FAT32 filesystem and at least 512MB of free space
* Install OtherCrashOverride/odroid-go-firmware to your ODroid Go ([Device firmware instructions](https://wiki.odroid.com/odroid_go/firmware_update))
  * Release [20180727](https://github.com/OtherCrashOverride/odroid-go-firmware/releases/tag/20180727) is currently recommended (as of 23-Aug-2018)
* ODroid Go application firmware GitHub repositories must release their app as a compatibile .fw file.
* BIOS files
  * ColecoVision: BIOS.col
  * Commodore 64: 1541 ROM, Basic ROM, Char ROM, Kernal ROM
  * MSX : DISK.ROM, MSX2.ROM, MSX2EXT.ROM

# Instructions
1. Move odroid\_go\_app_manager.py to the root directory of your SD card
2. Optional: By default, all currently supported apps will be installed. Modify odroid\_go_apps.json to include or exclude apps.
3. Optional: Some emulators require BIOS files. If BIOS files are not already in the appropriate directories, put the BIOS files in the root directory of your SD card.
4. Open a command line or terminal, change the working directory to your SD card
5. Run python odroid_go_app_manager.py

# Supported app firmware repositories
* mad-ady/doom-odroid-go
* OtherCrashOverride/doom-odroid-go
* OtherCrashOverride/go-play
* OtherCrashOverride/MicroPython_ESP32_psRAM_LoBo-odroid-go
* OtherCrashOverride/prosystem-odroid-go
* OtherCrashOverride/stella-odroid-go
* Schuemi/c64-go
* Schuemi/fMSX-go

# Disclamer
* I have no association with Hardkernel, ODroid, or referenced repositories
* Use at your own risk. The script is nondestructive by default, but I take no responsibility.
