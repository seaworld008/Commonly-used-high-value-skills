#!/usr/bin/env python3
"""
Enhanced transcript fixer wrapper with improved user experience.

Features:
- Custom output directory support
- Optional HTML diff opening with --auto-open
- API key supplied explicitly via GLM_API_KEY
- Progress feedback

CRITICAL FIX: Now uses secure API key handling (Critical-2)
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# CRITICAL FIX: Import path validation (Critical-5)
from utils.path_validator import PathValidator, PathValidationError, add_allowed_directory

# Initialize path validator
path_validator = PathValidator()


def find_glm_api_key():
    """Read only the explicitly supplied process environment; never shell files."""
    return os.environ.get('GLM_API_KEY')


def open_html_in_browser(html_path):
    """
    Open HTML file in default browser.

    Args:
        html_path: Path to HTML file
    """
    if not Path(html_path).exists():
        print(f"⚠️  HTML file not found: {html_path}")
        return

    try:
        if sys.platform == 'darwin':  # macOS
            subprocess.run(['open', html_path], check=True)
        elif sys.platform == 'win32':  # Windows
            # Use os.startfile for safer Windows file opening
            import os
            os.startfile(html_path)
        else:  # Linux
            subprocess.run(['xdg-open', html_path], check=True)
        print(f"✓ Opened HTML diff in browser: {html_path}")
    except Exception as e:
        print(f"⚠️  Could not open browser: {e}")
        print(f"   Please manually open: {html_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Enhanced transcript fixer with optional HTML diff opening",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fix transcript and save to custom output directory
  %(prog)s input.md --output ./corrected --auto-open

  # Fix without opening browser
  %(prog)s input.md --output ./corrected --no-auto-open

  # Use specific domain
  %(prog)s input.md --output ./corrected --domain embodied_ai
        """
    )

    parser.add_argument('input', help='Input transcript file (.md or .txt)')
    parser.add_argument('--output', '-o', help='Output directory (default: same as input file)')
    parser.add_argument('--domain', default='general',
                       choices=['general', 'embodied_ai', 'finance', 'medical'],
                       help='Domain for corrections (default: general)')
    parser.add_argument('--stage', type=int, default=3, choices=[1, 2, 3],
                       help='Processing stage: 1=dict, 2=AI, 3=both (default: 3)')
    parser.add_argument('--auto-open', action='store_true', default=False,
                       help='Automatically open HTML diff in browser (default: False)')
    parser.add_argument('--no-auto-open', dest='auto_open', action='store_false',
                       help='Do not open HTML diff automatically')

    args = parser.parse_args()

    # CRITICAL FIX: Validate input file with security checks
    try:
        # Add current directory to allowed paths (for user convenience)
        add_allowed_directory(Path.cwd())

        input_path = path_validator.validate_input_path(args.input)
        print(f"✓ Input file validated: {input_path}")

    except PathValidationError as e:
        print(f"❌ Input file validation failed: {e}")
        sys.exit(1)

    # CRITICAL FIX: Validate output directory
    if args.output:
        try:
            # Add output directory to allowed paths
            output_dir_path = Path(args.output).expanduser().absolute()
            add_allowed_directory(output_dir_path.parent if output_dir_path.parent.exists() else output_dir_path)

            output_dir = output_dir_path
            output_dir.mkdir(parents=True, exist_ok=True)
            print(f"✓ Output directory validated: {output_dir}")

        except PathValidationError as e:
            print(f"❌ Output directory validation failed: {e}")
            sys.exit(1)
    else:
        output_dir = input_path.parent

    # Check/find API key if Stage 2 or 3
    if args.stage in [2, 3]:
        api_key = find_glm_api_key()
        if not api_key:
            print("❌ GLM_API_KEY not set. Supply it explicitly or run with --stage 1")
            sys.exit(1)

    # Get script directory
    script_dir = Path(__file__).parent
    main_script = script_dir / "fix_transcription.py"

    if not main_script.exists():
        print(f"❌ Main script not found: {main_script}")
        sys.exit(1)

    # Build command
    cmd = [
        'uv', 'run', '--with', 'httpx',
        str(main_script),
        '--input', str(input_path),
        '--stage', str(args.stage),
        '--domain', args.domain
    ]

    print(f"📖 Processing: {input_path.name}")
    print(f"📁 Output directory: {output_dir}")
    print(f"🎯 Domain: {args.domain}")
    print(f"⚙️  Stage: {args.stage}")
    print()

    # Run main script
    try:
        result = subprocess.run(cmd, check=True, cwd=script_dir.parent)
    except subprocess.CalledProcessError as e:
        print(f"❌ Processing failed with exit code {e.returncode}")
        sys.exit(e.returncode)

    # Move output files to desired directory if different from input directory
    if output_dir != input_path.parent:
        print(f"\n📦 Moving output files to {output_dir}...")

        base_name = input_path.stem
        output_patterns = [
            f"{base_name}_stage1.md",
            f"{base_name}_stage2.md",
            f"{base_name}_对比.html",
            f"{base_name}_对比报告.md",
            f"{base_name}_修复报告.md",
        ]

        for pattern in output_patterns:
            source = input_path.parent / pattern
            if source.exists():
                dest = output_dir / pattern
                source.rename(dest)
                print(f"  ✓ {pattern}")

    # Auto-open HTML diff
    if args.auto_open:
        html_file = output_dir / f"{input_path.stem}_对比.html"
        if html_file.exists():
            print("\n🌐 Opening HTML diff in browser...")
            open_html_in_browser(html_file)
        else:
            print(f"\n⚠️  HTML diff not generated; run scripts/generate_word_diff.py explicitly")

    print("\n✅ Processing complete!")
    print(f"\n📄 Output files in: {output_dir}")
    for suffix in ('_stage1.md', '_stage2.md', '_对比.html'):
        produced = output_dir / f"{input_path.stem}{suffix}"
        if produced.exists():
            print(f"   - {produced.name}")


if __name__ == '__main__':
    main()
