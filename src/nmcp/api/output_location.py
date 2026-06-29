import os
from dataclasses import dataclass

from cloudfiles import paths

_PRECOMPUTED_PREFIX = "precomputed://"


@dataclass(frozen=True)
class OutputLocation:
    cloudpath: str
    """Protocol-only location to write to: no `precomputed://` prefix or `|precomputed:` suffix, no trailing slash."""
    protocol: str
    host: str | None
    bucket: str | None
    path: str
    """Comparison path: no trailing slash, and symlinks resolved for `file` locations."""

    def is_at_or_under(self, other: "OutputLocation") -> bool:
        if (self.protocol, self.host, self.bucket) != (other.protocol, other.host, other.bucket):
            return False

        if self.protocol == "file":
            # Root-aware where a string-prefix test is not: a protected "/" covers every local path.
            return os.path.commonpath([self.path, other.path]) == other.path

        return other.path == "" or self.path == other.path or self.path.startswith(f"{other.path}/")


def parse_output_location(location: str, require_protocol: bool = True) -> OutputLocation:
    """
    Parse a cloud-files location the way CloudFiles itself resolves it, so that comparisons see the destination that
    will actually be written to rather than the caller's spelling. Raises `ValueError` for anything unusable.
    """
    stripped = _remove_precomputed_prefix(location.strip())

    if len(stripped) == 0:
        raise ValueError("the output location is empty")

    try:
        fmt, protocol, _, _, _ = paths.extract_format_protocol(stripped, allow_defaults=False)
        normalized = paths.normalize(stripped)
        extracted = paths.extract(normalized)
    except Exception as ex:
        raise ValueError(f"unsupported location '{location}': {ex}") from ex

    if fmt not in (None, "precomputed"):
        raise ValueError(f"unsupported format '{fmt}' in location '{location}'; only precomputed is supported")

    # cloud-files treats an unknown or mis-cased scheme, or a bare path, as a path relative to the working directory.
    if require_protocol and protocol is None:
        raise ValueError(f"the location '{location}' has no recognized protocol (e.g. s3://, gs://, file://)")

    if extracted.protocol == "file":
        comparison_path = os.path.realpath(extracted.path)
    else:
        comparison_path = extracted.path.rstrip("/")

    return OutputLocation(_to_cloudpath(normalized), extracted.protocol, extracted.host, extracted.bucket,
                          comparison_path)


def _remove_precomputed_prefix(location: str) -> str:
    if location.startswith(_PRECOMPUTED_PREFIX):
        return location[len(_PRECOMPUTED_PREFIX):]

    return location


def _to_cloudpath(normalized: str) -> str:
    # `normalize` turns the `…|precomputed:` tail spelling into a `precomputed://` prefix, and the generation code
    # adds its own, so it is removed here as well as from the raw input.
    scheme, separator, rest = _remove_precomputed_prefix(normalized).partition("://")

    trimmed = rest.rstrip("/")

    if len(trimmed) == 0 and rest.startswith("/"):
        trimmed = "/"

    return f"{scheme}{separator}{trimmed}"
