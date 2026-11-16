#!/usr/bin/env python3
"""Read-only APQ8064 DSPS split-firmware validation; never authorizes boot."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

# Stock devices-8064.c: PPSS_DSPS_{TCM_CODE,TCM_BUF,PIPE,DDR}_{BASE,SIZE}.
WINDOWS = ((0x12000000, 0x12028000, 'tcm-code'),
           (0x12040000, 0x12044000, 'tcm-buffer'),
           (0x12800000, 0x12804000, 'pipe'),
           (0x8fe00000, 0x8ff00000, 'ddr'))
HEADER = struct.Struct('<16sHHIIIIIHHHHHH')
PHDR = struct.Struct('<8I')


def firmware_layout(data):
    """Validate the ELF table before examining or loading any segment file."""
    if len(data) < HEADER.size:
        raise ValueError('dsps.mdt: truncated ELF header')
    h = HEADER.unpack_from(data)
    if h[0][:7] != b'\x7fELF\x01\x01\x01' or h[1:4] != (2, 40, 1):
        raise ValueError('dsps.mdt: expected ARM ELF32 little-endian executable')
    if h[8] != HEADER.size or h[9] != PHDR.size or not 2 <= h[10] <= 100:
        raise ValueError('dsps.mdt: invalid ELF/program header size or count')
    end = h[5] + h[10] * PHDR.size
    if h[5] < HEADER.size or end > len(data):
        raise ValueError('dsps.mdt: program header table out of bounds')
    phdrs = [PHDR.unpack_from(data, h[5] + i * PHDR.size) for i in range(h[10])]
    # APQ8064 image: ELF-header segment first, one hash segment second.
    if phdrs[0][0] != 0 or phdrs[0][1] != 0 or phdrs[0][4] != end:
        raise ValueError('dsps.mdt: invalid metadata header segment')
    hash_indices = [i for i, p in enumerate(phdrs) if p[6] & 0x07000000 == 0x02000000]
    if (hash_indices != [1] or phdrs[1][0] != 1 or phdrs[1][4] == 0
            or len(data) != end + phdrs[1][4]):
        raise ValueError('dsps.mdt: invalid or truncated hash metadata')
    loads = []
    for i, p in enumerate(phdrs):
        kind, offset, vaddr, paddr, filesz, memsz, flags, align = p
        if i < 2:
            continue
        if kind != 1:
            continue
        if filesz > memsz or paddr + memsz > 1 << 32:
            raise ValueError(f'segment {i}: invalid file/memory size')
        if memsz == 0:
            continue
        if flags & 0x08000000:
            raise ValueError(f'segment {i}: relocatable images are unsupported')
        window = next((name for lo, hi, name in WINDOWS if lo <= paddr and paddr + memsz <= hi), None)
        if window is None:
            raise ValueError(f'segment {i}: outside documented DSPS memory windows')
        if any(paddr < s['physical_address'] + s['memory_size'] and
               s['physical_address'] < paddr + memsz for s in loads):
            raise ValueError(f'segment {i}: overlapping load segments')
        loads.append({'index': i, 'physical_address': paddr, 'virtual_address': vaddr,
                      'file_size': filesz, 'memory_size': memsz, 'window': window})
    if not loads:
        raise ValueError('dsps.mdt: no loadable segments')
    return loads, end, phdrs[1][4]


def memory_check(iomem):
    """Absence of System RAM overlap is deliberately not proof of a carveout."""
    try:
        text = iomem.read_text()
    except (OSError, UnicodeError):
        return 'unknown', []
    ranges = []
    for line in text.splitlines():
        match = re.fullmatch(r'\s*([0-9a-fA-F]+)-([0-9a-fA-F]+)\s*:\s*System RAM\s*', line)
        if match:
            lo, last = (int(n, 16) for n in match.groups())
            if last < lo or (lo == last == 0):
                return 'unknown', []
            ranges.append((lo, last + 1))
    if not ranges:
        return 'unknown', []
    overlap = [[lo, hi] for lo, hi in ranges if lo < 0x8ff00000 and 0x8fe00000 < hi]
    return ('overlaps-system-ram' if overlap else 'no-overlap-reservation-unverified'), overlap


def audit(firmware_dir, iomem):
    """Return structural validation and evidence, without changing any inputs."""
    files = {}

    def read(name):
        blob = (firmware_dir / name).read_bytes()
        files[name] = {'size': len(blob), 'sha256': hashlib.sha256(blob).hexdigest()}
        return blob

    mdt = read('dsps.mdt')
    loads, header_end, hash_size = firmware_layout(mdt)
    if read('dsps.b00') != mdt[:header_end]:
        raise ValueError('dsps.b00: does not match MDT ELF metadata')
    if read('dsps.b01') != mdt[header_end:header_end + hash_size]:
        raise ValueError('dsps.b01: does not match MDT hash metadata')
    for segment in loads:
        name = f"dsps.b{segment['index']:02d}"
        if len(read(name)) != segment['file_size']:
            raise ValueError(f'{name}: segment size differs from ELF program header')
    state, overlap = memory_check(iomem)
    return {'schema_version': 1, 'architecture': 'ARM ELF32 little-endian',
            'files': files, 'load_segments': loads, 'ddr_memory_check': state,
            'overlapping_system_ram': overlap,
            'scope': 'Structural validation only; not signature verification or boot authorization.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--firmware-dir', type=Path, default=Path('/lib/firmware/postmarketos'))
    parser.add_argument('--iomem', type=Path, default=Path('/proc/iomem'))
    args = parser.parse_args()
    try:
        result = audit(args.firmware_dir, args.iomem)
    except (OSError, ValueError) as error:
        print(f'flo-sensor-audit: {error}', file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
