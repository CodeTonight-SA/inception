import struct, zlib
def read_png(path):
    d = open(path, 'rb').read()
    assert d[:8].hex() == '89504e470d0a1a0a', 'not a png'
    pos = 8; idat = b''; w = h = bitd = colort = interlace = None
    while pos < len(d):
        ln = struct.unpack('>I', d[pos:pos+4])[0]; typ = d[pos+4:pos+8]
        chunk = d[pos+8:pos+8+ln]
        if typ == b'IHDR':
            w, h, bitd, colort, _comp, _filt, interlace = struct.unpack('>IIBBBBB', chunk[:13])
        elif typ == b'IDAT':
            idat += chunk
        elif typ == b'IEND':
            break
        pos += 12 + ln
    if interlace != 0:
        raise SystemExit('interlaced png not supported')
    raw = zlib.decompress(idat)
    ch = 4 if colort == 6 else (3 if colort == 2 else 1)
    stride = w * ch
    out = bytearray(w * h * ch); prev = bytearray(stride); p = 0
    for y in range(h):
        f = raw[p]; p += 1
        line = bytearray(raw[p:p+stride]); p += stride
        if f == 1:
            for i in range(ch, stride): line[i] = (line[i] + line[i-ch]) & 255
        elif f == 2:
            for i in range(stride): line[i] = (line[i] + prev[i]) & 255
        elif f == 3:
            for i in range(stride):
                a = line[i-ch] if i >= ch else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 255
        elif f == 4:
            for i in range(stride):
                a = line[i-ch] if i >= ch else 0
                b = prev[i]; c = prev[i-ch] if i >= ch else 0
                pp = a + b - c; pa, pb, pc = abs(pp-a), abs(pp-b), abs(pp-c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 255
        out[y*stride:(y+1)*stride] = line
        prev = line
    return w, h, ch, bytes(out)

w, h, ch, px = read_png('receipt.png')
print('PNG', w, 'x', h, 'channels', ch)
def at(x, y):
    i = (y * w + x) * ch
    return px[i], px[i+1], px[i+2]
green = red = paper = band = amber = other = 0
for y in range(0, h, 4):
    for x in range(0, w, 4):
        r, g, b = at(x, y)
        if g > 120 and g > r + 40 and g > b + 40:
            green += 1
        elif r > 130 and r > g + 50 and r > b + 50:
            red += 1
        elif r < 45 and g < 45 and b < 50:
            band += 1
        elif r > 170 and g > 110 and b < 90:
            amber += 1
        elif abs(r-g) < 18 and abs(g-b) < 22 and r > 200 and g > 190:
            paper += 1
        else:
            other += 1
print('green=%d red=%d band=%d amber=%d paper=%d other=%d' % (green, red, band, amber, paper, other))
print('VERDICT: green_stamps=%s red_stamps=%s paper_body=%s dark_header=%s' % (
    green > 50, red > 50, paper > 800, band > 200))
