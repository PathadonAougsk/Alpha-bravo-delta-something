Git but Python. Supports `init`,
`add`, `commit`, `log`, `branch`, `checkout`, `merge` (with real three-way
conflict detection), and `push` (to a local folder acting as a remote).

This README covers turning `minigit.py` into a real command — so you can
type `minigit` instead of `python3 minigit.py` — on macOS, Linux, and Windows.

**Requirement on every platform:** Python 3 installed and on your `PATH`.
Check with:

```sh
python3 --version   # macOS / Linux
python --version     # Windows
```

---

## macOS / Linux

### Option 1: Put it on your PATH (recommended)

```sh
# 1. Rename it (drop the .py) and make it executable
mv minigit.py minigit
chmod +x minigit

# 2. Move it into a folder that's on your PATH
mkdir -p ~/bin
mv minigit ~/bin/

# 3. Make sure ~/bin is on PATH — add this line to ~/.bashrc or ~/.zshrc
#    (whichever your shell uses) if it's not already there:
export PATH="$HOME/bin:$PATH"

# 4. Reload your shell config
source ~/.bashrc    # or: source ~/.zshrc
```

Now from any directory:

```sh
minigit init
minigit add file.txt
minigit commit -m "message"
```

This works because the script starts with `#!/usr/bin/env python3` — once
it's executable and on your `PATH`, the shell runs it directly without you
typing `python3` at all.

### Option 2: Shell alias (quick, but only works in interactive shells)

```sh
echo 'alias minigit="python3 /full/path/to/minigit.py"' >> ~/.bashrc
source ~/.bashrc
```

Simpler to set up, but it won't work inside non-interactive scripts, and you
have to keep the full path correct if you move the file.

### Option 3: pip-installable package (most "real", works on any machine)

If you want `minigit` to install like a normal CLI tool (`pipx install .`),
turn it into a proper package. In the same folder as `minigit.py`:

**`pyproject.toml`**

```toml
[project]
name = "minigit"
version = "0.1.0"
description = "A tiny Git-like version control system"
requires-python = ">=3.8"

[project.scripts]
minigit = "minigit:main"

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
```

Then install it:

```sh
pip install --user .
# or, if you use pipx (recommended for CLI tools):
pipx install .
```

This creates a real `minigit` executable wired to the `main()` function in
`minigit.py`, placed automatically on your `PATH`. No manual `PATH` editing
needed.

---

## Windows

Windows doesn't use executable bits or shebang lines, so the setup differs
a bit. Pick one:

### Option 1: pip-installable package (recommended — works the same as macOS/Linux)

Same `pyproject.toml` as above. From PowerShell or Command Prompt, in the
folder with `minigit.py`:

```powershell
pip install --user .
```

This adds a `minigit.exe` wrapper to your Python Scripts folder (something
like `C:\Users\<you>\AppData\Roaming\Python\Python3x\Scripts`) and that
folder is normally already on `PATH` if Python was installed with the
"Add Python to PATH" option checked. Then:

```powershell
minigit init
minigit add file.txt
minigit commit -m "message"
```

### Option 2: A `.bat` wrapper on PATH

If you don't want to package it, create a small batch file that forwards to
the script:

1. Create a folder for your personal commands, e.g. `C:\tools\`.
2. Put `minigit.py` in that folder.
3. In the same folder, create **`minigit.bat`** with:

   ```bat
   @echo off
   python "%~dp0minigit.py" %*
   ```

   (`%~dp0` resolves to the folder the `.bat` file is in, so this works
   regardless of where `C:\tools` actually is.)

4. Add `C:\tools` to your `PATH`:
   - Search **"Environment Variables"** in the Start menu →
     **Edit the system environment variables** → **Environment Variables...**
   - Under **User variables**, select `Path` → **Edit** → **New** →
     add `C:\tools`.
   - Click OK on everything, then **open a new terminal** (PowerShell or
     Command Prompt) so it picks up the change.

Now `minigit` works from any directory, any terminal.

### Option 3: PowerShell function (quick, current user only)

Add this to your PowerShell profile (`notepad $PROFILE` to open it):

```powershell
function minigit { python "C:\full\path\to\minigit.py" @args }
```

Restart PowerShell, then `minigit init` etc. will work — but only inside
PowerShell, not Command Prompt or other shells.

---

## Verifying it worked (any platform)

```sh
minigit init
echo "hello" > file.txt
minigit add file.txt
minigit commit -m "first commit"
minigit log
```

If `init` prints `Initialized empty minigit repository in .minigit/`,
the command is wired up correctly.

# Uninstallation
## macOS / Linux

If you used Option 1 (PATH + ~/bin):

```sh
rm ~/bin/minigit
```

The export PATH="$HOME/bin:$PATH" line in ~/.bashrc/~/.zshrc can stay (harmless if the folder’s empty) or you can delete that line too.

If you used Option 2 (alias):

```sh
sed -i '/alias minigit=/d' ~/.bashrc   # or ~/.zshrc
source ~/.bashrc
```

Or just open the file and delete the line manually.

If you used Option 3 (pip/pipx package):

```sh
pipx uninstall minigit
# or, if installed with pip:
pip uninstall minigit
```
## Windows

If you used Option 1 (pip package):

```powershell
pip uninstall minigit
```

If you used Option 2 (.bat wrapper):

```powershell
del C:\tools\minigit.bat
del C:\tools\minigit.py
```

Then remove C:\tools from PATH if you added it just for this: Environment Variables → edit Path under User variables → select the entry → Remove.

If you used Option 3 (PowerShell function):
Open your profile with notepad $PROFILE and delete the function minigit { ... } line, then restart PowerShell.

Checking it’s gone (any platform)
```sh
minigit
``

Should give “command not found” (or PowerShell’s equivalent). If it still runs, something’s still on PATH — run which minigit (macOS/Linux) or where.exe minigit (Windows) to find the leftover file.

One more thing worth remembering: none of this touches any .minigit/ folders you created inside actual projects while testing. Those are just local data, so delete them per-project with rm -rf .minigit (or rmdir /s .minigit on Windows) if you want to clean those up too.