# SPDX-License-Identifier: GPL-2.0-or-later
"""Small deterministic raw-LZ4 encoder; standard block form, no dependencies."""
def encode(data):
    data = bytes(data)
    result = bytearray()
    table = {}
    anchor = at = 0
    def extra(n):
        while n >= 255:
            result.append(255)
            n -= 255
        result.append(n)
    while at <= len(data)-12:
        key = data[at:at+4]
        previous = table.get(key)
        table[key] = at
        if previous is None or at-previous > 65535:
            at += 1
            continue
        matched = 4
        while at+matched < len(data)-5 and data[previous+matched] == data[at+matched]:
            matched += 1
        literals = at-anchor
        result.append(min(literals,15)<<4 | min(matched-4,15))
        if literals >= 15: extra(literals-15)
        result += data[anchor:at]
        result += (at-previous).to_bytes(2,'little')
        if matched-4 >= 15: extra(matched-19)
        stop = at+matched
        for pos in range(at+1,stop): table[data[pos:pos+4]] = pos
        at = anchor = stop
    literals = len(data)-anchor
    result.append(min(literals,15)<<4)
    if literals >= 15: extra(literals-15)
    result += data[anchor:]
    return bytes(result) if len(result)<len(data) else data
