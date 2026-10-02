"""One PDF of a patient's records, in order, for an office or attorney that
asks for them - instead of finding the patient in EZClaim, then the scans in
Google Drive, then the paper in the cabinet.

    cover page (practice, patient, what is enclosed, for whom, by whom)
    table of contents (folder, document, its dates, page number)
    every document, folder by folder, oldest first

Built on Main with no outside service: scanned JPEGs go into the PDF as they
are, plain PNG scans are carried over losslessly (PDF can hold PNG's own
compressed rows), anything else is converted by tesseract, and the parts are
joined by poppler's pdfunite. Nothing here decides what may be sent - the
person sending chooses; claims_web records the disclosure.
"""
from __future__ import annotations

import shutil
import struct
import subprocess
import tempfile
from pathlib import Path


class PacketError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# a minimal PDF writer: text pages and image pages
# ---------------------------------------------------------------------------

def _pdf(objects: list[bytes]) -> bytes:
    out, offs = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"), []
    for i, o in enumerate(objects, 1):
        offs.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    x = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offs)
    out += b"trailer << /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, x)
    return bytes(out)


def _esc(s: str) -> str:
    s = s.encode("latin-1", "replace").decode("latin-1")
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def text_pdf(pages: list[list[tuple[str, int, bool]]]) -> bytes:
    """Letter-size pages of (text, size, bold) lines, Helvetica, top down."""
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>"]
    kids = []
    for lines in pages:
        y, ops = 740, []
        for text, size, bold in lines:
            if text:
                ops.append(f"BT /{'F2' if bold else 'F1'} {size} Tf 54 {y} Td ({_esc(text)}) Tj ET")
            y -= int(size * 1.45)
        stream = "\n".join(ops).encode("latin-1", "replace")
        objs.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
        content = len(objs)
        objs.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents %d 0 R >>" % content)
        kids.append(len(objs))
    objs[1] = b"<< /Type /Pages /Kids [%s] /Count %d >>" % (b" ".join(b"%d 0 R" % k for k in kids), len(kids))
    return _pdf(objs)


def _jpeg_size(raw: bytes) -> tuple[int, int, int]:
    i = 2
    while i < len(raw) - 9:
        if raw[i] != 0xFF:
            i += 1
            continue
        marker = raw[i + 1]
        if marker in (0xC0, 0xC1, 0xC2):
            h, w = struct.unpack(">HH", raw[i + 5:i + 9])
            return w, h, raw[i + 9]
        i += 2 + struct.unpack(">H", raw[i + 2:i + 4])[0]
    raise PacketError("not a readable JPEG")


def _png_parts(raw: bytes):
    """(width, height, colors, idat) for 8-bit gray/RGB non-interlaced PNGs;
    None for anything else (then tesseract converts it)."""
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    i, idat, ihdr = 8, b"", None
    while i < len(raw):
        n = struct.unpack(">I", raw[i:i + 4])[0]
        kind, body = raw[i + 4:i + 8], raw[i + 8:i + 8 + n]
        if kind == b"IHDR":
            ihdr = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            idat += body
        i += 12 + n
    if not ihdr:
        return None
    w, h, depth, ctype, _, _, interlace = ihdr
    if depth != 8 or interlace or ctype not in (0, 2):
        return None
    return w, h, 1 if ctype == 0 else 3, idat


