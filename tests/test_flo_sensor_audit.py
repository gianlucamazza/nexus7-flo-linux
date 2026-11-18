"""Catch unsafe acceptance of malformed or RAM-overlapping DSPS images."""
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/flo-sensor-audit.py'


def image(folder, segments=None):
    # The hash segment is authenticated metadata, never a loaded RAM segment.
    loads = segments if segments is not None else [
        (1, 0x2000, 0, 0x12000000, 4, 8, 7, 4),
        (1, 0x3000, 0x8fe00000, 0x8fe00000, 4, 8, 7, 4)]
    segments = [(0, 0, 0, 0, 0, 0, 0x07000000, 0),
                (1, 0x1000, 0x8fe10000, 0x8fe10000, 4, 8, 0x02200000, 4)] + loads
    ident = b'\x7fELF\x01\x01\x01' + bytes(9)
    hdr = struct.pack('<16sHHIIIIIHHHHHH', ident, 2, 40, 1, 0, 52, 0, 0, 52, 32, len(segments), 0, 0, 0)
    table = b''.join(struct.pack('<8I', *s) for s in segments)
    metadata = hdr + table
    segments[0] = (0, 0, 0, 0, len(metadata), 0, 0x07000000, 0)
    table = b''.join(struct.pack('<8I', *s) for s in segments)
    metadata = hdr + table
    for i, seg in enumerate(segments):
        (folder / f'dsps.b{i:02d}').write_bytes(metadata if i == 0 else bytes([i]) * seg[4])
    (folder / 'dsps.mdt').write_bytes(metadata + bytes([1]) * 4)


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        image(self.root)
        self.iomem = self.root / 'iomem'
        self.iomem.write_text('80200000-8effffff : System RAM\n8f700000-fffffffe : System RAM\n')
        self.dt_reserved = self.root / 'reserved-memory'
        self.dt_reserved.mkdir()

    def run_audit(self):
        return subprocess.run([sys.executable, str(SCRIPT), '--firmware-dir', str(self.root),
                               '--iomem', str(self.iomem),
                               '--dt-reserved-memory', str(self.dt_reserved)],
                              capture_output=True, text=True)

    def result(self):
        run = self.run_audit()
        self.assertEqual(run.returncode, 0, run.stderr)
        return json.loads(run.stdout)

    def test_reports_physical_load_addresses_and_skips_hash(self):
        result = self.result()
        self.assertEqual(result['schema_version'], 2)
        self.assertEqual([s['physical_address'] for s in result['load_segments']], [0x12000000, 0x8fe00000])
        self.assertEqual(result['architecture'], 'ARM ELF32 little-endian')

    def test_linux_ram_overlap_blocks_reservation_check(self):
        result = self.result()
        self.assertEqual(result['ddr_memory_check'], 'overlaps-system-ram')
        self.assertEqual(result['overlapping_system_ram'], [[0x8f700000, 0xffffffff]])

    def test_no_overlap_is_not_proof_of_reservation(self):
        self.iomem.write_text('80200000-8effffff : System RAM\n')
        self.assertEqual(self.result()['ddr_memory_check'], 'no-overlap-reservation-unverified')

    def test_exact_dt_reservation_needs_no_map_and_no_ram_overlap(self):
        node = self.dt_reserved / 'dsps@8fe00000'
        node.mkdir()
        (node / 'reg').write_bytes(struct.pack('>II', 0x8fe00000, 0x100000))
        (node / 'no-map').touch()
        result = self.result()
        self.assertEqual(result['ddr_dt_reservation'], 'exact-no-map')
        self.assertEqual(result['ddr_memory_check'], 'overlaps-system-ram')
        self.iomem.write_text('80200000-8effffff : System RAM\n')
        self.assertEqual(self.result()['ddr_dt_reservation'], 'exact-no-map')

    def test_missing_or_wrong_dt_reservation_is_not_exact(self):
        self.assertEqual(self.result()['ddr_dt_reservation'], 'missing')
        node = self.dt_reserved / 'dsps@8fe00000'
        node.mkdir()
        (node / 'reg').write_bytes(struct.pack('>II', 0x8fe00000, 0x80000))
        (node / 'no-map').touch()
        self.assertEqual(self.result()['ddr_dt_reservation'], 'invalid')
        (node / 'reg').write_bytes(struct.pack('>II', 0x8fe00000, 0x100000))
        (node / 'no-map').unlink()
        self.assertEqual(self.result()['ddr_dt_reservation'], 'invalid')

    def test_missing_or_redacted_iomem_stays_unknown(self):
        for text in ['', '00000000-00000000 : System RAM\n']:
            self.iomem.write_text(text)
            self.assertEqual(self.result()['ddr_memory_check'], 'unknown')
        self.iomem.unlink()
        self.assertEqual(self.result()['ddr_memory_check'], 'unknown')

    def test_hashes_match_real_input(self):
        result = self.result()
        self.assertEqual(result['files']['dsps.b02']['sha256'], 'bb72b4e4eb29dc59328668f32e0511e3ac0e5ce4026b1591965216e49ca1f5d7')

    def test_rejects_missing_or_truncated_load_blob(self):
        path = self.root / 'dsps.b02'
        for data in [None, b'\x02' * 3, b'\x02' * 5]:
            if data is None:
                path.unlink()
            else:
                path.write_bytes(data)
            run = self.run_audit()
            self.assertEqual(run.returncode, 1)
            self.assertIn('dsps.b02', run.stderr)

    def test_rejects_missing_or_mismatched_metadata(self):
        (self.root / 'dsps.b01').write_bytes(b'\x03' * 4)
        self.assertEqual(self.run_audit().returncode, 1)

    def test_rejects_bad_elf_headers(self):
        original = (self.root / 'dsps.mdt').read_bytes()
        for offset, value in [(0, b'BAD!'), (4, b'\x02'), (5, b'\x02'), (18, b'\xa4\x00'),
                              (42, b'\x01\x00'), (44, b'\xff\xff')]:
            with self.subTest(offset=offset):
                data = bytearray(original)
                data[offset:offset + len(value)] = value
                (self.root / 'dsps.mdt').write_bytes(data)
                self.assertEqual(self.run_audit().returncode, 1)
        (self.root / 'dsps.mdt').write_bytes(original[:40])
        self.assertEqual(self.run_audit().returncode, 1)

    def test_rejects_segments_outside_confirmed_windows(self):
        for paddr, filesz, memsz in [(0x12027ffc, 4, 8), (0x8ff00000, 4, 8),
                                     (0x12000000, 8, 4), (0xfffffff0, 4, 32)]:
            with self.subTest(paddr=paddr, memsz=memsz):
                image(self.root, [(1, 0x1000, 0, paddr, filesz, memsz, 7, 4)])
                self.assertEqual(self.run_audit().returncode, 1)

    def test_rejects_overlapping_load_segments(self):
        image(self.root, [(1, 0x1000, 0, 0x12000000, 4, 8, 7, 4),
                          (1, 0x2000, 0, 0x12000004, 4, 8, 7, 4)])
        self.assertEqual(self.run_audit().returncode, 1)

    def test_rejects_payload_with_zero_memory_even_if_blob_absent(self):
        image(self.root, [(1, 0x2000, 0, 0xffffffff, 4, 0, 7, 4),
                          (1, 0x3000, 0, 0x12000000, 4, 8, 7, 4)])
        (self.root / 'dsps.b02').unlink()
        run = self.run_audit()
        self.assertEqual(run.returncode, 1)
        self.assertIn('invalid file/memory size', run.stderr)

    def test_rejects_empty_or_nonload_hash_metadata(self):
        original = (self.root / 'dsps.mdt').read_bytes()
        header_end = len(original) - 4
        for kind, size in [(0, 4), (1, 0), (0, 0)]:
            with self.subTest(kind=kind, size=size):
                data = bytearray(original[:header_end] + bytes([1]) * size)
                struct.pack_into('<I', data, 52 + 32, kind)
                struct.pack_into('<I', data, 52 + 32 + 16, size)
                (self.root / 'dsps.mdt').write_bytes(data)
                (self.root / 'dsps.b00').write_bytes(data[:header_end])
                (self.root / 'dsps.b01').write_bytes(bytes([1]) * size)
                run = self.run_audit()
                self.assertEqual(run.returncode, 1)
                self.assertIn('hash metadata', run.stderr)

    def test_undecodable_iomem_is_unknown(self):
        self.iomem.write_bytes(b'\xff')
        self.assertEqual(self.result()['ddr_memory_check'], 'unknown')

    def test_failure_does_not_modify_inputs(self):
        (self.root / 'dsps.b02').write_bytes(b'bad')
        before = {str(p.relative_to(self.root)): p.read_bytes()
                  for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(self.run_audit().returncode, 1)
        self.assertEqual({str(p.relative_to(self.root)): p.read_bytes()
                          for p in self.root.rglob('*') if p.is_file()}, before)


if __name__ == '__main__':
    unittest.main()
