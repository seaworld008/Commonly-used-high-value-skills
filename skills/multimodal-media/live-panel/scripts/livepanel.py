"""Shared helpers: build the page from template + config, and drive Chrome over the DevTools pipe (standard library only)."""
import base64, json, os, shutil, signal, stat, subprocess, sys, tempfile, threading, time
from contextlib import ExitStack, contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE = ROOT / "assets" / "template.html"
CHROME_NAMES = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "microsoft-edge"]
# On macOS the browser lives inside an .app bundle, not on PATH. Homebrew's `chromium` shim on PATH launches
# and then dies on the DevTools pipe, so real bundles are preferred over anything shutil.which() would find.
CHROME_MAC_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
]


def find_exe(explicit, names, what):
    if explicit:
        p = shutil.which(explicit) or (explicit if os.path.exists(explicit) else None)
        if p:
            return p
        sys.exit(f"{what} not found: {explicit}")
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    sys.exit(f"{what} not found on PATH (tried {', '.join(names)}); pass it explicitly")


def find_chrome(explicit):
    """Chrome lookup: an explicit path wins, then macOS .app bundles, then the PATH names in CHROME_NAMES."""
    if explicit:
        return find_exe(explicit, CHROME_NAMES, "Chrome")
    if sys.platform == "darwin":
        for p in CHROME_MAC_PATHS:
            if os.path.exists(p):
                return p
    return find_exe(None, CHROME_NAMES, "Chrome")


CANVAS_PRESETS = {"4:5": (1200, 1500), "3:4": (1080, 1440), "1:1": (1080, 1080)}


def canvas(cfg):
    """(width, height, duration, fps) from a config, honouring canvas.preset."""
    cv = cfg.get("canvas", {})
    pw, ph = CANVAS_PRESETS.get(cv.get("preset"), (1200, 1500))
    return cv.get("width", pw), cv.get("height", ph), cv.get("duration", 30), cv.get("fps", 30)


def load_config(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_page(config_path, out_path, template=None):
    """Write a self-contained HTML file: template with the JSON config embedded. Returns the config dict."""
    cfg = load_config(config_path)
    tpl = Path(template or DEFAULT_TEMPLATE).read_text(encoding="utf-8")
    blob = json.dumps(cfg, ensure_ascii=False).replace("</", "<\\/")
    tag = f'<script id="live-config" type="application/json">{blob}</script>'
    if "<!--LIVE_CONFIG-->" not in tpl:
        sys.exit("template has no <!--LIVE_CONFIG--> placeholder")
    Path(out_path).write_text(tpl.replace("<!--LIVE_CONFIG-->", tag), encoding="utf-8")
    return cfg


@contextmanager
def handle_sigterm():
    """Let the CLI unwind its contexts on termination; leave the caller's handler intact."""
    if threading.current_thread() is not threading.main_thread():
        yield
        return
    terminating = False

    def terminate(signum, frame):
        nonlocal terminating
        if not terminating:
            terminating = True
            raise SystemExit(128 + signum)

    previous = signal.signal(signal.SIGTERM, terminate)
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous)


def _is_mp4(stream, length):
    """Check bounded top-level ISO BMFF boxes without reading the video payload."""
    boxes = set()
    while stream.tell() < length:
        start = stream.tell()
        header = stream.read(8)
        if len(header) != 8:
            return False
        size = int.from_bytes(header[:4], "big")
        if size == 1:
            extended = stream.read(8)
            if len(extended) != 8:
                return False
            size = int.from_bytes(extended, "big")
        elif size == 0:
            size = length - start
        end = start + size
        payload = end - stream.tell()
        if payload < 0 or end > length:
            return False
        if header[4:] == b"ftyp" and (payload < 8 or payload % 4):
            return False
        if header[4:] == b"moov" and payload < 8:
            return False
        if payload:
            boxes.add(header[4:])
        stream.seek(end)
    return {b"ftyp", b"moov", b"mdat"} <= boxes


