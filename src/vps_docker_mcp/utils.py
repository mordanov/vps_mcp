import re
import shlex

NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$")


def q(value: str) -> str:
    return shlex.quote(value)


def validate_name(value: str, label: str = "name") -> str:
    if not NAME_RE.fullmatch(value):
        raise ValueError(f"Invalid {label}: {value!r}")
    return value


def clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(int(value), hi))


def limit_output(output: str, max_chars: int) -> str:
    if len(output) <= max_chars:
        return output
    return output[:max_chars] + f"\n\n[Output truncated at {max_chars} characters]"
