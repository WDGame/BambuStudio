"""Runner/3MF-oracle unit tests. These are explicitly NOT Bambu GUI tests."""
import copy
import contextlib
import importlib.util
import io
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import zipfile

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'scripts/printfins'))
from stability_support import (CORE, assert_project_equal, make_project_variant, mesh_error, project_summary, sha256, source_hash_matches)
from windows_test_ui import WindowsUI


def make_fixture(path, split=False, cycle=False, invalid=False):
    mesh='''<object id="1" type="model"><mesh><vertices><vertex x="0" y="0" z="0"/>
        <vertex x="1" y="0" z="0"/><vertex x="0" y="1" z="0"/></vertices>
        <triangles><triangle v1="0" v2="1" v3="2"/></triangles></mesh></object>'''
    if invalid: mesh=mesh.replace('v1="0"','v1="-1"')
    ref=' p:path="/3D/Objects/part.model"' if split else ''
    if cycle: ref=''
    component=f'<object id="2" type="model"><components><component objectid="{2 if cycle else 1}"{ref} transform="0 1 0 -1 0 0 0 0 1 2 3 4"/></components></object>'
    model=f'<model xmlns="{CORE}" xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06"><resources>{"" if split else mesh}{component}</resources><build><item objectid="2" transform="1 0 0 0 1 0 0 0 1 10 20 30"/></build></model>'
    config='''<config><object id="2"><metadata key="name" value="fixture"/><metadata key="extruder" value="1"/>
        <part id="1" subtype="normal_part" uuid="synthetic"><metadata key="name" value="fixture"/></part></object>
        <plate><model_instance><metadata key="object_id" value="2"/><metadata key="instance_id" value="0"/>
        <metadata key="identify_id" value="1"/></model_instance></plate><assemble/></config>'''
    with zipfile.ZipFile(path,'x') as archive:
        archive.writestr('3D/3dmodel.model',model)
        archive.writestr('Metadata/model_settings.config',config)
        archive.writestr('Metadata/project_settings.config',json.dumps({'layer_height':'0.16','initial_layer_print_height':'0.2'}))
        if split: archive.writestr('3D/Objects/part.model',f'<model xmlns="{CORE}"><resources>{mesh}</resources></model>')


