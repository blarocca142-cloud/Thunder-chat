"""Read the signing certificate out of an APK's v2 signing block.
keytool -printcert only understands v1 JAR signatures and silently prints
nothing for these, which is why it gave no signal at all."""
import struct, sys, hashlib, zipfile, re

MAGIC = b"APK Sig Block 42"
V2_ID = 0x7109871a
u32 = lambda b, o: struct.unpack_from("<I", b, o)[0]
u64 = lambda b, o: struct.unpack_from("<Q", b, o)[0]


def certificates(path):
    d = open(path, "rb").read()
    i = d.rfind(MAGIC)
    if i < 0:
        return []
    size = u64(d, i - 8)
    body = d[i + len(MAGIC) - 8 - size + 8 : i - 8]
    o = 0
    while o + 12 <= len(body):
        plen = u64(body, o)
        if u32(body, o + 8) == V2_ID:
            val = body[o + 12 : o + 8 + plen]
            end = 4 + u32(val, 0)
            p, out = 4, []
            while p + 4 <= end:
                slen = u32(val, p)
                sp = p + 4
                sd = val[sp + 4 : sp + 4 + u32(val, sp)]
                q = 4 + u32(sd, 0)          # skip digests
                cend = q + 4 + u32(sd, q)
                q += 4
                while q + 4 <= cend:
                    clen = u32(sd, q)
                    q += 4
                    out.append(sd[q : q + clen])
                    q += clen
                p = sp + slen
            return out
        o += 8 + plen
    return []


def version(path):
    m = zipfile.ZipFile(path).read("AndroidManifest.xml").decode("utf-16-le", "ignore")
    found = re.findall(r"\d+\.\d+\.\d+", m)
    return found[0] if found else "?"


expected = open("mykey.der", "rb").read()
for apk in sys.argv[1:]:
    cs = certificates(apk)
    if not cs:
        print(f"{apk}: no v2 signature found")
        continue
    for c in cs:
        ok = c == expected
        print(f"{apk}  v{version(apk)}  {hashlib.sha256(c).hexdigest()[:32]}  "
              f"{'MATCH' if ok else 'DIFFERENT'}")
