#!/usr/bin/env sh
# Downloads everything in the `documents` section of reference/documents.yaml.
# The `links` section lists web pages kept for reference only and is never fetched.
# Files already present in reference/ are not re-downloaded, so this is safe to
# re-run; their sha256 is still checked (a fraction of a second), and a mismatch
# fails without touching the file.
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
manifest="$repo_root/reference/documents.yaml"
dest_dir="$repo_root/reference"

[ -f "$manifest" ] || { echo "manifest not found: $manifest" >&2; exit 1; }
mkdir -p "$dest_dir"

# Prints the file's sha256 if it differs from the expected one (empty = no pin).
sha_mismatch() {
    [ -n "$2" ] || return 1
    actual=$(shasum -a 256 "$1" | cut -d' ' -f1)
    [ "$actual" != "$2" ] && echo "$actual"
}

downloaded=0
skipped=0
failed=0

# Tab-separated so filenames containing spaces survive the read. Routed through a
# temp file rather than a pipe, so the counters below stay in this shell.
list=$(mktemp)
trap 'rm -f "$list"' EXIT
# Only the `documents` section is fetched; `links` is reference-only by design.
yq -r '(.documents // [])[] | [.filename, .url, .sha256 // ""] | @tsv' "$manifest" > "$list" ||
    { echo "could not parse $manifest" >&2; exit 1; }

while IFS="$(printf '\t')" read -r filename url sha256; do
    [ -n "$filename" ] || continue
    target="$dest_dir/$filename"

    if [ -f "$target" ]; then
        if actual=$(sha_mismatch "$target" "$sha256"); then
            echo "  FAILED: reference/$filename has sha256 $actual, documents.yaml expects $sha256" >&2
            echo "          (left in place: a new ILR version to adopt, or a bad copy to delete)" >&2
            failed=$((failed + 1))
            continue
        fi
        echo "skip     $filename (already present)"
        skipped=$((skipped + 1))
        continue
    fi

    echo "download $filename"
    tmp="$target.part"
    # Download to a temp file and validate before moving into place, so a 404
    # error page never lands under the real name and get cached as "present".
    if ! curl -fSL --retry 2 --retry-delay 2 -o "$tmp" "$url"; then
        echo "  FAILED: could not fetch $url" >&2
        rm -f "$tmp"
        failed=$((failed + 1))
        continue
    fi

    if [ ! -s "$tmp" ] || [ "$(dd if="$tmp" bs=1 count=4 2>/dev/null)" != "%PDF" ]; then
        echo "  FAILED: $url did not return a PDF" >&2
        rm -f "$tmp"
        failed=$((failed + 1))
        continue
    fi

    # The pipeline is validated against these exact bytes; a re-upload under the
    # same URL must fail loudly, not quietly change what data/ is built from.
    if actual=$(sha_mismatch "$tmp" "$sha256"); then
        echo "  FAILED: $url has sha256 $actual, documents.yaml expects $sha256" >&2
        rm -f "$tmp"
        failed=$((failed + 1))
        continue
    fi

    mv "$tmp" "$target"
    downloaded=$((downloaded + 1))
done < "$list"

echo "$downloaded downloaded, $skipped already present, $failed failed"
[ "$failed" -eq 0 ] || exit 1
