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

Nothing in `make check` runs this. A gate that reaches the network to decide
whether it passes is a gate that fails when GitHub does.
"""

from __future__ import annotations

import hashlib
import platform
import shutil
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent

RELEASES = "https://github.com/open-telemetry/opentelemetry-collector-releases"
BINARY = "otelcol-contrib"

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


def main() -> int:
    version = pinned_version()
    asset = f"{BINARY}_{version}_{this_platform()}.tar.gz"
    expected = pinned_digests().get(asset)
    if expected is None:
        raise SystemExit(
            f"collector: {asset} has no line in collector/SHA256SUMS. "
            f"An unpinned binary is not a pinned Collector (SPEC.md §4.1)."
        )

    print(f"collector: {BINARY} {version} for {this_platform()}")
    with tempfile.TemporaryDirectory(prefix="zoo-collector-") as scratch:
        tarball = Path(scratch) / asset
        download(f"{RELEASES}/releases/download/v{version}/{asset}", tarball)
        actual = digest_of(tarball)
        if actual != expected:
            raise SystemExit(
                f"collector: REFUSING to unpack {asset}.\n"
                f"  expected sha256 {expected}  (collector/SHA256SUMS)\n"
                f"  downloaded       {actual}\n"
                f"The pinned digest is the release's own. These are not the "
                f"bytes that were pinned."
            )
        print(f"  sha256 {actual} matches collector/SHA256SUMS")
        binary = extract(tarball, HERE)

    print(f"collector: {binary} ready (gitignored -- the pin is the record)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
