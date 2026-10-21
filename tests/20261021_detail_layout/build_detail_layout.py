from pathlib import Path
import ast
import hashlib
import re

HERE = Path(__file__).resolve().parent


def fixed_source(source):
    tree = ast.parse(source)
    replacements = {}
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name not in ('_efup_init', '_efup_bad_render', '_efread_init'):
            continue
        body = ast.get_source_segment(source, node)
        if node.name == '_efup_init':
            body = body.replace('x == 90 and 50 <= y < 1000', 'x == sx(90) and sy(50) <= y < sy(1000)')
            body = body.replace('and 50 <= y < 1000', 'and sy(50) <= y < sy(1000)')
            body = body.replace('and x < 1450', 'and x < sx(1450)')
            body = body.replace('(x, y - 30)', '(x, y - sy(30))')
            replacements[node.name] = (node, body)
        elif node.name == '_efup_bad_render':
            body = body.replace('in (325, 384)', 'in (sy(325), sy(384))')
            body = body.replace('position.y() - 30', 'position.y() - sy(30)')
            replacements[node.name] = (node, body)
        elif node.name == '_efread_init':
            body = body.replace(' % (x, y)', ' % (sx(x), sy(y))')
            body = body.replace(' % (w, h)', ' % (sx(w), sy(h))')
            body = body.replace('"Regular;24"', '"Regular;%d" % sy(24)')
            body = body.replace('"90,%d" % y', '"%d,%d" % (sx(90), sy(y))')
            body = body.replace('"150,36"', '"%d,%d" % (sx(150), sy(36))')
            replacements[node.name] = (node, body)
    if len(replacements) != 3:
        raise RuntimeError('Expected detail layout functions not found')
    lines = source.splitlines(keepends=True)
    for node, body in sorted(replacements.values(), key=lambda value: value[0].lineno, reverse=True):
        lines[node.lineno-1:node.end_lineno] = [body + '\n']
    return ''.join(lines)


def build():
    baseline = HERE / 'audio_neutral.py'
    if not baseline.exists():
        baseline = HERE.parents[1] / 'EmbyFlowE2_2026102102.py'
    source = baseline.read_text(encoding='utf-8')
    if hashlib.sha256(source.encode('utf-8')).hexdigest() != 'a3799cd2846aa6d482d8df8b6699e6f6f02d973f2256cc44ae4609d19b8723a4':
        raise RuntimeError('Published audio baseline mismatch')
    source = fixed_source(source)
    source = source.replace('2026102102', '2026102103')
    source = source.replace('2026-RCDEV-TEST-20261021-RECEIVER-AUDIO-4097',
                            '2026-RCDEV-TEST-20261021-DETAIL-HD-AUDIO-4097')
    lines = source.splitlines(keepends=True)
    changelog = 'Detailansicht: Ueberschrift und Beschreibung nutzen dieselbe HD/FHD-Skalierung; keine Ueberlagerung durch unskalierte 30-Pixel-Verschiebung.|Tonspur-Test mit 4097 und LCD-Zeitfix bleiben enthalten. Hardwaretest und UT-Test stehen noch aus.'
    for i, line in enumerate(lines):
        if line.startswith('PLUGIN_UPDATE_CHANGELOG = '):
            lines[i] = 'PLUGIN_UPDATE_CHANGELOG = ' + repr(changelog) + '\n'
    source = ''.join(lines)
    ast.parse(source, feature_version=(3, 8))
    compile(source, 'EmbyFlowE2_2026102103.py', 'exec')
    out = HERE / 'EmbyFlowE2_2026102103.py'
    out.write_bytes(source.encode('utf-8'))
    data = out.read_bytes()
    print(out.name, hashlib.sha256(data).hexdigest())
    print('git_blob', hashlib.sha1(('blob %d\0' % len(data)).encode() + data).hexdigest())


if __name__ == '__main__': build()
