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

Install the pinned project dependencies into the virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run the program

The virtual environment does not need to be activated. Run the current entry point directly:

```powershell
.\.venv\Scripts\python.exe main.py
```

Alternatively, activate the environment first:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python main.py
```

The execution-policy command only affects the current PowerShell window.

## Verify pygame

```powershell
.\.venv\Scripts\python.exe -c "import pygame; print(pygame.version.ver)"
```

## Project files

- `main.py` - current Python entry point and Pygame application.
- `docs/project_plan.md` - project behavior and development plan.
- `.venv` - local virtual environment; it should not be committed to source control.

