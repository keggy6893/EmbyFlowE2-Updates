import ast,unittest
import build
class GenreRelease(unittest.TestCase):
    def test_only_genre_fields_and_release_identity(self):
        old=ast.parse(build.baseline());new=ast.parse(build.build_source())
        for a,b in zip(old.body,new.body):
            if isinstance(a,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('PLUGIN_VERSION','PLUGIN_UPDATE_BUILD','PLUGIN_UPDATE_CHANGELOG') for t in a.targets):continue
            if isinstance(a,ast.FunctionDef) and a.name=='_efbad_init':
                before=ast.unparse(a);after=ast.unparse(b)
                self.assertIn('sy(400)',after);self.assertNotIn('sy(442)',after)
                self.assertIn('#F2C94C',after)
                after=after.replace('sy(400)','sy(442)').replace('#F2C94C','#CFD5DD')
                self.assertEqual(before,after)
            else:self.assertEqual(ast.dump(a),ast.dump(b))
        self.assertEqual(len(old.body),len(new.body))
    def test_no_local_test_wrappers(self):
        text=build.build_source()
        self.assertNotIn('EMBYFLOW_DETAIL_GENRES_LOCAL_V1_BEGIN',text)
        self.assertIn('EMBYFLOW_RECEIVER_AUDIO_4097_V2_END',text)
    def test_compiles_python38(self):
        ast.parse(build.build_source(),feature_version=(3,8))
if __name__=='__main__':unittest.main()
