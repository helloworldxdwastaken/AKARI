# AKARI #
My personal Spotify Assistant to be able to play without opening Spotify 
It uses Spotify API to avoid calling the Spotify App to the front and disrupting your game 


# Installation#
1- install requirements.txt with the next command ```pip install -r requirements.txt```

2- install Spotify APP https://www.spotify.com/us/download

3- Open Spotify on the device u want to control (ex: PC, Mobile)
  - Bot will list the devices that are open and will play there
  - 
4- Set Up Spotify API Credentials
 - Create a Spotify Developer Account:
 - [Go to Spotify Developer Dashboard.](https://developer.spotify.com/dashboard)
 - Log in with your Spotify account and create a new application.
 - Get Your Client ID and Client Secret and paste it the bot
 - 
Enjoy!


# Building a Standalone Executable for Akari Bot

This guide provides step-by-step instructions to create a standalone executable (`.exe`) for the `akari.py` script using **PyInstaller**. This executable can be run on Windows machines without requiring a Python installation.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Setting Up the Virtual Environment](#setting-up-the-virtual-environment)
3. [Installing Dependencies](#installing-dependencies)
4. [Building the Executable](#building-the-executable)
5. [Testing the Executable](#testing-the-executable)
6. [Troubleshooting](#troubleshooting)
7. [Additional Tips](#additional-tips)

---

## Prerequisites

Before you begin, ensure you have the following installed on your system:

- **Python 3.10.6**: Ensure Python is installed and added to your system's PATH.
- **PyInstaller**: A tool to convert Python scripts into standalone executables.
- **Git**: For version control (optional, but recommended).

## Setting Up the Virtual Environment

Creating a virtual environment helps manage dependencies and isolate your project.

1. **Navigate to Your Project Directory**

   Open **PowerShell** or **Command Prompt** and navigate to your project root directory:

   ```powershell
   cd C:\Users\username\Downloads\AKARI-main\AKARI-main\

2- Create a Virtual Environment
```python -m venv akari_env```
3- Activate the Virtual Environment
`Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\akari_env\Scripts\Activate.ps1
`
Installing Dependencies
Ensure all necessary Python packages are installed within the virtual environment.

Upgrade pip

powershell
`pip install --upgrade pip`


Install Required Packages
powershell
`pip install spotipy speechrecognition pyaudio inquirer pynput cryptography readchar`

Handling pyaudio Installation on Windows:
If you encounter issues installing pyaudio via pip, follow these steps:

1- Download the Appropriate Wheel File:

Visit Unofficial Windows Binaries for Python Extension Packages and download the .whl file matching your Python version and system architecture (e.g., PyAudio‑0.2.13‑cp310‑cp310‑win_amd64.whl for Python 3.10, 64-bit).

Install the Wheel File:

powershell

`pip install path\to\PyAudio‑0.2.13‑cp310‑cp310‑win_amd64.whl`

Replace path\to\ with the actual path where you downloaded the wheel file.

Building the Executable
With all dependencies installed, you can now build the standalone executable using PyInstaller.

Ensure You Are in the Project Root Directory
powershell
`cd C:\Users\Tokyo\Downloads\AKARI-main\AKARI-main\`

Clean Previous Builds (Optional but Recommended)
Remove any existing build, dist folders and akari.spec file to avoid conflicts.
powershell
Copy code
`Remove-Item -Recurse -Force .\build
Remove-Item -Recurse -Force .\dist
Remove-Item -Force .\akari.spec`
Run PyInstaller with the Appropriate Options

powershell
`
pyinstaller --onefile akari.py --icon=icon.ico --collect-all readchar --hidden-import=inquirer --hidden-import=spotipy --hidden-import=pynput --hidden-import=cryptography --hidden-import=speech_recognition --name akari --specpath .`

Explanation of Options:

--onefile: Packages everything into a single executable.
--icon=icon.ico: Sets a custom icon for the executable. Ensure icon.ico is in the project root.
--collect-all readchar: Includes all data and dependencies related to the readchar package.
--hidden-import=...: Specifies additional modules that PyInstaller might not detect automatically.
--name akari: Names the executable akari.exe.
--specpath .: Places the spec file in the current directory.
Note: Make sure to include all necessary hidden imports to prevent runtime errors.
