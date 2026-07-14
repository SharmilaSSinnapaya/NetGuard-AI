"""Download NSL-KDD train/test files into data/raw/."""

from __future__ import annotations

import sys
from pathlib import Path

import requests

# Ensure `src/` is importable when running as a script
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from netguard.config import get_settings

# Public mirrors of the NSL-KDD dataset (CSV/TXT, no header row).
# Primary: widely used GitHub mirror of the UNB NSL-KDD release.
DEFAULT_URLS: dict[str, str] = {
    "KDDTrain+.txt": (
        "https://raw.githubusercontent.com/defcom17/NSL_KDD/master/KDDTrain%2B.txt"
    ),
    "KDDTest+.txt": (
        "https://raw.githubusercontent.com/defcom17/NSL_KDD/master/KDDTest%2B.txt"
    ),
}

# Fallback CSV mirrors (same content; we still save as .txt names from config)
FALLBACK_URLS: dict[str, str] = {
    "KDDTrain+.txt": (
        "https://raw.githubusercontent.com/defcom17/NSL_KDD/master/KDDTrain%2B.csv"
    ),
    "KDDTest+.txt": (
        "https://raw.githubusercontent.com/defcom17/NSL_KDD/master/KDDTest%2B.csv"
    ),
}


def download_file(url: str, destination: Path, timeout: int = 120) -> None:
    """Stream a remote file to disk; raise on HTTP errors."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=timeout) as response:
        response.raise_for_status()
        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    handle.write(chunk)


def _candidate_urls(filename: str, settings_urls: dict[str, str]) -> list[str]:
    """Ordered URL candidates: config override, then defaults, then CSV fallback."""
    ordered: list[str] = []
    if filename in settings_urls:
        ordered.append(settings_urls[filename])
    if filename in DEFAULT_URLS:
        ordered.append(DEFAULT_URLS[filename])
    if filename in FALLBACK_URLS:
        ordered.append(FALLBACK_URLS[filename])
    # Preserve order while removing duplicates
    deduped: list[str] = []
    for url in ordered:
        if url not in deduped:
            deduped.append(url)
    return deduped


def download_nsl_kdd(force: bool = False) -> list[Path]:
    """
    Download KDDTrain+.txt and KDDTest+.txt into the configured raw data dir.

    Skips files that already exist unless force=True.
    Tries config URLs, then the .txt mirror, then the .csv fallback.
    """
    settings = get_settings()
    raw_dir = settings.resolve_path(settings.paths.raw_data_dir)
    targets = [settings.dataset.train_file, settings.dataset.test_file]
    saved: list[Path] = []

    for filename in targets:
        dest = raw_dir / filename
        if dest.exists() and not force:
            print(f"[skip] {dest} already exists (use --force to re-download)")
            saved.append(dest)
            continue

        urls = _candidate_urls(filename, settings.dataset.download_urls)
        if not urls:
            raise RuntimeError(f"No download URL configured for {filename}")

        last_error: Exception | None = None
        for url in urls:
            try:
                print(f"[download] {filename} <- {url}")
                download_file(url, dest)
                size_mb = dest.stat().st_size / (1024 * 1024)
                print(f"[ok] saved {dest} ({size_mb:.2f} MiB)")
                saved.append(dest)
                last_error = None
                break
            except Exception as exc:  # noqa: BLE001 — report and try fallback
                last_error = exc
                print(f"[warn] failed: {exc}")
                if dest.exists():
                    dest.unlink()

        if last_error is not None:
            raise RuntimeError(
                f"Could not download {filename} from any mirror"
            ) from last_error

    return saved


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    force = "--force" in argv
    paths = download_nsl_kdd(force=force)
    print(f"[done] {len(paths)} file(s) ready in data/raw/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