def _is_png(stream, length):
    if stream.read(16) != b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR":
        return False
    width = int.from_bytes(stream.read(4), "big")
    height = int.from_bytes(stream.read(4), "big")
    if not width or not height:
        return False
    stream.seek(33)  # Signature, IHDR and its CRC.
    image_data = False
    while stream.tell() + 12 <= length:
        size = int.from_bytes(stream.read(4), "big")
        kind = stream.read(4)
        end = stream.tell() + size + 4
        if end > length:
            return False
        if kind == b"IEND":
            return image_data and size == 0 and end == length
        if kind == b"IDAT" and size:
            image_data = True
        stream.seek(end)
    return False


class MediaOutputs:
    """Stage in private directories on the destination filesystems, then publish the batch."""

    def __init__(self):
        self.directories = {}
        self.files = {}
        self.recovery = set()

    def stage(self, destination, kind):
        destination = Path(destination)
        parent = destination.parent.resolve()
        destination = parent / destination.name
        if destination in self.files:
            raise ValueError(f"duplicate output: {destination}")
        if parent not in self.directories:
            parent.mkdir(parents=True, exist_ok=True)
            self.directories[parent] = Path(tempfile.mkdtemp(dir=parent, prefix=".livepanel-"))
        staged = self.directories[parent] / destination.name
        self.files[destination] = staged, kind
        return staged

    def publish(self):
        import fcntl  # The render/check CLIs use POSIX pipes. Building an HTML page does not.

        for destination, (staged, kind) in self.files.items():
            if not staged.exists() or not stat.S_ISREG(staged.lstat().st_mode):
                raise RuntimeError(f"missing or non-regular {kind} output: {destination}")
            with staged.open("rb") as media:
                length = os.fstat(media.fileno()).st_size
                validate = _is_mp4 if kind == "MP4" else _is_png
                if not length or not validate(media, length):
                    raise RuntimeError(f"empty or invalid {kind} output: {destination}")
        # Serialize overlapping publishes, including rollback, without a persistent lock file.
        with ExitStack() as locks:
            for directory in sorted(self.directories):
                fd = os.open(directory, os.O_RDONLY)
                locks.callback(os.close, fd)
                fcntl.flock(fd, fcntl.LOCK_EX)
            self._replace()

    def _replace(self):
        backups = {}
        for destination, (staged, _) in self.files.items():
            try:
                mode = destination.lstat().st_mode
            except FileNotFoundError:
                continue
            if not stat.S_ISREG(mode):
                raise RuntimeError(f"cannot replace non-regular output: {destination}")
            staged.chmod(mode & 0o777)
            # A private hard link keeps the previous inode available for rollback.
            backup_dir = staged.parent / ".previous"
            backup_dir.mkdir(exist_ok=True)
            backup = backup_dir / destination.name
            try:
                os.link(destination, backup)
            except OSError:
                shutil.copy2(destination, backup)
            backups[destination] = backup
        replacing = []
        try:
            for destination, (staged, _) in self.files.items():
                replacing.append((staged, destination))
                staged.replace(destination)
        except BaseException:
            failures = []
            for staged, destination in reversed(replacing):
                if staged.exists():
                    continue  # This replacement had not taken effect.
                try:
                    if destination in backups:
                        backups[destination].replace(destination)
                    else:
                        destination.unlink()
                except OSError as exc:
                    self.recovery.add(staged.parent)
                    failures.append(f"{destination}: {exc} (recovery directory: {staged.parent})")
            if failures:
                raise RuntimeError("incomplete output rollback: " + "; ".join(failures))
            raise

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        for directory in self.directories.values():
            if directory not in self.recovery:
                shutil.rmtree(directory)
        if exc_type and self.files and not self.recovery:
            print("discarded staged partial output, including any partial frames", file=sys.stderr)


