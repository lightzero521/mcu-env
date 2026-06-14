"""Generate and install shell profile snippets for mcuenv-on."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

MARKER_BEGIN = "# >>> mcuenv shell init >>>"
MARKER_END = "# <<< mcuenv shell init <<<"


def _ps1_root(root: Path) -> str:
    return str(root).replace("'", "''")


def _bash_root(root: Path) -> str:
    return str(root).replace('"', '\\"')


def generate_ps1_snippet(root: Path) -> str:
    export_script = _ps1_root(root / "export.ps1")
    return f"""{MARKER_BEGIN}
function global:mcuenv-on {{
    . '{export_script}'
}}
{MARKER_END}
"""


def generate_bash_snippet(root: Path) -> str:
    export_script = _bash_root(root / "export.sh")
    return f"""{MARKER_BEGIN}
mcuenv-on() {{
  source "{export_script}"
}}
{MARKER_END}
"""


def _query_powershell_profile(executable: str) -> Path | None:
    try:
        completed = subprocess.run(
            [executable, "-NoProfile", "-Command", "$PROFILE"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None

    profile = completed.stdout.strip()
    if profile and completed.returncode == 0:
        return Path(profile)
    return None


def ps1_profile_paths() -> list[Path]:
    """Return PowerShell profile paths for all installed hosts (5.1 and 7+)."""
    paths: list[Path] = []
    seen: set[str] = set()

    for executable in ("powershell", "pwsh"):
        profile = _query_powershell_profile(executable)
        if profile is None:
            continue
        key = str(profile).casefold()
        if key in seen:
            continue
        seen.add(key)
        paths.append(profile)

    if paths:
        return paths

    docs = Path.home() / "Documents"
    for relative in (
        "WindowsPowerShell/Microsoft.PowerShell_profile.ps1",
        "PowerShell/Microsoft.PowerShell_profile.ps1",
    ):
        profile = docs / relative
        key = str(profile).casefold()
        if key in seen:
            continue
        seen.add(key)
        paths.append(profile)

    return paths


def default_profile_path(fmt: str) -> Path | None:
    if fmt in {"ps1", "powershell"}:
        profiles = ps1_profile_paths()
        return profiles[0] if profiles else None

    if fmt in {"bash", "sh"}:
        return Path.home() / ".bashrc"

    return None


def _replace_or_append(content: str, snippet: str) -> str:
    if MARKER_BEGIN in content and MARKER_END in content:
        before, rest = content.split(MARKER_BEGIN, 1)
        _, after = rest.split(MARKER_END, 1)
        return f"{before}{snippet}\n{after.lstrip()}"

    if content and not content.endswith("\n"):
        content += "\n"
    if content:
        content += "\n"
    return content + snippet + "\n"


def install_snippet(profile_path: Path, snippet: str) -> tuple[bool, str]:
    existing = ""
    if profile_path.is_file():
        existing = profile_path.read_text(encoding="utf-8")

    if MARKER_BEGIN in existing and MARKER_END in existing:
        updated = _replace_or_append(existing, snippet)
        action = "updated"
    elif MARKER_BEGIN in existing:
        return False, f"Incomplete mcuenv block in {profile_path}; fix it manually."

    else:
        updated = _replace_or_append(existing, snippet)
        action = "installed"

    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(updated, encoding="utf-8")
    return True, f"Shell helpers {action} in {profile_path}"


def run_shell_init(
    root: Path,
    *,
    fmt: str = "all",
    install: bool = False,
) -> int:
    formats: list[str]
    if fmt == "all":
        formats = ["ps1", "bash"]
    elif fmt in {"powershell", "sh"}:
        formats = ["ps1" if fmt == "powershell" else "bash"]
    else:
        formats = [fmt]

    snippets: dict[str, str] = {
        "ps1": generate_ps1_snippet(root),
        "bash": generate_bash_snippet(root),
    }

    if install:
        for shell_fmt in formats:
            if shell_fmt == "ps1":
                profiles = ps1_profile_paths()
            else:
                profile = default_profile_path(shell_fmt)
                profiles = [profile] if profile is not None else []

            if not profiles:
                print(f"Unable to determine profile path for {shell_fmt}.", file=sys.stderr)
                return 1

            for profile in profiles:
                ok, message = install_snippet(profile, snippets[shell_fmt])
                print(message)
                if not ok:
                    return 1
        print("Restart the terminal, then run: mcuenv-on")
        return 0

    if len(formats) == 1:
        print(snippets[formats[0]])
        return 0

    print("# PowerShell profile snippet")
    print(snippets["ps1"])
    print()
    print("# Bash profile snippet")
    print(snippets["bash"])
    return 0
