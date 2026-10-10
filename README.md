# Pygame Git mergetool

A minimal entry point that reads Git's merge files into memory and opens a blank
Pygame window. No conflict display, editing, or saving is implemented yet.

Install the dependency:

```sh
python -m pip install -r requirements.txt
```

Configure Git in the repository where you want to use the tool, replacing both
absolute paths below with your Python interpreter and this project's `main.py`:

```sh
git config merge.tool pygame
git config mergetool.pygame.cmd '"/absolute/path/to/python" "/absolute/path/to/main.py" "$BASE" "$LOCAL" "$REMOTE" "$MERGED"'
git config mergetool.pygame.trustExitCode true
```

Then run `git mergetool` during a merge conflict. Git passes four file paths:

- `BASE`: the common ancestor.
- `LOCAL`: the current branch (HEAD).
- `REMOTE`: the branch being merged, such as your feature branch.
- `MERGED`: the working file containing conflict markers.

The program reads all four files as bytes without modifying them. Closing the
window returns exit code 1 so Git does not treat the conflict as resolved.
