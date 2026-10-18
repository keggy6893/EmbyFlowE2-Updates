"""Regression for the receiver crash in Screen.createGUIScreen, line 366.
Contract verified against openATV/enigma2 8.0 lib/python/Screens/Screen.py:
onLayoutFinish accepts bound methods or executable source, not plain functions.
"""
import unittest
from test_ui import load_ui, Session

def dispatch_layout(screen):
    # Same dispatch used by openATV 8.0 Screen.createGUIScreen.
    for method in screen.onLayoutFinish:
        if not isinstance(method, type(screen.close)):
            exec(method, globals(), locals())
        else:
            method()

class OpenATVLayoutTests(unittest.TestCase):
    def setUp(self):self.ns=load_ui();self.session=Session()
    def test_download_window_layout_uses_compatible_callback(self):
        screen=self.ns['EmbyFlowLocalDownloadScreen'](self.session,{'title':'Film'})
        dispatch_layout(screen)
    def test_plain_lambda_reproduces_reported_crash(self):
        screen=self.ns['EmbyFlowLocalDownloadScreen'](self.session,{})
        screen.onLayoutFinish=[lambda:None]
        with self.assertRaisesRegex(TypeError,'exec\\(\\) arg 1'):
            dispatch_layout(screen)
    def test_choice_layout_compatible_with_openatv_dispatch(self):
        screen=self.ns['EmbyFlowDownloadChoice'](self.session,title='Film',list=[('1080p',{'Size':100,'Container':'mkv'})])
        dispatch_layout(screen)
        self.assertEqual(screen['row0'].text,'Full HD')

if __name__=='__main__':unittest.main()
