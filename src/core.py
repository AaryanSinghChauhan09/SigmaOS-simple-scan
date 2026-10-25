"""SANE scanner frontend planner for SigmaOS-simple-scan.

The engine parses `scanimage -L` device dumps, plans scan invocations
(device, resolution, mode, format), multi-page batches and output filename
patterns. Talking to the scanner itself is the thin execute layer --
self_test() only exercises the pure parse/plan layer (no subprocess, no SANE
device access).
Principles: Separation of Concerns, Defensive Programming, Fail-Fast, KISS.
"""
import argparse, os, re, shlex, sys

ENGINE = {
    "name": "sigma-scan",
    "summary": "Plan SANE scans: devices, resolution, batches, output names",
    "language": "python",
    "verbs": ["devices", "scan-plan", "page", "output"],
    "principles": ["Separation of Concerns", "Defensive Programming",
                   "Fail-Fast", "KISS", "Deterministic Testing"],
}

cli_doc = """\
$ sigma-scan devices scanimage-L.txt
genesys:libusb:001:004  Genesys USB flatbed scanner
$ sigma-scan scan-plan --device 'genesys:libusb:001:004' --dpi 300
scanimage --device genesys:libusb:001:004 --resolution 300 --mode color --format=png
$ sigma-scan page --count 3
--batch --batch-count 3 --batch-start 1
$ sigma-scan output --pattern 'page-%d.png' --count 3
page-1.png page-2.png page-3.png
"""


class ScanError(Exception):
    pass


MODES = ("color", "gray", "lineart")
FORMATS = {"png": "png", "jpg": "jpeg", "jpeg": "jpeg", "tiff": "tiff",
           "pnm": "pnm", "pbm": "pbm"}
_DEV_RE = re.compile(r"^device\s+`(.+?)'\s+is\s+a\s+(.+)$")


# --------------------------------------------------------------------------- #
#  PURE parse / plan layer
# --------------------------------------------------------------------------- #
def parse_devices(text):
    """Parse `scanimage -L` output into SANE device records."""
    devices, seen = [], set()
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _DEV_RE.match(line)
        if not m:
            raise ScanError(f"line {lineno}: unparseable device line: {line!r}")
        dev_id, model = m.group(1), m.group(2)
        if dev_id in seen:
            continue                # de-duplicate
        seen.add(dev_id)
        devices.append({"id": dev_id, "model": model})
    if not devices:
        raise ScanError("no SANE devices found")
    return devices


def _check_device(device):
    if not isinstance(device, str) or not device.strip():
        raise ScanError("no scanner device given")
    if "\n" in device or device != device.strip():
        raise ScanError(f"bad device id: {device!r}")
    return device


def scan_plan(device, dpi=300, mode="color", fmt="png"):
    """Build the scanimage argv for a single page."""
    _check_device(device)
    dpi = int(dpi) if not isinstance(dpi, str) or dpi.isdigit() else None
    if dpi is None:
        raise ScanError("dpi must be an integer")
    if not (50 <= dpi <= 1200):
        raise ScanError("dpi must be 50..1200")
    if mode not in MODES:
        raise ScanError(f"unknown mode {mode!r} (choose from {', '.join(MODES)})")
    if fmt not in FORMATS:
        raise ScanError(f"unknown format {fmt!r} "
                        f"(choose from {', '.join(sorted(FORMATS))})")
    return ["scanimage", "--device", device, "--resolution", str(dpi),
            "--mode", mode, f"--format={FORMATS[fmt]}"]


def page_plan(pages=1, start=1):
    """Plan a multi-page batch; validates page counts."""
    try:
        pages, start = int(pages), int(start)
    except (TypeError, ValueError):
        raise ScanError("page count and start must be integers")
    if not (1 <= pages <= 9999):
        raise ScanError("page count must be 1..9999")
    if not (1 <= start <= 9999):
        raise ScanError("start page must be 1..9999")
    return {"pages": pages, "start": start,
            "argv": ["--batch", "--batch-count", str(pages),
                     "--batch-start", str(start)]}


def output_plan(pattern, pages=1):
    """Validate an output filename pattern and expand batch names."""
    if not isinstance(pattern, str) or not pattern.strip():
        raise ScanError("empty output pattern")
    if ".." in pattern or pattern.startswith("/"):
        raise ScanError("output pattern must be a plain relative filename")
    pages = int(pages)
    if pages < 1:
        raise ScanError("page count must be >= 1")
    has_slot = "%d" in pattern
    if pages > 1 and not has_slot:
        raise ScanError("multi-page output pattern needs a %d slot")
    if pages == 1 and has_slot:
        pages = 1                       # single page may still use the slot
    names = [pattern % (i,) for i in range(1, pages + 1)] if has_slot \
        else [pattern]
    for n in names:
        if not n or n.endswith("."):
            raise ScanError(f"bad expanded filename: {n!r}")
    return names


