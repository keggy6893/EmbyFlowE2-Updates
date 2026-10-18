"""Optional integration check using the pinned public LCD4linux r36 source.

No plugin import/startup; only AST-selected functions are compiled.
Installed r40 remains a receiver test, not an asserted equivalent source.
"""
import ast
from pathlib import Path
from types import SimpleNamespace
import urllib.request

URL = ('https://raw.githubusercontent.com/oe-alliance/oe-alliance-plugins/'
       '4d4bde2651a25bf9570be58182af8f6ad64b29d9/LCD4linux/src/plugin.py')


def main():
    with urllib.request.urlopen(URL,timeout=20) as response:source=response.read().decode()
    tree=ast.parse(source)
    progress=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='putProgress')
    picture=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='LCD4linuxPIC')
    class Player:
        def __init__(self):pass
    runtime={'EmbyFlowMoviePlayer':Player}
    exec(Path(__file__).with_name('runtime.py').read_text(),runtime)
    # Verify that the real upstream function passes our structural API guard.
    code={}
    exec(compile(ast.Module(body=[picture],type_ignores=[]),'upstream_picture.py','exec'),code)
    assert runtime['_eflcd_bridge'](SimpleNamespace(LCD4linuxPIC=code['LCD4linuxPIC'])) is not None
    texts,errors=[],[]
    namespace=dict(ImageFont=SimpleNamespace(truetype=lambda *a,**kw:None),
        getProgess=lambda width,percent:width,getSplit=lambda *args:0,
        getFsize=lambda text,font:(len(text)*8,16),
        ShadowText=lambda *args:texts.append(args[3]),L4log=lambda *args:errors.append(args))
    exec(compile(ast.Module(body=[progress],type_ignores=[]),'upstream_progress.py','exec'),namespace)
    options=(400,16,100,'21','white','white','0','0',True,'off','false','false','font')
    def renderer(self,session):
        unused=(self.Llength,self.Lposition)
        namespace['self']=self
        namespace['putProgress'](options,0,0)
    module=SimpleNamespace(LCD4linuxPIC=renderer)
    session=object()
    status=SimpleNamespace(im={0:SimpleNamespace(size=(800,480))},LsreftoString='own',
        Llength=[0,86400*90000],Lposition=[0,49*60*90000])
    module.LCD4linuxPIC(status,session)
    assert texts==['+1391 min'] and not errors,(texts,errors)
    texts.clear()
    state=runtime['_eflcd_bridge'](module)
    state['snapshot']=(object(),id(session),'own',158*60*90000,49*60*90000,runtime['_eflcd_time'].monotonic())
    module.LCD4linuxPIC(status,session)
    assert texts==['+109 min'] and not errors,(texts,errors)
    assert status.Llength==[0,86400*90000]
    print('Public r36 API guard passes; original renderer +1391 min -> bridge +109 min; backend fields unchanged.')


if __name__=='__main__':main()
