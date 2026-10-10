"""`make collector`: download the pinned Collector and check its sha256.

Deliberately **outside** `spanweave_zoo/`. This is the one thing in the
repository that fetches from the network, and the package's claim is that it
does not: the sink, the tee and the replayer open sockets only through the seams
`SPEC.md` names, and `urllib` has no business importing anywhere under
`spanweave_zoo/`. So the fetcher is a script beside the config it fetches a
binary for, run by `make collector` and by nothing else.

It reads `collector/VERSION` -- the only place the version is spelled -- builds
the asset name for this platform, downloads it, and **refuses to unpack
anything whose sha256 is not the digest on the matching line of
`collector/SHA256SUMS`** (`SPEC.md` §4.1). A platform with no line is a refusal
too: an unpinned binary is not a pinned Collector, and a capture labelled with a
version that was not the one that ran would be worse than one labelled with
nothing.

The archive it downloads is kept in `collector/.cache/` -- gitignored, like the
binary -- and a second run re-uses it instead of fetching 100 MB again, after
re-hashing it: **a cached archive whose digest is not the pin is refused
exactly as a downloaded one is.** The download writes `<asset>.part` and renames
it only once the digest matches, so an interrupted fetch never becomes the
cache. CI keys its cache on that same digest (`--print-pin`), which is why a
`VERSION` or `SHA256SUMS` change is a cache miss and a fresh download rather
than a stale hit.

Nothing in `make check` runs this. A gate that reaches the network to decide
whether it passes is a gate that fails when GitHub does.
"""

from __future__ import annotations

import hashlib
import platform
import shutil
import sys
import tarfile
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent

RELEASES = "https://github.com/open-telemetry/opentelemetry-collector-releases"
BINARY = "otelcol-contrib"

# Where the downloaded archive is kept between runs. Gitignored, like the
# binary: the pin is the record and the bytes are a download.
CACHE = HERE / ".cache"

# `uname -s` / `uname -m` as the release names them. Anything not in here has no
# line in SHA256SUMS either, and is refused rather than guessed at.
SYSTEMS = {"Linux": "linux", "Darwin": "darwin"}
MACHINES = {"x86_64": "amd64", "amd64": "amd64", "arm64": "arm64", "aarch64": "arm64"}


def pinned_version() -> str:
    return (HERE / "VERSION").read_text(encoding="utf-8").strip()


def pinned_digests() -> dict[str, str]:
    """`{asset: sha256}` from `SHA256SUMS`, comments and blank lines skipped."""
    digests: dict[str, str] = {}
    for line in (HERE / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        digest, _, asset = stripped.partition("  ")
        digests[asset.strip()] = digest.strip()
    return digests


def this_platform() -> str:
    system = platform.system()
    machine = platform.machine().lower()
    if system not in SYSTEMS or machine not in MACHINES:
        raise SystemExit(
            f"collector: no pinned Collector for {system}/{machine}. "
            f"SPEC.md §4.1: a platform with no line in collector/SHA256SUMS is "
            f"refused, not guessed at -- add the line from the release's own "
            f"{BINARY}_<version>_<os>_<arch>.tar.gz.sha256."
        )
    return f"{SYSTEMS[system]}_{MACHINES[machine]}"


def digest_of(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            sha.update(block)
    return sha.hexdigest()


def download(url: str, destination: Path) -> None:
    print(f"  fetching {url}")
    try:
        with (
            urllib.request.urlopen(url) as response,
            destination.open("wb") as handle,
        ):
            shutil.copyfileobj(response, handle)
    except urllib.error.URLError as unreachable:
        raise SystemExit(f"collector: cannot fetch {url}: {unreachable}") from None


def extract(tarball: Path, into: Path) -> Path:
    """Pull exactly `otelcol-contrib` out, by name, and nothing else."""
    with tarfile.open(tarball) as archive:
        member = archive.getmember(BINARY)
        if not member.isfile():
            raise SystemExit(f"collector: {BINARY} in the tarball is not a file")
        extracted = archive.extractfile(member)
        if extracted is None:
            raise SystemExit(f"collector: cannot read {BINARY} from the tarball")
        target = into / BINARY
        with extracted, target.open("wb") as handle:
            shutil.copyfileobj(extracted, handle)
    target.chmod(0o755)
    return target


def pinned_asset() -> tuple[str, str]:
    """`(asset, sha256)` for this platform. No line in `SHA256SUMS` is a refusal."""
    asset = f"{BINARY}_{pinned_version()}_{this_platform()}.tar.gz"
    expected = pinned_digests().get(asset)
    if expected is None:
        raise SystemExit(
            f"collector: {asset} has no line in collector/SHA256SUMS. "
            f"An unpinned binary is not a pinned Collector (SPEC.md §4.1)."
        )
    return asset, expected


def refuse(archive: Path, expected: str, actual: str, how: str) -> SystemExit:
    return SystemExit(
        f"collector: REFUSING to unpack {archive.name}.\n"
        f"  expected sha256 {expected}  (collector/SHA256SUMS)\n"
        f"  {how:<16}{actual}\n"
        f"The pinned digest is the release's own. These are not the bytes that "
        f"were pinned.\n"
        f"Delete {archive} and run `make collector` again to fetch them."
    )


def cached(archive: Path, expected: str) -> bool:
    """Is the pinned archive already on disk? A wrong digest is a refusal.

    Not "is there a file with the right name": the cache is re-hashed on every
    run, because a cache hit that trusted its own file name would be a way of
    running an unpinned Collector while `make collector` printed the pin
    (`SPEC.md` §4.1).
    """
    if not archive.is_file():
        return False
    actual = digest_of(archive)
    if actual != expected:
        raise refuse(archive, expected, actual, "cached")
    return True


def print_pin() -> int:
    """`asset=` and `sha256=` -- what CI keys its archive cache on.

    `KEY=value` lines, which is the `$GITHUB_OUTPUT` form, so the cache key
    names the digest that pins the bytes rather than a branch or a date
    (`.github/workflows/ci.yml`, the `collector` job). A `VERSION` or
    `SHA256SUMS` change is then a different key: a miss and a fresh download,
    never a stale hit.
    """
    asset, expected = pinned_asset()
    print(f"asset={asset}")
    print(f"sha256={expected}")
    return 0


def fetch_into_cache(asset: str, expected: str) -> Path:
    """Download the archive and put it in the cache once its digest matches.

    Written as `<asset>.part` and renamed only after the check, so an
    interrupted or truncated download is never mistaken for a cache hit by the
    next run.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    archive = CACHE / asset
    partial = CACHE / f"{asset}.part"
    download(f"{RELEASES}/releases/download/v{pinned_version()}/{asset}", partial)
    actual = digest_of(partial)
    if actual != expected:
        partial.unlink(missing_ok=True)
        raise refuse(archive, expected, actual, "downloaded")
    partial.replace(archive)
    return archive


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if arguments == ["--print-pin"]:
        return print_pin()
    if arguments:
        raise SystemExit(f"collector: usage: fetch.py [--print-pin] (got {arguments})")

    asset, expected = pinned_asset()
    print(f"collector: {BINARY} {pinned_version()} for {this_platform()}")
    archive = CACHE / asset
    if cached(archive, expected):
        print(f"  cached {archive}")
    else:
        archive = fetch_into_cache(asset, expected)
    print(f"  sha256 {expected} matches collector/SHA256SUMS")
    binary = extract(archive, HERE)

    print(f"collector: {binary} ready (gitignored -- the pin is the record)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
