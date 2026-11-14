# Draw With Your Voice

A Python project exploring sound-driven drawing and cymatic plate simulations.

## Requirements

- Windows PowerShell
- Python 3.12 (64-bit)
- `pygame 2.6.1`

Python 3.14 is installed on the system, but this project uses Python 3.12 because it is compatible with the current pygame installation.

## Replicate the environment

From the project directory, confirm that Python 3.12 is available:

```powershell
py -3.12 --version
```

Create the virtual environment:

```powershell
py -3.12 -m venv .venv
```

Install pygame into the virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install pygame==2.6.1
```

## Run the program

The virtual environment does not need to be activated. Run the current entry point directly:

```powershell
.\.venv\Scripts\python.exe hello_world.py
```

Alternatively, activate the environment first:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python hello_world.py
```

The execution-policy command only affects the current PowerShell window.

## Verify pygame

```powershell
.\.venv\Scripts\python.exe -c "import pygame; print(pygame.version.ver)"
```

## Project files

- `hello_world.py` - current Python entry point.
- `idea.md` - project concept and development notes.
- `.venv` - local virtual environment; it should not be committed to source control.