class StabilitySupportTests(unittest.TestCase):
    def setUp(self):
        self.build=pathlib.Path(__file__).resolve().parents[2]/'build'; self.build.mkdir(exist_ok=True)
        self.temporary=tempfile.TemporaryDirectory(prefix='printfins-support-',dir=self.build)
        self.root=pathlib.Path(self.temporary.name)
    def tearDown(self):
        assert self.root.resolve().parent==self.build.resolve() and self.root.name.startswith('printfins-support-')
        self.temporary.cleanup()

    def test_native_and_split_3mf_follow_nested_transforms(self):
        expected=[12,23,34,12,24,34,11,23,34]
        for split in (False,True):
            target=self.root/f'{split}.3mf'; make_fixture(target,split)
            summary=project_summary(target)
            self.assertEqual(summary['meshes'],[expected])
            self.assertEqual(summary['parts'][0]['metadata']['name'],'fixture')

    def test_mesh_comparison_allows_reindexing_but_detects_displacement(self):
        a=[0,0,0,1,0,0,0,1,0]
        b=[0,1,0,0,0,0,1,0,0]
        self.assertEqual(mesh_error(a,b),0)
        self.assertGreater(mesh_error(a,[v+.1 for v in b]),.09)
        with self.assertRaises(AssertionError): mesh_error(a,[])

    def test_roundtrip_rejects_changed_geometry_names_types_and_settings(self):
        path=self.root/'source.3mf'; make_fixture(path); before=project_summary(path)
        self.assertEqual(assert_project_equal(before,copy.deepcopy(before))['max_position_error_mm'],0)
        for field in ('geometry','name','type','setting','object-setting'):
            after=copy.deepcopy(before)
            if field=='geometry': after['meshes'][0][0]+=1
            if field=='name': after['parts'][0]['metadata']['name']='renamed'
            if field=='type': after['parts'][0]['subtype']='negative_part'
            if field=='setting': after['settings']['layer_height']='0.2'
            if field=='object-setting': after['object_settings'][0]['extruder']='2'
            with self.assertRaises(AssertionError,msg=field): assert_project_equal(before,after)

    def test_invalid_3mf_cycles_and_vertex_indices_are_detected(self):
        for kind in ('cycle','index'):
            target=self.root/f'{kind}.3mf'; make_fixture(target,cycle=kind=='cycle',invalid=kind=='index')
            with self.assertRaises(AssertionError): project_summary(target)

    def test_model_variants_preserve_source_and_create_intended_inputs(self):
        for split in (False,True):
            source=self.root/f'source-{split}.3mf'; make_fixture(source,split)
            digest=sha256(source)
            for kind in ('two-objects','two-instances','modifier','negative'):
                target=self.root/f'{split}-{kind}.3mf'; make_project_variant(source,target,kind)
                with zipfile.ZipFile(target) as archive:
                    xml=archive.read('3D/3dmodel.model').decode()
                    self.assertIn('<model ',xml)
                    self.assertNotIn('<ns0:model',xml)
                    if split: self.assertIn('p:path=',xml)
                summary=project_summary(target)
                self.assertEqual(len(summary['meshes']),2)
                self.assertEqual(len(summary['parts']),1 if kind=='two-instances' else 2)
                if kind in ('modifier','negative'): self.assertEqual(summary['parts'][-1]['subtype'],kind+'_part')
                self.assertEqual(sha256(source),digest)

    def test_fixture_writer_refuses_overwriting_existing_evidence(self):
        source=self.root/'source.3mf'; make_fixture(source)
        target=self.root/'protected.3mf'; target.write_bytes(b'preserve')
        with self.assertRaises(FileExistsError): make_project_variant(source,target,'two-objects')
        self.assertEqual(target.read_bytes(),b'preserve')

    def test_source_receipts_allow_checkout_newlines_but_reject_code_changes(self):
        path=self.root/'source.cpp'; path.write_bytes(b'first\nsecond\n'); lf=sha256(path)
        path.write_bytes(b'first\r\nsecond\r\n'); crlf=sha256(path)
        self.assertTrue(source_hash_matches(path,lf))
        path.write_bytes(b'first\nsecond\n')
        self.assertTrue(source_hash_matches(path,crlf))
        path.write_bytes(b'first\nchanged\n')
        self.assertFalse(source_hash_matches(path,lf))
        self.assertFalse(source_hash_matches(path,crlf))

    def test_split_variant_keeps_external_ids_when_root_ids_overlap(self):
        source=self.root/'overlapping-ids.3mf'; make_fixture(source,split=True)
        with zipfile.ZipFile(source) as archive:
            contents={name:archive.read(name) for name in archive.namelist()}
        # Root and external resources can both legally use ID 1.
        contents['3D/3dmodel.model']=contents['3D/3dmodel.model'].replace(b'id="2"',b'id="1"')
        contents['Metadata/model_settings.config']=contents['Metadata/model_settings.config'].replace(b'id="2"',b'id="1"').replace(b'value="2"',b'value="1"')
        overlapped=self.root/'overlapped.3mf'
        with zipfile.ZipFile(overlapped,'x') as archive:
            for name,data in contents.items(): archive.writestr(name,data)
        target=self.root/'two-objects.3mf'; make_project_variant(overlapped,target,'two-objects')
        summary=project_summary(target)
        self.assertEqual(len(summary['meshes']),2)
        self.assertEqual([p['id'] for p in summary['parts']],['1','1'])

    def menu_ui(self, entries):
        # Test the regression at the driver boundary: actual popup activation,
        # rather than synthetic WM_COMMAND after destroying the menu context.
        ui=WindowsUI.__new__(WindowsUI)
        ui.menu=Mock(return_value=entries); ui.dismiss_menu=Mock()
        ui.click_menu_item=Mock(); ui.record=Mock()
        return ui

    def test_menu_commands_activate_live_popup_and_submenus(self):
        leaf={'text':'Export G-code','enabled':True,'id':465}
        parent={'text':'Export','enabled':True,'id':0xffffffff,'children':[leaf]}
        ui=self.menu_ui([parent])
        self.assertTrue(ui.command('Export G-code',file=True))
        ui.menu.assert_called_once_with(True,close=False)
        self.assertEqual([c.args[0] for c in ui.click_menu_item.call_args_list],[parent,leaf])
        ui.dismiss_menu.assert_not_called()

    def test_unavailable_menu_commands_close_popup_without_dispatching(self):
        for entries in ([],[{'text':'Save Project as','enabled':False,'id':455}]):
            ui=self.menu_ui(entries)
            if entries: self.assertFalse(ui.command('Save Project as',file=True,required=False))
            else:
                with self.assertRaisesRegex(RuntimeError,'entry unavailable'):
                    ui.command('Save Project as',file=True)
            ui.dismiss_menu.assert_called_once()
            ui.click_menu_item.assert_not_called()

    def focus_ui(self):
        ui=WindowsUI.__new__(WindowsUI); ui.pid=123; ui.u=Mock(); ui.record=Mock()
        ui.owner=lambda hwnd:123 if hwnd in (10,11) else 999
        ui.u.GetAncestor.return_value=10; ui.u.IsIconic.return_value=False
        ui.u.GetForegroundWindow.return_value=11
        return ui

    def test_active_visible_windows_keep_geometry_and_focus(self):
        ui=self.focus_ui(); ui.foreground(10)
        ui.u.ShowWindow.assert_not_called(); ui.u.SetForegroundWindow.assert_not_called()

    def test_minimized_window_restores_and_waits_for_activation(self):
        ui=self.focus_ui(); ui.u.IsIconic.return_value=True
        ui.u.GetForegroundWindow.side_effect=[99,99,10]
        with patch('stability_support.time.sleep'): ui.foreground(10)
        ui.u.ShowWindow.assert_called_once_with(10,9)
        ui.u.SetForegroundWindow.assert_called_once_with(10)

    def test_denied_focus_stays_blocked_without_repeated_activation(self):
        ui=self.focus_ui(); ui.u.GetForegroundWindow.return_value=99; ui.describe=Mock(return_value={})
        with patch('windows_test_ui.wait_for',side_effect=TimeoutError):
            with self.assertRaisesRegex(RuntimeError,'Cannot focus'): ui.foreground(10)
        ui.u.SetForegroundWindow.assert_called_once_with(10)
        ui.u.ShowWindow.assert_not_called()

    def test_submenus_hover_and_leaf_items_click(self):
        for submenu in (False,True):
            ui=WindowsUI.__new__(WindowsUI); ui.u=Mock(); ui.popup=Mock(return_value=20)
            ui.point=Mock(); ui.click=Mock()
            def rectangle(_,menu,index,rect):
                rect._obj.left=100; rect._obj.right=180; rect._obj.top=200; rect._obj.bottom=220
                return True
            ui.u.GetMenuItemRect.side_effect=rectangle
            ui.u.ClientToScreen.return_value=True
            item={'menu':21,'index':2}
            if submenu: item['children']=[{'menu':22}]
            ui.click_menu_item(item)
            if submenu:
                ui.point.assert_called_once_with(20,140,210); ui.click.assert_not_called()
                self.assertEqual(ui.popup.call_args_list[-1].args,(22,))
            else:
                ui.click.assert_called_once_with(20,140,210); ui.point.assert_not_called()

    def test_missing_popup_is_inconclusive_and_keeps_window_evidence(self):
        ui=WindowsUI.__new__(WindowsUI); ui.snapshot=Mock(); ui.log=self.root/'native-ui.jsonl'
        with patch('windows_test_ui.wait_for',side_effect=TimeoutError):
            with self.assertRaisesRegex(RuntimeError,'automation inconclusive'): ui.popup(21)
        ui.snapshot.assert_called_once_with(self.root/'menu-unavailable.json')

    def runner(self):
        path=pathlib.Path(__file__).resolve().parents[2]/'scripts/printfins/run-stability.py'
        spec=importlib.util.spec_from_file_location('printfins_stability_runner',path)
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        return module

    def test_report_handles_empty_errors_and_keeps_blocked_and_failed_distinct(self):
        runner=self.runner(); report=runner.Report(self.root)
        with contextlib.redirect_stdout(io.StringIO()):
            report.record('pass','unit','PASS',error='')
            report.run('blocked','unit',lambda _ : (_ for _ in ()).throw(runner.Blocked('desktop unavailable')))
            report.run('failed','unit',lambda _ : (_ for _ in ()).throw(AssertionError('expected test failure')))
        result=json.loads((self.root/'report.json').read_text())
        self.assertEqual(result['counts'],{'PASS':1,'BLOCKED':1,'FAIL':1})
        self.assertIn('desktop unavailable',(self.root/'report.md').read_text())
        self.assertTrue((self.root/'failed/failure.log').is_file())

    def test_report_rejects_an_unknown_status(self):
        report=self.runner().Report(self.root)
        with self.assertRaises(AssertionError): report.record('unknown','unit','MAYBE')

    def test_forced_cleanup_cannot_turn_a_failed_shutdown_into_a_pass(self):
        report=self.runner().Report(self.root)
        def action(folder):
            (folder/'cleanup.json').write_text(json.dumps({'forced':True,'exit_code':1}))
            return {'geometry':'passed'}
        with contextlib.redirect_stdout(io.StringIO()): result=report.run('shutdown','unit',action)
        self.assertEqual(result['status'],'FAIL')
        self.assertIn('did not close cleanly',result['error'])


if __name__=='__main__': unittest.main(verbosity=2)
