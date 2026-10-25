import re

IMPORT='    import py_compile\n'
HELPER='''    def _embyflow_update_builtin_syntax(path):
        with open(path, "rb") as handle:
            compile(handle.read(), path, "exec", dont_inherit=True)
'''


def patched(source):
    headers=list(re.finditer(r'(?m)^def _embyflow_update_install_plugin\(manifest\):\n',source))
    if len(headers)!=1:raise RuntimeError('Updater nicht eindeutig erkannt. Nichts geaendert.')
    first=headers[0].start()
    following=re.search(r'(?m)^(?:def |class )',source[headers[0].end():])
    last=headers[0].end()+following.start() if following else len(source)
    body=source[first:last]
    if IMPORT not in body:
        if ('def _embyflow_update_builtin_syntax(path):' in body and body.count('_embyflow_update_builtin_syntax(')==6):
            compile(source,'plugin.py','exec');return source
        if ('class py_compile:' in body and 'compile(handle.read(), path, "exec", dont_inherit=True)' in body):
            compile(source,'plugin.py','exec');return source
        if ('def _embyflow_update_check_python_source(path):' in source and body.count('_embyflow_update_check_python_source(')==5):
            compile(source,'plugin.py','exec');return source
        raise RuntimeError('Abweichender Updater. Nichts geaendert.')
    if body.count(IMPORT)!=1 or body.count('py_compile.compile(')!=5:
        raise RuntimeError('Erwartete fuenf Syntaxpruefungen nicht gefunden. Nichts geaendert.')
    calls=re.compile(r'py_compile\.compile\(\s*([A-Za-z_]\w*)\s*,\s*doraise\s*=\s*True\s*\)')
    if len(list(calls.finditer(body)))!=5:
        raise RuntimeError('Syntaxpruefung weicht ab. Nichts geaendert.')
    body=body.replace(IMPORT,HELPER,1)
    body=calls.sub(lambda match:'_embyflow_update_builtin_syntax('+match.group(1)+')',body)
    if 'py_compile' in body:raise RuntimeError('Weitere Modulverwendung gefunden. Nichts geaendert.')
    result=source[:first]+body+source[last:]
    compile(result,'plugin.py','exec')
    return result
