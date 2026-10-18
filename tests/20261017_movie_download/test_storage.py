import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from test_ui import load_ui, Session

class StorageTests(unittest.TestCase):
    def setUp(self):
        self.ns=load_ui();self.engine=self.ns['_efdl_engine'];self.session=Session()
        self.root='/media/usb'
    def info(self,free=87*2**30,total=119*2**30):
        with patch.object(self.engine.shutil,'disk_usage',return_value=SimpleNamespace(free=free,total=total)):
            return self.engine.storage_info(self.root,8*2**30)
    def chooser(self,capacity):
        return self.ns['EmbyFlowDownloadChoice'](self.session,title='Downloadziel auswählen',list=[('/media/usb',self.root)],storage={self.root:capacity})
    def test_free_and_total_shown_with_movie_requirement(self):
        screen=self.chooser(self.info());screen.draw()
        self.assertIn('87,0 GiB frei',screen['info0'].text)
        self.assertIn('119,0 GiB gesamt',screen['storage_meta0'].text)
        self.assertIn('Film: 8,00 GiB',screen['details'].text)
        self.assertIn('Reserve: 0,50 GiB',screen['details'].text)
        self.assertIn('Genügend Speicher',screen['details'].text)
    def test_low_space_visible_and_ok_blocked(self):
        screen=self.chooser(self.info(free=8*2**30));screen.draw();screen.accept()
        self.assertIn('Zu wenig Speicher',screen['storage_meta0'].text)
        self.assertIn('Zu wenig Speicher',screen['hint'].text)
        self.assertFalse(hasattr(screen,'result'))
    def test_space_probe_failure_cannot_be_selected(self):
        with patch.object(self.engine.shutil,'disk_usage',side_effect=OSError('unmounted')):
            capacity=self.engine.storage_info(self.root,8*2**30)
        screen=self.chooser(capacity);screen.draw();screen.accept()
        self.assertIn('Nicht ermittelbar',screen['info0'].text)
        self.assertFalse(hasattr(screen,'result'))
    def test_exact_required_plus_reserve_is_enough(self):
        screen=self.chooser(self.info(free=8*2**30+self.engine.RESERVE))
        screen.accept()
        self.assertEqual(screen.result,(('/media/usb',self.root),))
    def test_capacity_collected_for_each_target_in_real_flow(self):
        screen=self.ns['EmbyFlowLocalDownloadScreen'](self.session,{})
        screen.permission_state='granted'
        self.ns['_efdl_targets']=lambda:[('/media/hdd','/media/hdd'),('/media/usb','/media/usb')]
        with patch.object(self.engine.shutil,'disk_usage',return_value=SimpleNamespace(free=50*2**30,total=100*2**30)) as probe:
            screen.source_chosen(('Film',{'Id':'s','Size':8*2**30}))
        self.assertEqual(probe.call_count,2)
        self.assertEqual(set(self.session.kwargs['storage']),{'/media/hdd','/media/usb'})
        self.assertTrue(self.session.kwargs['storage']['/media/usb']['enough'])
    def test_real_disk_snapshot_matches_os_free_space(self):
        with tempfile.TemporaryDirectory() as root:
            measured=self.engine.storage_info(root,1)
            actual=self.engine.shutil.disk_usage(root)
            self.assertTrue(measured['known'])
            self.assertEqual(measured['total'],actual.total)
            self.assertLess(abs(measured['free']-actual.free),16*1024*1024)

if __name__=='__main__':unittest.main()
