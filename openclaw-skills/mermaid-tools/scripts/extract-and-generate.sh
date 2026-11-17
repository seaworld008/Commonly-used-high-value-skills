#!/bin/bash
# Enhanced Mermaid diagram extraction and PNG generation script
# Extracts diagrams from markdown and numbers them sequentially
#
# Usage: ./extract-and-generate.sh <markdown_file> [output_directory]
# Example: ./extract-and-generate.sh "~/workspace/document.md" "~/workspace/diagrams"

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/puppeteer-config.json"
EXTRACTOR_SCRIPT="$SCRIPT_DIR/extract_diagrams.py"

# Parse arguments
if [ $# -lt 1 ]; then
    echo "Usage: $0 <markdown_file> [output_directory]"
    echo "Example: $0 '~/workspace/document.md' '~/workspace/diagrams'"
    exit 1
fi

MARKDOWN_FILE="$1"
OUTPUT_DIR="${2:-$(dirname "$MARKDOWN_FILE")/diagrams}"

echo "=== Enhanced Mermaid Diagram Processor ==="
echo "Source markdown: $MARKDOWN_FILE" 
echo "Output directory: $OUTPUT_DIR"
echo

# Validate inputs
if [ ! -f "$MARKDOWN_FILE" ]; then
    echo "ERROR: Markdown file not found: $MARKDOWN_FILE"
    exit 1
fi

# Create output directory if it doesn't exist
mkdir -p -- "$OUTPUT_DIR"
OUTPUT_DIR="$(cd -- "$OUTPUT_DIR" && pwd)"

# Extraction is isolated from published files. A successful empty manifest needs
# no renderer, and a failed read/extraction must never fall back to old inputs.
batch=$(mktemp -d "${TMPDIR:-$OUTPUT_DIR}/mermaid-batch.XXXXXXXX")
trap 'rm -rf -- "$batch"' EXIT
manifest="$batch/inputs"
source_stage="$batch/source"
echo "Extracting Mermaid diagrams from markdown..."
if ! python3 "$EXTRACTOR_SCRIPT" --manifest "$manifest" -- "$MARKDOWN_FILE" "$source_stage"; then
    echo "ERROR: Failed to extract diagrams from markdown" >&2
    exit 1
fi
mmd_files=()
while IFS= read -r -d '' mmd_file; do
    mmd_files+=("$mmd_file")
done < "$manifest"
if [ ${#mmd_files[@]} -eq 0 ]; then
    echo "No Mermaid diagrams extracted from this document"
    exit 0
fi

# Configuration
CHROME_PATH="${PUPPETEER_EXECUTABLE_PATH:-/usr/bin/google-chrome-stable}"

# Check dependencies
echo "Checking dependencies..."
if ! command -v mmdc &> /dev/null; then
    echo "ERROR: @mermaid-js/mermaid-cli not installed"
    echo "Install with: npm install -g @mermaid-js/mermaid-cli"
    exit 1
fi

if [ ! -f "$CHROME_PATH" ]; then
    echo "ERROR: Google Chrome not found at $CHROME_PATH"
    echo "Install Chrome and dependencies with the setup commands"
    exit 1
fi

if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: Puppeteer config not found: $CONFIG_FILE"
    exit 1
fi

if [ ! -f "$EXTRACTOR_SCRIPT" ]; then
    echo "ERROR: Python extractor script not found: $EXTRACTOR_SCRIPT"
    exit 1
fi

echo "✅ Dependencies verified"
echo

# Now generate PNGs using the existing generation logic
echo "Generating PNG files..."
cd -- "$source_stage"

# Default dimensions - can be overridden with environment variables  
DEFAULT_WIDTH="${MERMAID_WIDTH:-1200}"
DEFAULT_HEIGHT="${MERMAID_HEIGHT:-800}"
SCALE_FACTOR="${MERMAID_SCALE:-2}"

echo "Found ${#mmd_files[@]} Mermaid diagram(s) to process"
echo

failed=()
failed_inputs=()
record_failure() {
    failed+=("$1")
    failed_inputs+=("$mmd_file")
}
# A PNG header can survive an interrupted render. Check chunk boundaries and CRCs
# through the final IEND using the Python already required by the extractor.
valid_png() {
    test -f "$1" && test -s "$1" || return 1
    python3 - "$1" <<'PY'
import mmap
import struct
import sys
import zlib

with open(sys.argv[1], "rb") as src, mmap.mmap(src.fileno(), 0, access=mmap.ACCESS_READ) as png:
    if png[:16] != b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR":
        sys.exit(1)
    offset = 8
    has_data = False
    while offset + 12 <= len(png):
        size, kind = struct.unpack_from(">I4s", png, offset)
        end = offset + 8 + size
        if end + 4 > len(png):
            break
        checksum, = struct.unpack_from(">I", png, end)
        if zlib.crc32(memoryview(png)[offset + 4:end]) != checksum:
            break
        offset = end + 4
        if kind == b"IDAT" and size:
            has_data = True
        if kind == b"IEND":
            sys.exit(0 if has_data and size == 0 and offset == len(png) else 1)
sys.exit(1)
PY
}

# Check only files produced by this run, even if a previous batch left PNGs here.
stage="$batch/png"
mkdir "$stage"
for mmd_file in "${mmd_files[@]}"; do
    if [ ! -f "$mmd_file" ]; then
        record_failure "${mmd_file%.mmd}.png (missing diagram input)"
        continue
    fi
    
    # Extract filename without extension
    diagram="${mmd_file%.mmd}"
    
    # Use smart defaults based on diagram content or filename patterns
    width="$DEFAULT_WIDTH"
    height="$DEFAULT_HEIGHT"
    
    # Smart sizing based on filename patterns
    if [[ "$diagram" =~ timeline|gantt ]]; then
        width=$((DEFAULT_WIDTH * 2))  # Wider for timelines
        height=$((DEFAULT_HEIGHT / 2))  # Shorter for timelines
    elif [[ "$diagram" =~ architecture|system ]]; then
        width=$((DEFAULT_WIDTH * 2))  # Larger for complex diagrams
        height=$((DEFAULT_HEIGHT * 2))
    elif [[ "$diagram" =~ caching ]]; then
        width=$((DEFAULT_WIDTH * 2))  # Larger for caching flowcharts
        height=$((DEFAULT_HEIGHT * 2))
    elif [[ "$diagram" =~ monitoring|workflow|sequence|api ]]; then
        width=$((DEFAULT_WIDTH * 2))  # Wider for workflows and sequences
        height="$DEFAULT_HEIGHT"
    fi
    
    echo "Generating $diagram.png (${width}x${height}, scale: ${SCALE_FACTOR}x)..."
    if ! PUPPETEER_EXECUTABLE_PATH="$CHROME_PATH" mmdc \
        -i "$mmd_file" \
        -o "$stage/$diagram.png" \
        --puppeteerConfigFile "$CONFIG_FILE" \
        -w "$width" \
        -H "$height" \
        -s "$SCALE_FACTOR"; then
        record_failure "$diagram.png (generation failed)"
        continue
    fi
    
    # Validate PNG
    if valid_png "$stage/$diagram.png"; then
        dimensions_actual=unknown
        if command -v identify >/dev/null && ! dimensions_actual=$(identify -format "%wx%h" "$stage/$diagram.png" 2>/dev/null); then
            record_failure "$diagram.png (PNG inspection failed)"
            continue
        fi
        if ! size=$(python3 -c 'import os, sys; print(os.path.getsize(sys.argv[1]))' "$stage/$diagram.png"); then
            record_failure "$diagram.png (could not inspect staged PNG)"
            continue
        fi
        if ! python3 "$EXTRACTOR_SCRIPT" --publish-png "$stage/$diagram.png" -- "$source_stage/$mmd_file" "$OUTPUT_DIR"; then
            record_failure "$diagram.png (could not publish source/PNG pair)"
            continue
        fi
        echo "  ✅ Validated PNG (${size} bytes, ${dimensions_actual})"
    else
        record_failure "$diagram.png (missing or invalid PNG)"
    fi
    echo
done

echo "=== Generation Complete ==="
if [ "${#failed[@]}" -gt 0 ]; then
    printf 'Failed PNGs (%d):\n' "${#failed[@]}" >&2
    printf '  %s\n' "${failed[@]}" >&2
    # Failed inputs are diagnostic artifacts in a separate, unique directory;
    # they never take the names of a previously published pair.
    if diagnostics=$(mktemp -d "$OUTPUT_DIR/failed-mermaid.XXXXXXXX"); then
        for mmd_file in "${failed_inputs[@]}"; do
            if ! cp -- "$source_stage/$mmd_file" "$diagnostics/$mmd_file"; then
                echo "ERROR: Could not retain failed input: $mmd_file" >&2
            fi
        done
        echo "Failed inputs saved separately: $diagnostics" >&2
    else
        echo "ERROR: Could not create failed-input diagnostic directory" >&2
    fi
    exit 1
fi
echo "All PNG diagrams generated and validated successfully!"
echo

echo "Generated files (in sequence order):"
for mmd_file in "${mmd_files[@]}"; do
    printf '  %s\n' "${mmd_file%.mmd}.png"
done