# --------------------------------------------------------------------------- #
#  CLI
# --------------------------------------------------------------------------- #
def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog=ENGINE["name"], description=ENGINE["summary"])
    sub = p.add_subparsers(dest="cmd", required=True)
    dv = sub.add_parser("devices", help="parse a `scanimage -L` dump")
    dv.add_argument("file")
    sp = sub.add_parser("scan-plan", help="build a scanimage invocation")
    sp.add_argument("--device", required=True)
    sp.add_argument("--dpi", default=300)
    sp.add_argument("--mode", default="color", choices=list(MODES))
    sp.add_argument("--format", default="png", dest="fmt",
                    choices=sorted(FORMATS))
    pg = sub.add_parser("page", help="plan a multi-page batch")
    pg.add_argument("--count", default=1)
    pg.add_argument("--start", default=1)
    ot = sub.add_parser("output", help="validate an output filename pattern")
    ot.add_argument("--pattern", required=True)
    ot.add_argument("--count", default=1)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "devices":
            for d in parse_devices(_read(args.file)):
                print(f'{d["id"]}  {d["model"]}')
        elif args.cmd == "scan-plan":
            plan = scan_plan(args.device, args.dpi, args.mode, args.fmt)
            print(" ".join(shlex.quote(a) for a in plan))
        elif args.cmd == "page":
            plan = page_plan(args.count, args.start)
            print(" ".join(plan["argv"]))
        elif args.cmd == "output":
            print(" ".join(output_plan(args.pattern, args.count)))
        return 0
    except (ScanError, ValueError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


# --------------------------------------------------------------------------- #
#  Tests (pure parse/plan layer only)
# --------------------------------------------------------------------------- #
SAMPLE_SCANIMAGE_L = """\
device `genesys:libusb:001:004' is a Genesys USB flatbed scanner
device `escl:HP LaserJet MFP M148dw [CNBL001ABC]' is a HP LaserJet MFP eSCL scanner
device `net:192.168.1.50:canon' is a network TWAIN scanner
"""


def self_test() -> None:
    devs = parse_devices(SAMPLE_SCANIMAGE_L)
    assert len(devs) == 3, devs
    assert devs[0]["id"] == "genesys:libusb:001:004"
    assert devs[0]["model"] == "Genesys USB flatbed scanner"
    assert devs[1]["id"].startswith("escl:HP LaserJet")
    assert devs[2]["model"] == "network TWAIN scanner"
    # de-duplication + comment tolerance
    dup = SAMPLE_SCANIMAGE_L + "device `net:192.168.1.50:canon' is a network scanner\n# note\n"
    assert len(parse_devices(dup)) == 3
    for bad in ("", "garbage line\n", "device `x' is\n"):
        try:
            parse_devices(bad)
        except ScanError:
            pass
        else:
            raise AssertionError(f"bad device dump not rejected: {bad!r}")

    plan = scan_plan("genesys:libusb:001:004", 300, "color", "png")
    assert plan == ["scanimage", "--device", "genesys:libusb:001:004",
                    "--resolution", "300", "--mode", "color",
                    "--format=png"], plan
    assert scan_plan("x", fmt="jpg")[-1] == "--format=jpeg"
    for bad in (("genesys", 25, "color", "png"),      # dpi too low
                ("genesys", 2000, "color", "png"),    # dpi too high
                ("genesys", 300, "colour", "png"),    # bad mode
                ("genesys", 300, "color", "bmp"),     # bad format
                ("", 300, "color", "png"),            # empty device
                ("genesys\n", 300, "color", "png")):  # injection attempt
        try:
            scan_plan(*bad)
        except ScanError:
            pass
        else:
            raise AssertionError(f"bad scan plan not rejected: {bad!r}")

    plan = page_plan(3, 1)
    assert plan["argv"] == ["--batch", "--batch-count", "3", "--batch-start", "1"]
    assert page_plan(1)["argv"] == ["--batch", "--batch-count", "1", "--batch-start", "1"]
    for bad in ((0, 1), (3, 0), (10000, 1), ("many", 1)):
        try:
            page_plan(*bad)
        except ScanError:
            pass
        else:
            raise AssertionError(f"bad page plan not rejected: {bad!r}")

    assert output_plan("scan-%d.png", 3) == ["scan-1.png", "scan-2.png", "scan-3.png"]
    assert output_plan("single.png", 1) == ["single.png"]
    assert output_plan("s-%d.png", 1) == ["s-1.png"]
    for bad in (("page.png", 3),     # missing %d slot for a batch
                ("../escape.png", 1),
                ("/etc/passwd", 1),
                ("", 1)):
        pat, pages = bad
        try:
            output_plan(pat, pages)
        except ScanError:
            pass
        else:
            raise AssertionError(f"bad output plan not rejected: {bad!r}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
