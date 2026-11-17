#!/usr/bin/env python3
"""Render a live-panel config to an H.264 mp4: step window.seek(t) frame by frame, screenshot, pipe into ffmpeg.

  python3 scripts/render.py --config examples/service-pipeline/config.json --out out.mp4
Chrome and ffmpeg are looked up on PATH (Chrome also under /Applications on macOS) unless --chrome / --ffmpeg are given.
Runs on Linux and macOS; on Windows use WSL (the Chrome DevTools pipe needs POSIX fd passing).
"""
import argparse, os, subprocess, sys, tempfile
from contextlib import contextmanager
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import livepanel as lp


@contextmanager
def generated_page(config, html_out=None, template=None):
    """Keep explicit HTML; scope private HTML (including build failures) to this run."""
    if html_out:
        yield html_out, lp.build_page(config, html_out, template)
    else:
        with tempfile.TemporaryDirectory(prefix="livepanel-page-") as directory:
            page = os.path.join(directory, "page.html")
            yield page, lp.build_page(config, page, template)


def check_page_error(br):
    err = br.eval("window.__error||''")
    if err:
        raise RuntimeError("page errors: " + str(err))


def finish_encoder(ff, abort=False):
    """Send EOF and reap the encoder even when rendering or closing its pipe fails."""
    if abort:
        ff.kill()  # Do not wait on a stalled reader while flushing a cancelled render.
    try:
        ff.stdin.close()
    except BrokenPipeError:
        if not abort:
            raise
    finally:
        try:
            rc = ff.wait(timeout=30)
        except BaseException as exc:
            ff.terminate()
            try:
                ff.wait(timeout=5)
            except BaseException:
                ff.kill()
                ff.wait()
            if isinstance(exc, subprocess.TimeoutExpired):
                raise RuntimeError("encoder did not finish after EOF") from exc
            raise
    return rc


@lp.handle_sigterm()
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True, help="path to the JSON config")
    ap.add_argument("--out", required=True, help="output .mp4")
    ap.add_argument("--width", type=int, help="video width (default: config canvas.width)")
    ap.add_argument("--height", type=int, help="video height (default: config canvas.height)")
    ap.add_argument("--duration", type=float, help="seconds (default: config canvas.duration)")
    ap.add_argument("--fps", type=int, help="frames per second (default: config canvas.fps or 30)")
    ap.add_argument("--chrome", help="Chrome/Chromium executable (default: search PATH, and /Applications on macOS)")
    ap.add_argument("--ffmpeg", help="ffmpeg executable (default: search PATH)")
    ap.add_argument("--template", help="alternative template.html")
    ap.add_argument("--crf", type=int, default=16)
    ap.add_argument("--audio", choices=["silent", "none"], default="silent", help="add a silent AAC track (some chat apps treat silent-less mp4 as a GIF)")
    ap.add_argument("--html-out", help="also keep the generated self-contained page here (opens live in any browser)")
    ap.add_argument("--keep-frames", help="also write PNG frames into this directory")
    ap.add_argument("--no-sandbox", action="store_true", help="disable the Chrome sandbox in an explicitly approved isolated environment")
    a = ap.parse_args()

    chrome = lp.find_chrome(a.chrome)
    ffmpeg = lp.find_exe(a.ffmpeg, ["ffmpeg"], "ffmpeg")
    with lp.MediaOutputs() as outputs:
        with generated_page(a.config, a.html_out, a.template) as (page, cfg):
            cw, ch, cdur, cfps = lp.canvas(cfg)
            w = a.width or cw; h = a.height or ch
            fps = a.fps if a.fps is not None else cfps
            dur = a.duration if a.duration is not None else cdur
            n = int(round(fps * dur))
            if fps <= 0 or n < 1:
                ap.error("duration and fps must produce at least one frame at a positive frame rate")
            w -= w % 2; h -= h % 2   # yuv420p needs even sizes
            cmd = [ffmpeg, "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(fps), "-c:v", "png", "-i", "-"]
            if a.audio == "silent":
                cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest", "-c:a", "aac", "-b:a", "32k"]
            video = outputs.stage(a.out, "MP4")
            cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", str(a.crf), "-pix_fmt", "yuv420p",
                    "-r", str(fps), "-movflags", "+faststart", "-f", "mp4", str(video)]
            with lp.Chrome(chrome, w, h, a.no_sandbox) as br:
                br.open("file://" + os.path.abspath(page) + "?manual")
                check_page_error(br)
                ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
                try:
                    for i in range(n):
                        br.seek(i / fps)
                        check_page_error(br)
                        png = br.shot()
                        check_page_error(br)
                        if a.keep_frames:
                            frame = outputs.stage(Path(a.keep_frames, f"f_{i:04d}.png"), "PNG")
                            frame.write_bytes(png)
                        ff.stdin.write(png)
                        if i % fps == 0:
                            print(f"\r{i}/{n} frames", end="", file=sys.stderr, flush=True)
                    check_page_error(br)
                except BaseException:
                    finish_encoder(ff, abort=True)
                    raise
                rc = finish_encoder(ff)
            if rc != 0:
                raise RuntimeError(f"encoder exited with status {rc}")
        outputs.publish()
    print(f"\nwrote {a.out} ({n} frames, {w}x{h}@{fps})", file=sys.stderr)
    sys.exit(rc)


if __name__ == "__main__":
    main()
