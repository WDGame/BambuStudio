"""Independent test artifact checks. Never imported by the product."""
import copy
import hashlib
import io
import json
import math
import pathlib
import posixpath
import time
import uuid
import xml.etree.ElementTree as ET
import zipfile

CORE = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
NS = {'m': CORE}
PRODUCTION_PATH = '{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}path'
IDENTITY = '1 0 0 0 1 0 0 0 1 0 0 0'


class Blocked(RuntimeError):
    """An environmental prerequisite is unavailable; this is not a passing test."""


def wait_for(action, timeout=30, message='Condition timed out', interval=.15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = action()
        if value:
            return value
        time.sleep(interval)
    raise TimeoutError(message)


def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def source_hash_matches(path, expected):
    """Accept Git's LF/CRLF checkout conversion for text source receipts only."""
    data=pathlib.Path(path).read_bytes()
    lf=data.replace(b'\r\n',b'\n')
    return any(hashlib.sha256(value).hexdigest()==expected for value in (data,lf,lf.replace(b'\n',b'\r\n')))


def project_summary(path):
    """Follow build/component transforms, including split native 3MF model files."""
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None, 'Corrupt 3MF ZIP member'
        models = {name: ET.fromstring(archive.read(name)) for name in archive.namelist() if name.endswith('.model')}
        settings = json.loads(archive.read('Metadata/project_settings.config'))
        config = ET.fromstring(archive.read('Metadata/model_settings.config'))
        parts = [{'object': o.get('id'), 'id': p.get('id'), 'subtype': p.get('subtype'),
                  'metadata': {m.get('key'): m.get('value') for m in p.findall('metadata')}}
                 for o in config.findall('object') for p in o.findall('part')]
        object_settings = [{m.get('key'):m.get('value') for m in o.findall('metadata') if m.get('key')}
                           for o in config.findall('object')]
        objects = {(name, o.get('id')): o for name, model in models.items() for o in model.findall('m:resources/m:object', NS)}
        meshes = []

        def visit(entry, item, parents, ancestors):
            ref = item.get(PRODUCTION_PATH)
            if ref:
                entry = ref.lstrip('/') if ref.lstrip('/') in models else posixpath.normpath(posixpath.join(posixpath.dirname(entry), ref))
            key = (entry, item.get('objectid'))
            assert key not in ancestors, 'Cyclic 3MF component'
            matrix = list(map(float, item.get('transform', IDENTITY).split()))
            assert len(matrix) == 12 and all(map(math.isfinite, matrix)), 'Invalid 3MF transform'
            transforms = parents + [matrix]
            obj = objects[key]
            mesh = obj.find('m:mesh', NS)
            if mesh is not None:
                vertices = []
                for v in mesh.findall('m:vertices/m:vertex', NS):
                    p = [float(v.get(k)) for k in ('x', 'y', 'z')]
                    for transform in reversed(transforms):
                        p = [sum(transform[a+3*j]*p[j] for j in range(3))+transform[a+9] for a in range(3)]
                    assert all(map(math.isfinite, p)), 'Non-finite 3MF vertex'
                    vertices.append(p)
                soup = []
                for triangle in mesh.findall('m:triangles/m:triangle', NS):
                    for k in ('v1', 'v2', 'v3'):
                        index = int(triangle.get(k))
                        assert 0 <= index < len(vertices), 'Invalid 3MF vertex index'
                        soup.extend(vertices[index])
                meshes.append(soup)
            for component in obj.findall('m:components/m:component', NS):
                visit(entry, component, transforms, ancestors | {key})

        for item in models['3D/3dmodel.model'].findall('m:build/m:item', NS):
            visit('3D/3dmodel.model', item, [], set())
    return {'sha256': sha256(path), 'parts': parts, 'meshes': meshes, 'settings': settings, 'object_settings':object_settings}


def mesh_error(before, after):
    """Ignore vertex/face reindexing, compare posed triangle coordinates in mm."""
    assert len(before) == len(after), f'Triangle count changed: {len(before)//9} != {len(after)//9}'
    def triangles(soup):
        result = []
        for i in range(0, len(soup), 9):
            points = [soup[j:j+3] for j in range(i, i+9, 3)]
            points.sort(key=lambda p: tuple(round(x, 3) for x in p))
            result.append([x for point in points for x in point])
        result.sort(key=lambda t: tuple(round(x, 3) for x in t))
        return result
    return max((abs(x-y) for a, b in zip(triangles(before), triangles(after)) for x, y in zip(a, b)), default=0)


def assert_project_equal(before, after, tolerance=1e-4):
    assert len(before['meshes']) == len(after['meshes']), 'Mesh/instance count changed'
    assert [(p['metadata'].get('name'), p['subtype']) for p in before['parts']] == [
        (p['metadata'].get('name'), p['subtype']) for p in after['parts']], 'Part names/types changed'
    assert before['object_settings']==after['object_settings'], 'Object settings changed'
    error = max((mesh_error(a, b) for a, b in zip(before['meshes'], after['meshes'])), default=0)
    assert error < tolerance, f'World geometry moved by {error} mm'
    for key in ('layer_height', 'initial_layer_print_height', 'filament_type', 'filament_settings_id',
                'print_settings_id', 'printer_settings_id', 'nozzle_diameter', 'enable_support', 'support_enable'):
        assert before['settings'].get(key) == after['settings'].get(key), f'Preset setting changed: {key}'
    return {'max_position_error_mm': error, 'parts': len(after['parts']),
            'triangles': [len(m)//9 for m in after['meshes']],
            'other_settings_changed': sorted(k for k in before['settings'].keys() | after['settings'].keys()
                                             if before['settings'].get(k) != after['settings'].get(k))}


def make_project_variant(source, target, kind):
    """Alter only a synthetic project's input, never the running model or engine."""
    with zipfile.ZipFile(source) as archive:
        contents = {n: archive.read(n) for n in archive.namelist()}
    # Bambu's native importer also uses conventional tag/prefix spellings.
    # Preserve the default core namespace and original production prefixes.
    for _, (prefix, uri) in ET.iterparse(io.BytesIO(contents['3D/3dmodel.model']),events=('start-ns',)):
        ET.register_namespace(prefix,uri)
    model = ET.fromstring(contents['3D/3dmodel.model'])
    config = ET.fromstring(contents['Metadata/model_settings.config'])
    resources = model.find('m:resources', NS)
    build = model.find('m:build', NS)
    original = config.find('object')
    root_id = original.get('id')
    root_object = next(o for o in resources if o.get('id') == root_id)
    assert len(config.findall('object')) == 1 and len(original.findall('part')) == 1
    if kind in ('modifier', 'negative'):
        first = original.find('part')
        component = root_object.find('m:components/m:component', NS)
        external = component.get(PRODUCTION_PATH)
        if external:
            external_model = ET.fromstring(contents[external.lstrip('/')])
            mesh = next(o for o in external_model.find('m:resources', NS) if o.get('id') == component.get('objectid'))
        else:
            mesh = next(o for o in resources if o.get('id') == component.get('objectid'))
        identifier = str(max(int(o.get('id')) for o in resources)+1)
        cloned = copy.deepcopy(mesh); cloned.set('id', identifier); resources.append(cloned)
        component = copy.deepcopy(root_object.find('m:components/m:component', NS))
        component.attrib.pop(PRODUCTION_PATH, None)
        component.set('objectid', identifier); root_object.find('m:components', NS).append(component)
        part = copy.deepcopy(first); part.set('id', identifier)
        part.set('subtype', 'modifier_part' if kind == 'modifier' else 'negative_part')
        part.set('uuid', str(uuid.uuid5(uuid.NAMESPACE_URL, 'printfins-test/'+kind)))
        original.append(part)
    else:
        assert kind in ('two-objects', 'two-instances')
        item = copy.deepcopy(build[0])
        matrix = list(map(float, item.get('transform', IDENTITY).split())); matrix[9] += 65
        item.set('transform', ' '.join(map(str, matrix)))
        new_id = root_id
        if kind == 'two-objects':
            mapping = {o.get('id'): str(int(o.get('id'))+1000) for o in resources}
            for obj in list(resources):
                cloned = copy.deepcopy(obj)
                for node in cloned.iter():
                    for attr in ('id', 'objectid'):
                        if attr=='objectid' and node.get(PRODUCTION_PATH): continue
                        if node.get(attr) in mapping: node.set(attr, mapping[node.get(attr)])
                resources.append(cloned)
            cloned = copy.deepcopy(original)
            external_part_ids={c.get('objectid') for c in root_object.findall('m:components/m:component',NS)
                               if c.get(PRODUCTION_PATH)}
            for node in cloned.iter():
                if node.get('id') in mapping and not (node.tag=='part' and node.get('id') in external_part_ids):
                    node.set('id', mapping[node.get('id')])
                if node.get('uuid'): node.set('uuid', str(uuid.uuid5(uuid.NAMESPACE_URL, node.get('uuid')+'/second')))
                if node.get('key') == 'name': node.set('value', 'unselected-second')
            config.insert(1, cloned)
            new_id = mapping[root_id]
            item.set('objectid', new_id)
        build.append(item)
        plate = config.find('plate')
        instance = copy.deepcopy(plate.find('model_instance'))
        for meta in instance:
            if meta.get('key') == 'object_id': meta.set('value', new_id)
            if meta.get('key') == 'instance_id': meta.set('value', '1' if kind == 'two-instances' else '0')
            if meta.get('key') == 'identify_id': meta.set('value', str(int(meta.get('value'))+1000))
        plate.append(instance)
        # Assembly is an independent view; let Bambu reconstruct it from build.
        assemble = config.find('assemble')
        if assemble is not None: config.remove(assemble)
    contents['3D/3dmodel.model'] = ET.tostring(model, encoding='utf-8', xml_declaration=True)
    contents['Metadata/model_settings.config'] = ET.tostring(config, encoding='utf-8', xml_declaration=True)
    with zipfile.ZipFile(target, 'x', zipfile.ZIP_DEFLATED) as archive:
        for name, data in contents.items(): archive.writestr(name, data)


def compact_summary(summary):
    return {'sha256': summary['sha256'], 'names': [p['metadata'].get('name') for p in summary['parts']],
            'types': [p['subtype'] for p in summary['parts']], 'triangles': [len(m)//9 for m in summary['meshes']]}