def image_pdf(mime: str, raw: bytes, work: Path) -> bytes:
    """One page holding the image, scaled to fit inside letter margins."""
    if mime == "image/jpeg":
        w, h, comps = _jpeg_size(raw)
        cs = {1: "/DeviceGray", 3: "/DeviceRGB", 4: "/DeviceCMYK"}.get(comps, "/DeviceRGB")
        img = b"<< /Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace %s /BitsPerComponent 8 /Filter /DCTDecode /Length %d >>\nstream\n" % (
            w, h, cs.encode(), len(raw)) + raw + b"\nendstream"
    else:
        parts = _png_parts(raw)
        if not parts:   # palette / alpha / 16-bit PNG: let tesseract make the page
            src = work / "img.png"
            src.write_bytes(raw)
            subprocess.run(["tesseract", str(src), str(work / "img"), "--dpi", "200", "pdf"], capture_output=True, timeout=180)
            out = work / "img.pdf"
            if not out.exists():
                raise PacketError("could not convert an image page")
            return out.read_bytes()
        w, h, colors, idat = parts
        img = (b"<< /Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace %s /BitsPerComponent 8 /Filter /FlateDecode "
               b"/DecodeParms << /Predictor 15 /Colors %d /BitsPerComponent 8 /Columns %d >> /Length %d >>\nstream\n") % (
            w, h, b"/DeviceGray" if colors == 1 else b"/DeviceRGB", colors, w, len(idat)) + idat + b"\nendstream"
    scale = min(540 / w, 720 / h)
    dw, dh = w * scale, h * scale
    x, y = (612 - dw) / 2, (792 - dh) / 2
    stream = f"q {dw:.2f} 0 0 {dh:.2f} {x:.2f} {y:.2f} cm /Im0 Do Q".encode()
    return _pdf([b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
                 b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>",
                 img, b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"])


def page_count(pdf: bytes, work: Path) -> int:
    f = work / "count.pdf"
    f.write_bytes(pdf)
    r = subprocess.run(["pdfinfo", str(f)], capture_output=True, text=True, timeout=60)
    for line in r.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split()[1])
    raise PacketError("a PDF in this patient's file could not be read")


# ---------------------------------------------------------------------------
# the packet
# ---------------------------------------------------------------------------

def build(cover: dict, docs: list[dict]) -> tuple[bytes, int]:
    """cover: practice, patient, dob, account, period, recipient, prepared, by.
    docs: [{"category", "title", "when", "pages": [{"type", "raw"}]}] in order.
    Returns (pdf, total pages)."""
    if not docs:
        raise PacketError("nothing matches - no documents in those folders and dates")
    work = Path(tempfile.mkdtemp(prefix="packet_"))
    try:
        parts, counts = [], []
        for d in docs:
            n = 0
            for pg in d["pages"]:
                blob = pg["raw"] if pg["type"] == "application/pdf" else image_pdf(pg["type"], pg["raw"], work)
                p = work / f"part{len(parts):04d}.pdf"
                p.write_bytes(blob)
                parts.append(p)
                n += page_count(blob, work)
            counts.append(n)

        # cover + contents first, so the contents can give page numbers
        rows = []
        for d, n in zip(docs, counts):
            rows.append((d["category"], d["title"], d.get("when") or "", n))
        lines_per_page = 40
        toc_pages = max(1, -(-len(rows) // lines_per_page))
        first = 1 + toc_pages + 1
        cover_lines = [(cover.get("practice") or "", 16, True), (cover.get("practice_addr") or "", 10, False), ("", 10, False),
                       ("PATIENT RECORDS", 20, True), ("", 10, False),
                       (f"Patient:  {cover.get('patient', '')}", 12, False), (f"Date of birth:  {cover.get('dob', '')}", 12, False),
                       (f"Account #:  {cover.get('account', '')}", 12, False), (f"Records period:  {cover.get('period', 'all dates')}", 12, False),
                       ("", 10, False), (f"Prepared for:  {cover.get('recipient') or '-'}", 12, True),
                       (f"Prepared:  {cover.get('prepared', '')}  by  {cover.get('by', '')}", 12, False),
                       (f"Enclosed:  {len(docs)} documents, {sum(counts)} pages (contents follow)", 12, False), ("", 10, False),
                       ("CONFIDENTIAL: This packet contains protected health information disclosed for the purpose", 9, False),
                       ("stated above. If you received it in error, notify the sender and destroy all copies.", 9, False)]
        toc, page, last_cat = [], first, None
        for cat, title, when, n in rows:
            label = (cat + ":  " if cat != last_cat else "      ") + title + (f"  ({when})" if when and when not in title else "")
            toc.append((f"{label[:88]:<90}{page:>5}", 9, cat != last_cat))
            last_cat, page = cat, page + n
        toc_chunks = [toc[i:i + lines_per_page] for i in range(0, len(toc), lines_per_page)] or [[]]
        head = [[("CONTENTS" + (" (continued)" if i else ""), 14, True), ("", 8, False)] + chunk for i, chunk in enumerate(toc_chunks)]
        front = work / "front.pdf"
        front.write_bytes(text_pdf([cover_lines] + head))
        out = work / "packet.pdf"
        r = subprocess.run(["pdfunite", str(front), *map(str, parts), str(out)], capture_output=True, timeout=600)
        if r.returncode != 0 or not out.exists():
            raise PacketError("could not join the documents: " + r.stderr.decode(errors="replace")[-200:])
        data = out.read_bytes()
        return data, page_count(data, work)
    finally:
        shutil.rmtree(work, ignore_errors=True)