class Chrome:
    """Headless Chrome driven through --remote-debugging-pipe (no websocket, no third-party packages)."""

    def __init__(self, chrome, width, height, no_sandbox=False):
        with ExitStack() as resources:
            self.tmp = resources.enter_context(tempfile.TemporaryDirectory(prefix="livepanel-"))
            args = [chrome, "--headless=new", "--remote-debugging-pipe", f"--user-data-dir={self.tmp}", "--no-first-run",
                    "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1", "--font-render-hinting=none",
                    "--allow-file-access-from-files", "--disable-background-timer-throttling", "--mute-audio", "about:blank"]
            if no_sandbox is True:
                args.insert(1, "--no-sandbox")
            with ExitStack() as child_fds:
                r1, w1 = os.pipe()   # we write -> chrome fd 3
                child_fds.callback(os.close, r1)
                self.wf = resources.enter_context(os.fdopen(w1, "wb", buffering=0))
                r2, w2 = os.pipe()   # chrome fd 4 -> we read
                child_fds.callback(os.close, w2)
                self.rf = resources.enter_context(os.fdopen(r2, "rb", buffering=0))
                env = dict(os.environ, LP_R=str(r1), LP_W=str(w2))
                self.proc = subprocess.Popen(["sh", "-c", 'exec "$@" 3<&"$LP_R" 4>&"$LP_W"', "sh"] + args,
                                             pass_fds=(r1, w2), env=env,
                                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                resources.callback(self._stop_process)
            self.buf = b""; self.n = 0
            self._connect(width, height)
            self.resources = resources.pop_all()

    def _connect(self, width, height):
        try:
            tid = self.call("Target.createTarget", {"url": "about:blank"})["targetId"]
            self.sid = self.call("Target.attachToTarget", {"targetId": tid, "flatten": True})["sessionId"]
            self.cmd("Page.enable")
            self.cmd("Emulation.setDeviceMetricsOverride", {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": False})
        except (OSError, RuntimeError) as exc:
            raise RuntimeError(f"Chrome startup failed, rendering unverified: {exc}") from exc

    def call(self, method, params=None, session=None):
        self.n += 1
        msg = {"id": self.n, "method": method, "params": params or {}}
        if session:
            msg["sessionId"] = session
        self.wf.write(json.dumps(msg).encode() + b"\0")
        while True:
            while b"\0" not in self.buf:
                chunk = os.read(self.rf.fileno(), 1 << 20)
                if not chunk:
                    raise RuntimeError("Chrome closed the pipe")
                self.buf += chunk
            raw, self.buf = self.buf.split(b"\0", 1)
            m = json.loads(raw)
            if m.get("id") == self.n:
                if "error" in m:
                    raise RuntimeError(f"{method}: {m['error']}")
                return m.get("result", {})

    def cmd(self, method, params=None):
        return self.call(method, params, self.sid)

    def eval(self, expr):
        r = self.cmd("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
        if "exceptionDetails" in r:
            raise RuntimeError(f"js error: {r['exceptionDetails']}")
        return r["result"].get("value")

    def open(self, url, timeout=20):
        self.cmd("Page.navigate", {"url": url})
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                if self.eval("window.__ready===true"):
                    err = self.eval("window.__error||''")
                    if err:
                        raise RuntimeError("page error: " + err)
                    return
                err = self.eval("window.__error||''")
                if err:
                    raise RuntimeError("page error: " + err)
            except RuntimeError as e:
                if "page error" in str(e):
                    raise
            time.sleep(0.1)
        raise RuntimeError("page did not become ready (check the config JSON)")

    def seek(self, t):
        self.eval(f"window.seek({t!r})")

    def shot(self):
        return base64.b64decode(self.cmd("Page.captureScreenshot", {"format": "png"})["data"])

    def _stop_process(self):
        try:
            self.proc.terminate(); self.proc.wait(5)
        except BaseException as exc:
            self.proc.kill()
            self.proc.wait()
            if not isinstance(exc, subprocess.TimeoutExpired):
                raise

    def close(self):
        self.resources.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()
