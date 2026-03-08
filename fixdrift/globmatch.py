from __future__ import annotations

import fnmatch


def match_path(path: str, pattern: str) -> bool:
    path_parts = [p for p in path.strip("/").split("/") if p]
    pat_parts = [p for p in pattern.strip("/").split("/") if p]

    def rec(i: int, j: int) -> bool:
        if j >= len(pat_parts):
            return i >= len(path_parts)

        pat = pat_parts[j]
        if pat == "**":
            if rec(i, j + 1):
                return True
            return i < len(path_parts) and rec(i + 1, j)

        if i >= len(path_parts):
            return False

        if not fnmatch.fnmatchcase(path_parts[i], pat):
            return False
        return rec(i + 1, j + 1)

    return rec(0, 0)


def match_any(path: str, patterns: list[str]) -> bool:
    return any(match_path(path, p) for p in patterns)
