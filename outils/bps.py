"""Création / application de patchs BPS (format standard des romhacks SMW)."""
import zlib


def _num(n):
    out = bytearray()
    while True:
        x = n & 0x7F; n >>= 7
        if n == 0:
            out.append(0x80 | x); return out
        out.append(x); n -= 1


def create(source, target, metadata=b""):
    p = bytearray(b"BPS1")
    p += _num(len(source)) + _num(len(target)) + _num(len(metadata)) + metadata
    i, n = 0, len(target)
    while i < n:
        same = i < len(source) and source[i] == target[i]
        j = i
        while j < n and (j < len(source) and source[j] == target[j]) == same:
            j += 1
        if same:
            p += _num(((j - i - 1) << 2) | 0)           # SourceRead
        else:
            p += _num(((j - i - 1) << 2) | 1) + target[i:j]  # TargetRead
        i = j
    p += zlib.crc32(source).to_bytes(4, "little") + zlib.crc32(target).to_bytes(4, "little")
    p += zlib.crc32(p).to_bytes(4, "little")
    return bytes(p)


def apply(source, patch):
    assert patch[:4] == b"BPS1"
    pos = 4

    def num():
        nonlocal pos
        data, shift = 0, 1
        while True:
            x = patch[pos]; pos += 1
            data += (x & 0x7F) * shift
            if x & 0x80:
                return data
            shift <<= 7; data += shift
    ssize, tsize, msize = num(), num(), num()
    pos += msize
    assert len(source) == ssize and zlib.crc32(source).to_bytes(4, "little") == patch[-12:-8]
    out = bytearray(); src_rel = tgt_rel = 0
    while pos < len(patch) - 12:
        d = num(); mode, length = d & 3, (d >> 2) + 1
        if mode == 0:
            out += source[len(out):len(out) + length]
        elif mode == 1:
            out += patch[pos:pos + length]; pos += length
        else:
            o = num(); o = -(o >> 1) if o & 1 else o >> 1
            if mode == 2:
                src_rel += o; out += source[src_rel:src_rel + length]; src_rel += length
            else:
                tgt_rel += o
                for _ in range(length):
                    out.append(out[tgt_rel]); tgt_rel += 1
    assert len(out) == tsize and zlib.crc32(out).to_bytes(4, "little") == patch[-8:-4]
    return bytes(out)
