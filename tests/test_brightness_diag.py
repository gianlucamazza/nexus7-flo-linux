import importlib.machinery
import importlib.util
from pathlib import Path
import tempfile
import unittest

path = Path(__file__).resolve().parents[1] / 'scripts/nexus7-brightness-diag'
loader = importlib.machinery.SourceFileLoader('brightness_diag', str(path))
spec = importlib.util.spec_from_loader(loader.name, loader)
diag = importlib.util.module_from_spec(spec)
loader.exec_module(diag)


class Backend:
    def __init__(self, states):
        self.states = iter(states)
        self.last = {}

    def state(self):
        self.last = next(self.states, self.last)
        return self.last

    def capture(self, path):
        path.write_bytes(b'P6\n1 1\n255\n\0\0\0')

    def layers(self):
        return {'0': {'levels': {'3': [{'namespace': 'flo-quicksettings', 'x': 0, 'y': 0, 'w': 600, 'h': 960}]}}}


READY = {'locked': False, 'displayOn': True, 'quickSettings': True, 'brightness': 50}


class BrightnessDiagnosticsTests(unittest.TestCase):
    def test_locked_session_creates_no_capture(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'capture'
            with self.assertRaises(diag.CaptureDenied):
                diag.run_capture(target, Backend([dict(READY, locked=True)]), frames=1, interval=0)
            self.assertFalse(target.exists())

    def test_off_or_unknown_session_creates_no_capture(self):
        for state in [dict(READY, displayOn=False), {}, {'locked': False}]:
            with self.subTest(state=state), tempfile.TemporaryDirectory() as temp:
                target = Path(temp) / 'capture'
                with self.assertRaises(diag.CaptureDenied):
                    diag.run_capture(target, Backend([state]), frames=1, interval=0)
                self.assertFalse(target.exists())

    def test_lock_during_collection_retains_only_prior_frame(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'capture'
            with self.assertRaises(diag.CaptureDenied):
                diag.run_capture(target, Backend([READY, READY, READY, READY, dict(READY, locked=True)]), frames=3, interval=0)
            self.assertEqual([p.name for p in target.glob('*.ppm')], ['frame-000.ppm'])
            self.assertEqual(len((target / 'samples.jsonl').read_text().splitlines()), 1)

    def test_lock_while_frame_is_captured_discards_that_frame(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'capture'
            with self.assertRaises(diag.CaptureDenied):
                diag.run_capture(target, Backend([READY, READY, dict(READY, locked=True)]), frames=1, interval=0)
            self.assertEqual(list(target.glob('*.ppm')), [])

    def test_ready_collection_records_frames_and_correlated_geometry(self):
        import json
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'capture'
            diag.run_capture(target, Backend([READY, READY, dict(READY, brightness=60)]), frames=2, interval=0)
            samples = [json.loads(x) for x in (target / 'samples.jsonl').read_text().splitlines()]
            self.assertEqual([x['state']['brightness'] for x in samples], [50, 60])
            self.assertEqual(len(list(target.glob('*.ppm'))), 2)
            self.assertEqual(samples[0]['layers']['0']['levels']['3'][0]['namespace'], 'flo-quicksettings')
            self.assertLessEqual(samples[0]['monotonic'], samples[1]['monotonic'])
