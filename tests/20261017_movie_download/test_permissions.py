import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import urlsplit
import requests
from test_ui import load_ui, Session

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        path=urlsplit(self.path).path
        self.server.paths.append(path)
        if path=='/Users/user':
            status=self.server.policy_status
            payload=self.server.policy
        elif path=='/Users/user/Items/movie':
            status=200
            payload=self.server.item
        else:
            status=500;payload={}
        data=json.dumps(payload).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(data)))
        self.end_headers();self.wfile.write(data)

class PermissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def setUp(self):
        self.ns=load_ui();self.engine=self.ns['_efdl_engine']
        self.base='http://127.0.0.1:%d'%self.server.server_port
        self.cancel=threading.Event()
        self.server.paths=[]
        self.server.policy_status=200
        self.server.policy={'Policy':{'EnableContentDownloading':True}}
        self.server.item={'Id':'movie','Name':'Film','Type':'Movie','MediaSources':[{'Id':'source','Size':1024,'Container':'mkv'}]}
        self.ns['requests']=requests
        self.ns['get_emby_auth']=lambda:(self.base,'test-token','user')
        self.screen=self.ns['EmbyFlowLocalDownloadScreen'](Session(),{'id':'movie'})
    def check(self):
        return self.engine.check_permission(requests,self.base,'test-token','user',self.cancel)
    def drain(self):
        while not self.screen.events.empty():self.screen.poll()
    def test_explicit_allow_opens_versions_with_visible_status(self):
        self.screen.metadata();self.drain()
        self.assertEqual(self.screen.permission_state,'granted')
        self.assertIn('Freigegeben',self.screen['permission'].text)
        self.assertIn('bestätigt',self.screen.session.kwargs['access_status'])
        self.assertEqual(self.server.paths,['/Users/user','/Users/user/Items/movie'])
    def test_single_episode_is_downloadable_but_whole_series_is_not(self):
        self.server.item['Type']='Episode'
        self.screen.metadata();self.drain()
        self.assertTrue(hasattr(self.screen.session,'kwargs'))
        self.screen.session=Session()
        self.server.item['Type']='Series'
        self.screen.metadata();self.drain()
        self.assertFalse(hasattr(self.screen.session,'kwargs'))
    def test_denial_does_not_fetch_film_or_open_choices(self):
        self.server.policy['Policy']['EnableContentDownloading']=False
        self.screen.metadata();self.drain()
        self.assertEqual(self.server.paths,['/Users/user'])
        self.assertEqual(self.screen.permission_state,'denied')
        self.assertIn('Nicht erlaubt',self.screen['permission'].text)
        self.assertFalse(hasattr(self.screen.session,'kwargs'))
    def test_missing_policy_blocks_as_unknown(self):
        self.server.policy={}
        self.screen.metadata();self.drain()
        self.assertEqual(self.screen.permission_state,'unknown')
        self.assertEqual(self.server.paths,['/Users/user'])
        self.assertFalse(hasattr(self.screen.session,'kwargs'))
    def test_http_failure_is_unknown_not_falsely_denied(self):
        self.server.policy_status=503
        self.screen.metadata();self.drain()
        self.assertEqual(self.screen.permission_state,'unknown')
        self.assertIn('Nicht prüfbar',self.screen['permission'].text)
    def test_item_specific_denial_blocks_versions(self):
        self.server.item['CanDownload']=False
        self.screen.metadata();self.drain()
        self.assertEqual(self.screen.permission_state,'denied')
        self.assertFalse(hasattr(self.screen.session,'kwargs'))
    def test_policy_revoked_before_transfer_does_not_call_download(self):
        self.screen.metadata();self.drain()
        self.screen.source=self.server.item['MediaSources'][0]
        self.screen.target='/media/hdd/movie/EmbyFlow/film.mkv'
        self.server.policy['Policy']['EnableContentDownloading']=False
        self.engine.download=Mock()
        self.screen.transfer();self.drain()
        self.engine.download.assert_not_called()
        self.assertEqual(self.screen.permission_state,'denied')
        self.assertEqual(self.server.paths.count('/Users/user'),2)
    def test_allowed_transfer_rechecks_before_request(self):
        self.screen.metadata();self.drain()
        self.screen.source=self.server.item['MediaSources'][0]
        self.screen.target='/media/hdd/movie/EmbyFlow/film.mkv'
        self.ns['_efdl_targets']=lambda:[('/media/hdd','/media/hdd')]
        self.engine.download=Mock(return_value=self.screen.target)
        self.screen.transfer();self.drain()
        self.engine.download.assert_called_once()
        self.assertEqual(self.server.paths.count('/Users/user'),2)
        self.assertIn('erneut bestätigt',self.screen['permission'].text)
    def test_final_server_denial_overrides_earlier_allow(self):
        self.screen.metadata();self.drain()
        self.screen.source=self.server.item['MediaSources'][0]
        self.screen.target='/media/hdd/movie/EmbyFlow/film.mkv'
        self.ns['_efdl_targets']=lambda:[('/media/hdd','/media/hdd')]
        self.engine.download=Mock(side_effect=self.engine.DownloadPermissionDenied('Download verweigert: HTTP 403'))
        self.screen.transfer();self.drain()
        self.assertEqual(self.screen.permission_state,'denied')
        self.assertIn('HTTP 403',self.screen['status'].text)
    def test_malformed_source_sizes_never_reach_dialog(self):
        self.server.item['MediaSources']=[None,{'Id':'bad','Size':'unknown'},{'Id':'negative','Size':-1}]
        self.screen.metadata();self.drain()
        self.assertFalse(hasattr(self.screen.session,'kwargs'))
        self.assertIn('Keine herunterladbare',self.screen['status'].text)
    def test_network_error_does_not_expose_token_or_url(self):
        client=Mock()
        client.get.side_effect=requests.Timeout('https://secret-server/?api_key=secret-token')
        with self.assertRaises(self.engine.DownloadPermissionUnknown) as error:
            self.engine.check_permission(client,self.base,'test-token','user',self.cancel)
        self.assertNotIn('secret',str(error.exception))
        self.assertNotIn('http',str(error.exception))
    def test_non_boolean_allow_is_not_permission(self):
        self.server.policy['Policy']['EnableContentDownloading']='true'
        with self.assertRaises(self.engine.DownloadPermissionUnknown):self.check()
    def test_cancelled_before_permission_no_network_request(self):
        self.cancel.set()
        with self.assertRaises(self.engine.DownloadCancelled):self.check()
        self.assertEqual(self.server.paths,[])
    def test_confirm_cannot_bypass_failed_permission(self):
        self.screen.permission_state='unknown'
        self.screen.confirmed(True)
        self.drain()
        self.assertIn('Kein Download gestartet',self.screen['status'].text)
        self.assertEqual(self.server.paths,[])
    def test_permission_redirect_never_followed(self):
        self.server.policy_status=302
        with self.assertRaises(self.engine.DownloadPermissionUnknown):self.check()
        self.assertEqual(self.server.paths,['/Users/user'])

if __name__=='__main__':unittest.main()
