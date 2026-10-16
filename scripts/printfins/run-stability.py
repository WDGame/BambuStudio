"""One-command, isolated Windows stability run. No product or engine modifications."""
import argparse
import collections
import datetime
import json
import os
import pathlib
import queue
import re
import socket
import subprocess
import sys
import threading
import time
import traceback
import unittest
import xml.etree.ElementTree as ET
import zipfile

from stability_support import (Blocked, assert_project_equal, compact_summary, make_project_variant,
                               mesh_error, project_summary, sha256, source_hash_matches, wait_for)

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / 'scripts/printfins'
HIDDEN = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')


class Cdp:
    def __init__(self, port, directory):
        self.stderr = (directory/'cdp-stderr.log').open('w', encoding='utf-8')
        self.process = subprocess.Popen(['node',str(SCRIPTS/'stability-cdp.mjs'),str(port),str(directory)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.stderr, text=True, encoding='utf-8', **HIDDEN)
        self.lines, self.sequence = queue.Queue(), 0
        def read():
            for line in self.process.stdout: self.lines.put(line)
            self.lines.put(None)
        threading.Thread(target=read, daemon=True).start()

    def call(self, method, **params):
        self.sequence += 1
        self.process.stdin.write(json.dumps({'id':self.sequence,'method':method,**params})+'\n'); self.process.stdin.flush()
        try: line = self.lines.get(timeout=20)
        except queue.Empty: raise TimeoutError('CDP test driver did not respond: '+method)
        if line is None: raise RuntimeError('CDP driver exited; see cdp-stderr.log')
        response = json.loads(line)
        assert response['id'] == self.sequence, 'Unexpected CDP response'
        if not response['ok']: raise RuntimeError(response['error'])
        return response.get('result')

    def evaluate(self, expression):
        return self.call('evaluate', expression=expression)

    def close(self):
        self.process.stdin.close()
        try: self.process.wait(timeout=5)
        except subprocess.TimeoutExpired: self.process.terminate(); self.process.wait(timeout=5)
        self.process.stdout.close(); self.stderr.close()


class Session:
    def __init__(self, args, directory, source):
        from windows_test_ui import WindowsUI
        self.args, self.directory, self.cdp = args, directory, None
        with (directory/'prepare.log').open('w',encoding='utf-8') as log:
            subprocess.run([sys.executable,str(SCRIPTS/'prepare-run.py'),str(directory/'data'),
                '--profile-template',str(args.profile_template)], stdout=log, stderr=subprocess.STDOUT, check=True, **HIDDEN)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0)); self.port = sock.getsockname()[1]
        env = {k:v for k,v in os.environ.items() if not k.startswith('BBS_PRINTFINS_POC_')}
        env['WEBVIEW2_USER_DATA_FOLDER'] = str(directory/'webview-profile')
        env['WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS'] = (f'--remote-debugging-address=127.0.0.1 --remote-debugging-port={self.port} '
            f'--enable-logging --log-file="{directory / "webview.log"}"')
        self.stdout = (directory/'native-stdout.log').open('w',encoding='utf-8')
        self.process = subprocess.Popen([str(args.exe),'--datadir',str(directory/'data/profile'),str(source)],
            cwd=directory, env=env, stdout=self.stdout, stderr=subprocess.STDOUT)
        write_json(directory/'launch.json',{'pid':self.process.pid,'exe':str(args.exe),'source':str(source),
            'profile':'data/profile','cdp_loopback_port':self.port})
        try: self.ui = WindowsUI(self.process.pid,directory/'native-ui.jsonl')
        except Exception:
            self.process.terminate(); self.process.wait(timeout=5); self.stdout.close(); raise

    def ready(self):
        def loaded():
            if self.process.poll() is not None: raise RuntimeError('Bambu exited during startup: '+str(self.process.returncode))
            return self.ui.main() and self.ui.u.IsWindowEnabled(self.ui.main()) and any(
                'finished load_model_objects' in p.read_text(encoding='utf-8',errors='replace')
                for p in (self.directory/'data/profile/log').glob('studio*'))
        wait_for(loaded,self.args.startup_timeout,'Model did not finish loading')
        self.ui.foreground(self.ui.main())
        self.ui.command('Select all')
        time.sleep(.25)

    def tool(self):
        return next((w['handle'] for w in self.ui.windows() if w['text']=='PrintFins'
                     and self.ui.find_control('Cancel',w['handle'])),None)

    def message(self):
        return next((w['handle'] for w in self.ui.windows() if w['text']=='PrintFins' and w['handle']!=self.tool()),None)

    def save(self, name):
        target = self.directory/(name+'.3mf')
        assert not target.exists(), 'Refusing to overwrite test artifacts'
        self.ui.command('Save Project as',file=True)
        self.ui.file_dialog(target)
        def complete():
            if not target.exists(): return False
            try: return project_summary(target)
            except (OSError,ValueError,KeyError,ET.ParseError,zipfile.BadZipFile): return False
        return wait_for(complete,30,'Native project save did not complete')

    def open_tool(self, mode='normal'):
        self.ui.command('PrintFins')
        wait_for(self.tool,10,'PrintFins settings dialog not found')
        if not self.cdp: self.cdp = Cdp(self.port,self.directory)
        deadline = time.monotonic()+35
        last = ''
        while time.monotonic()<deadline:
            try:
                self.cdp.call('attach',mode=mode)
                if self.cdp.evaluate("Boolean(document.getElementById('generate') && !document.getElementById('generate').disabled)"):
                    try: self.cdp.call('screenshot')
                    except RuntimeError as error:
                        with (self.directory/'capture-warning.log').open('a',encoding='utf-8') as log: log.write(str(error)+'\n')
                    return
            except RuntimeError as error: last=str(error)
            time.sleep(.2)
        if (self.directory/'webview.log').exists() and 'exit_code=-1073741790' in (self.directory/'webview.log').read_text(errors='replace'):
            raise Blocked('WebView2 GPU process denied (0xC0000022); no workaround attempted')
        raise TimeoutError('PrintFins WebView not ready: '+last)

    def configure(self, options):
        self.cdp.evaluate('(() => { const values='+json.dumps(options)+''';
            for(const [key,value] of Object.entries(values)) {
                const input=document.getElementById(key); if(!input) throw new Error('Missing setting '+key);
                if(input.type==='checkbox') input.checked=value; else input.value=String(value);
                input.dispatchEvent(new Event('input',{bubbles:true})); input.dispatchEvent(new Event('change',{bubbles:true}));
            } return true; })()''')

    def trace(self):
        path=self.directory/'trace.jsonl'
        if not path.exists(): return []
        result=[]
        for line in path.read_text(encoding='utf-8').splitlines():
            try: result.append(json.loads(line))
            except json.JSONDecodeError: pass  # Last append may still be in progress.
        return result

    def submit(self):
        try: self.cdp.evaluate("document.getElementById('generate').click(); true")
        except RuntimeError as error:
            if 'target closed' not in str(error).lower() or not any(e.get('action')=='computing' for e in self.trace()): raise

    def generated(self, expected):
        def done():
            message=self.message()
            if message:
                text=self.ui.dialog_text(message)
                if 'generated no geometry' in text:
                    assert expected=='empty',text
                    button=self.ui.find_control('OK',message)
                    if not button: button=self.ui.u.GetDlgItem(message,1)
                    self.ui.click(button); return 'empty'
                raise AssertionError('Unexpected PrintFins message: '+text)
            if not self.tool(): return 'generated'
            text=self.ui.dialog_text(self.tool())
            if any(x in text for x in ('discarded','failed','Invalid','Non-finite','timed out','[json.exception')):
                raise AssertionError('Native PrintFins failure: '+text)
            return False
        outcome=wait_for(done,135,'PrintFins did not finish')
        wait_for(lambda:not self.tool(),5,'PrintFins did not close')
        assert any(e.get('kind')=='engine-result' and e.get('ok') for e in self.trace()),'Missing real worker result'
        return outcome

    def close(self):
        # Only this newly started synthetic test process may be closed/terminated.
        cleanup={'forced':False,'pid':self.process.pid}
        try:
            self.ui.snapshot(self.directory/'windows-final.json')
            if self.cdp: self.cdp.close()
            for window in self.ui.windows():
                if window['text']=='PrintFins': self.ui.close_dialog(window['handle'])
            if self.ui.main(): self.ui.close_dialog(self.ui.main())
            deadline=time.monotonic()+15
            while self.process.poll() is None and time.monotonic()<deadline:
                for window in self.ui.windows():
                    if 'Save' in window['text'] and 'unsaved changes' in self.ui.dialog_text(window['handle']):
                        no=self.ui.find_control('No',window['handle'])
                        if no: self.ui.click(no)
                time.sleep(.1)
            if self.process.poll() is None:
                cleanup['forced']=True; self.process.terminate(); self.process.wait(timeout=5)
            cleanup['exit_code']=self.process.returncode
        except Exception as error:
            cleanup['error']=str(error)
            if self.process.poll() is None: cleanup['forced']=True; self.process.terminate(); self.process.wait(timeout=5)
        finally:
            self.stdout.close(); write_json(self.directory/'cleanup.json',cleanup)


def check_generated(session, before, after):
    request_file=sorted(session.directory.glob('request-*.json'))[-1]
    replay=session.directory/'engine-replay.json'
    script="import fs from 'node:fs'; const {generate}=await import(process.argv[1]); fs.writeFileSync(process.argv[3],JSON.stringify(generate(JSON.parse(fs.readFileSync(process.argv[2],'utf8')))));"
    with (session.directory/'replay.log').open('w') as log:
        subprocess.run(['node','--input-type=module','-e',script,(ROOT/'resources/printfins/adapter.mjs').as_uri(),str(request_file),str(replay)],
            stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60,**HIDDEN)
    request=json.loads(request_file.read_text()); engine=json.loads(replay.read_text())
    assert len(after['parts'])==len(before['parts'])+len(engine['pieces'])
    source_after={**after,'parts':after['parts'][:len(before['parts'])],'meshes':after['meshes'][:len(before['meshes'])]}
    original=assert_project_equal(before,source_after)
    assert mesh_error(request['positions'],after['meshes'][0])<1e-4,'Captured C++ input differs from saved source'
    errors=[]
    for index,piece in enumerate(engine['pieces'],len(before['meshes'])):
        expected=[]
        for a,b in piece['ranges']:
            expected.extend(value-engine['offset'][('x','y','z')[i%3]] for i,value in enumerate(engine['triangles'][a*9:b*9]))
        error=mesh_error(expected,after['meshes'][index]); assert error<1e-4,('Fin placement changed',error)
        errors.append(error)
    assert all(p['subtype']=='normal_part' for p in after['parts'])
    return {'original':original,'max_fin_position_error_mm':max(errors,default=0),'generated':compact_summary(after)}


def slice_export(session, suffix):
    # A real exported toolpath, not only an enabled Slice button, proves slicing.
    button=session.ui.find_control('Slice plate')
    if not button: raise Blocked('Native Slice plate control not found')
    session.ui.click(button)
    wait_for(lambda:session.ui.command('Export G-code',file=True,required=False),session.args.slice_timeout,'Toolpath did not become exportable',interval=1)
    target=session.directory/(suffix+'.gcode'); session.ui.file_dialog(target)
    wait_for(lambda:target.exists() and target.stat().st_size>1000 and
             '; EXECUTABLE_BLOCK_END' in target.read_text(encoding='utf-8',errors='replace')[-200:],30,'No complete exported G-code')
    text=target.read_text(encoding='utf-8',errors='replace')
    layers=re.search(r'^; total layer number: (\d+)',text,re.M)
    assert layers and int(layers[1])>0 and 'BambuStudio' in text[:200],'No valid Bambu layer/toolpath header'
    assert re.search(r'^G[01] .*E[0-9]',text,re.M),'No extrusion moves in exported toolpath'
    return {'sha256':sha256(target),'bytes':target.stat().st_size,'layers':int(layers[1])}


def reject_tool(session, expected):
    session.ui.command('PrintFins')
    message=wait_for(session.message,10,'Selection/duplicate rejection dialog not shown')
    text=session.ui.dialog_text(message)
    assert expected.lower() in text.lower(),text
    button=session.ui.find_control('OK',message) or session.ui.u.GetDlgItem(message,1)
    session.ui.click(button)
    wait_for(lambda:not session.message(),5,'Rejection dialog did not close')
    assert not session.tool(),'Rejected input unexpectedly opened the tool'
    return text


def gui_scenario(session, scenario, fixture):
    before=session.save('before')
    if scenario=='fresh-process-roundtrip':
        expected=project_summary(pathlib.Path(fixture['source_project']))
        loaded=assert_project_equal(expected,before)
        assert any(p['metadata'].get('name','').startswith('PrintFins ') for p in before['parts'])
        rejection=reject_tool(session,'already contains PrintFins')
        gcode=slice_export(session,'fresh-process-slice')
        return {'fresh_process_loaded':loaded,'duplicate_rejection':rejection,'slice':gcode,
                'resaved':assert_project_equal(before,session.save('fresh-process-resaved'))}
    if scenario.startswith('reject-'):
        if scenario=='reject-no-selection': session.ui.command('Deselect all')
        expected={'reject-no-selection':'Select one complete','reject-multiple-selection':'Select one complete',
                  'reject-two-instances':'one instance','reject-modifier':'modifiers','reject-negative':'modifiers',
                  'reject-oversized':'100000 input triangles'}[scenario]
        if scenario=='reject-oversized' and sum(len(m)//9 for m in before['meshes'])<=100000:
            raise Blocked('Bambu repaired/reduced the oversized fixture; input-limit scenario inconclusive')
        reason=reject_tool(session,expected)
        return {'rejection':reason,**assert_project_equal(before,session.save('after-rejection'))}
    if scenario=='single-with-neighbour':
        # Use the OS accessibility selection path, never set C++ selection directly.
        control=session.ui.find_control('Objects')
        if control: session.ui.click(control)
        with (session.directory/'uia-selection.log').open('w',encoding='utf-8') as log:
            try:
                result=subprocess.run(['powershell.exe','-NoProfile','-File',str(SCRIPTS/'select-test-object.ps1'),
                    '-TargetProcessId',str(session.process.pid),'-MainWindow',str(session.ui.main()),'-ObjectName',
                    before['parts'][0]['metadata']['name']],stdout=log,stderr=subprocess.STDOUT,timeout=20,**HIDDEN)
            except subprocess.TimeoutExpired: raise Blocked('Native UI Automation provider did not respond within 20 seconds')
        if result.returncode: raise Blocked('Native model selection not exposed through UI Automation; see uia-selection.log')
    mode=scenario if scenario in ('malformed-output','worker-post-failure') else 'normal'
    session.open_tool(mode)
    session.configure(fixture['options'])
    if scenario in ('cancel-before-submit','repeated-cancel','invalid-options'):
        if scenario=='invalid-options':
            for value in ['5','-1','']:
                session.configure({'gap':value}); session.submit()
                assert session.cdp.evaluate("!document.getElementById('gap').checkValidity()"),'Invalid gap accepted by HTML control'
                assert not any(e.get('kind')=='request' for e in session.trace()),'Invalid input reached worker'
        session.ui.click(session.ui.find_control('Cancel',session.tool()))
        wait_for(lambda:not session.tool(),5,'Cancel did not close settings')
        if scenario=='repeated-cancel':
            for method in ('escape','close'):
                session.open_tool()
                if method=='escape':
                    session.cdp.evaluate("document.getElementById('gap').focus(); true")
                    session.ui.keys(0x1b)
                else: session.ui.close_dialog(session.tool())
                wait_for(lambda:not session.tool(),5,'Repeated close did not finish')
        assert not any(e.get('kind')=='request' for e in session.trace()),'Generation started without a valid submit'
        return assert_project_equal(before,session.save('after-cancel'))
    session.submit()
    if scenario=='cancel-during-worker':
        wait_for(lambda:session.tool() and 'Generating PrintFins' in session.ui.dialog_text(session.tool()),5,'Native computing state not observed')
        assert any(e.get('kind')=='worker-created' for e in session.trace()),'No real worker was created'
        if any(e.get('kind')=='engine-result' for e in session.trace()):
            raise Blocked('Worker finished before cancellation; timing scenario inconclusive')
        requested=time.time()
        session.ui.click(session.ui.find_control('Cancel',session.tool()))
        wait_for(lambda:not session.tool(),5,'Cancel did not close a computing tool')
        after=session.save('after-worker-cancel')
        first=assert_project_equal(before,after)
        time.sleep(2)
        late=assert_project_equal(before,session.save('after-late-result-check'))
        assert not any(e.get('kind')=='engine-result' and e['time']<requested*1000 for e in session.trace()),'Cancellation lost the worker-result race'
        return {'real_worker_started':True,'cancel_requested_at':requested,'immediate':first,'late_result_check':late,
                'note':'Cancellation after the native computing state; no worker or engine was substituted.'}
    if mode!='normal':
        expected='[json.exception' if mode=='malformed-output' else 'Injected test worker post failure'
        wait_for(lambda:session.tool() and expected in session.ui.dialog_text(session.tool()),20,'Injected error was not reported by C++')
        error=session.ui.dialog_text(session.tool())
        session.ui.click(session.ui.find_control('Cancel',session.tool()))
        wait_for(lambda:not session.tool(),5,'Error dialog did not close')
        return {'native_error':error,**assert_project_equal(before,session.save('after-injected-error'))}
    session.generated(fixture['expected'])
    after=session.save('generated')
    if scenario=='single-with-neighbour':
        # Native export may reorder objects; identify the unaffected model by its
        # preserved name and triangle soup rather than assuming its position.
        assert len(before['meshes'])==2 and len(before['parts'])==2
        untouched=before['meshes'][1]
        assert any(len(mesh)==len(untouched) and mesh_error(untouched,mesh)<1e-4 for mesh in after['meshes']), 'Unselected object changed'
        request=json.loads(sorted(session.directory.glob('request-*.json'))[-1].read_text())
        assert len(request['positions'])==len(before['meshes'][0]),'Wrong/multiple objects were submitted'
        assert len(after['parts'])>2
        return {'unselected_model_preserved':True,'before':compact_summary(before),'after':compact_summary(after)}
    geometry=check_generated(session,before,after)
    if scenario=='duplicate-generation':
        session.ui.command('Select all')
        reason=reject_tool(session,'already contains PrintFins')
        return {'geometry':geometry,'rejection':reason,**assert_project_equal(after,session.save('after-duplicate'))}
    if scenario=='undo-redo':
        session.ui.command('Undo'); time.sleep(.3)
        undo=assert_project_equal(before,session.save('undone'))
        session.ui.command('Redo'); time.sleep(.3)
        redo=assert_project_equal(after,session.save('redone'))
        return {'geometry':geometry,'undo':undo,'redo':redo}
    gcode=slice_export(session,'first-slice')
    saved=session.save('sliced-project')
    assert_project_equal(after,saved)
    # Opening a freshly saved project must not trigger an unsaved-project prompt.
    def import_count():
        return sum(p.read_text(encoding='utf-8',errors='replace').count('finished load_model_objects')
                   for p in (session.directory/'data/profile/log').glob('studio*'))
    count=import_count()
    session.ui.command('Open Project',file=True); session.ui.file_dialog(session.directory/'sliced-project.3mf',save=False)
    wait_for(lambda:import_count()>count and session.ui.u.IsWindowEnabled(session.ui.main()),session.args.startup_timeout,'3MF GUI reopen did not complete')
    reopened=session.save('reopened-project')
    roundtrip=assert_project_equal(saved,reopened)
    # Explicitly return to Prepare before invoking the tool on saved fin parts.
    prepare=session.ui.find_control('Prepare')
    if prepare: session.ui.click(prepare)
    session.ui.command('Select all')
    if fixture['expected']=='generated': reject_tool(session,'already contains PrintFins')
    sliced_again=slice_export(session,'reopened-slice')
    return {'geometry':geometry,'slice':gcode,'roundtrip':roundtrip,'reopened_slice':sliced_again}


class Report:
    def __init__(self, directory):
        self.directory=directory
        self.data={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'maintainer_confirmed':['new GUI fin generation','joint slicing','native 3MF save and GUI reopen'],
            'confirmation_source':'Maintainer message; retained as manual evidence, not counted as automated passes',
            'cases':[]}

    def save(self):
        self.data['counts']=dict(collections.Counter(c['status'] for c in self.data['cases']))
        write_json(self.directory/'report.json',self.data)
        lines=['# PrintFins stability results','',str(self.data['counts']),'',
               '| Scenario | Kind | Result | Error |','| --- | --- | --- | --- |']
        for case in self.data['cases']:
            error=case.get('error','').replace('\n',' ').replace('|','/')[:220]
            lines.append(f"| {case['name']} | {case['kind']} | {case['status']} | {error} |")
        (self.directory/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

    def record(self, name, kind, status, **details):
        assert status in ('PASS','FAIL','BLOCKED','NOT_RUN'), 'Unknown test result status'
        case={'name':name,'kind':kind,'status':status,**details}; self.data['cases'].append(case); self.save()
        print(f"[{status}] {name}"+(f": {details['error'].splitlines()[0][:160]}" if details.get('error') else ''),flush=True)
        return case

    def run(self, name, kind, action):
        directory=self.directory/name.replace('/','-'); directory.mkdir()
        started=time.monotonic()
        details={}
        try:
            details['result']=action(directory)
            status='PASS'
            cleanup_file=directory/'cleanup.json'
            if cleanup_file.exists():
                cleanup=json.loads(cleanup_file.read_text())
                details['cleanup']=cleanup
                if cleanup.get('forced') or cleanup.get('error') or cleanup.get('exit_code')!=0:
                    raise RuntimeError('Test-owned Bambu process did not close cleanly; see cleanup.json')
        except Blocked as error: status='BLOCKED'; details['error']=str(error)
        except KeyboardInterrupt:
            self.record(name,kind,'NOT_RUN',error='Interrupted by user'); raise
        except Exception as error:
            status='FAIL'; details['error']=str(error)
            (directory/'failure.log').write_text(traceback.format_exc(),encoding='utf-8')
        case=self.record(name,kind,status,seconds=round(time.monotonic()-started,3),logs=str(directory.relative_to(self.directory)),**details)
        write_json(directory/'result.json',case)
        return case


def automated_checks(report):
    directory=report.directory/'automated'; directory.mkdir()
    tests=['tests/printfins/adapter.test.mjs','tests/printfins/settings.test.mjs','tests/printfins/stability-engine.test.mjs']
    with (directory/'node.log').open('w') as log:
        result=subprocess.run(['node','--test','--test-reporter=junit','--test-reporter-destination='+str(directory/'node.xml'),*tests],
            cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=120,**HIDDEN)
    if (directory/'node.xml').exists():
        testcases=ET.parse(directory/'node.xml').findall('.//testcase')
        if not testcases: report.record('node/test-process','engine_adapter','FAIL',error='JUnit report contains no tests')
        for case in testcases:
            error=case.find('failure')
            if error is None: error=case.find('error')
            name=case.get('name')
            kind='simulated_DOM_worker' if name.startswith(('dialog controls','original dependencies','percent fields','tool waits')) else 'engine_adapter'
            report.record('node/'+name,kind,'FAIL' if error is not None else 'NOT_RUN' if case.find('skipped') is not None else 'PASS',
                error='' if error is None else ''.join(error.itertext()),logs='automated/node.xml')
    else: report.record('node/test-process','engine_adapter','FAIL',error='No JUnit report; see automated/node.log')
    if result.returncode and not any(c['status']=='FAIL' for c in report.data['cases']):
        report.record('node/test-process','engine_adapter','FAIL',error='Node exited '+str(result.returncode))
    class Results(unittest.TextTestResult):
        def addSuccess(self,test): super().addSuccess(test); report.record(test.id(),'test_infrastructure_unit','PASS',logs='automated/python.log')
        def addFailure(self,test,error):
            super().addFailure(test,error); report.record(test.id(),'test_infrastructure_unit','FAIL',error=self._exc_info_to_string(error,test),logs='automated/python.log')
        def addError(self,test,error):
            super().addError(test,error); report.record(test.id(),'test_infrastructure_unit','FAIL',error=self._exc_info_to_string(error,test),logs='automated/python.log')
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests/printfins'),pattern='test_*.py')
    with (directory/'python.log').open('w',encoding='utf-8') as stream:
        unittest.TextTestRunner(stream=stream,resultclass=Results,verbosity=2).run(suite)
    def provenance(folder):
        with (folder/'snapshot.log').open('w') as log:
            subprocess.run([sys.executable,str(SCRIPTS/'check-snapshot.py')],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,**HIDDEN)
        return {'original_files':44}
    report.run('source/provenance','source_hashes',provenance)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe',type=pathlib.Path,default=ROOT/'build/runtime/bambu-studio.exe')
    parser.add_argument('--profile-template',type=pathlib.Path,default=ROOT/'build/ui-smoke/profile')
    parser.add_argument('--output',type=pathlib.Path)
    parser.add_argument('--no-gui',action='store_true',help='Run unit/engine checks; mark all desktop scenarios NOT_RUN')
    parser.add_argument('--startup-timeout',type=int,default=60)
    parser.add_argument('--slice-timeout',type=int,default=180)
    args=parser.parse_args()
    args.exe=args.exe.resolve(); args.profile_template=args.profile_template.resolve()
    destination=args.output or ROOT/'build'/('stability-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    destination=destination.resolve()
    destination.mkdir(parents=True,exist_ok=False)  # No deletion/reuse of previous evidence.
    report=Report(destination)
    try:
        report.data['commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        report.data['git_status']=subprocess.check_output(['git','status','--short','--branch'],cwd=ROOT,text=True)
        automated_checks(report)
        fixtures_dir=destination/'fixtures'
        subprocess.run(['node',str(ROOT/'tests/printfins/geometry-fixtures.mjs'),str(fixtures_dir)],check=True,timeout=30,**HIDDEN)
        fixtures=json.loads((fixtures_dir/'manifest.json').read_text())
        base=next(f for f in fixtures if f['id']=='tilted-box')
        scenarios=[('geometry-'+f['id'],'geometry',f,None) for f in fixtures if not f['cancelOnly'] and not f['rejectOnly']]
        scenarios += [(name,name,next(f for f in fixtures if f['id']=='cancel-grid') if name=='cancel-during-worker' else base,None)
            for name in ('invalid-options','cancel-before-submit','cancel-during-worker','repeated-cancel','duplicate-generation','undo-redo')]
        scenarios += [(name,name,base,variant) for name,variant in [('reject-no-selection',None),('reject-multiple-selection','two-objects'),
            ('reject-two-instances','two-instances'),('reject-modifier','modifier'),('reject-negative','negative'),('single-with-neighbour','two-objects')]]
        scenarios += [(mode,mode,base,None) for mode in ('malformed-output','worker-post-failure')]
        scenarios.append(('fresh-process-roundtrip','fresh-process-roundtrip',base,'generated-project'))
        scenarios.append(('reject-oversized','reject-oversized',next(f for f in fixtures if f['rejectOnly']),None))
        def preflight(folder):
            from windows_test_ui import WindowsUI
            if not args.exe.is_file(): raise Blocked('Test executable missing; supply --exe or build this checkout')
            if not (args.profile_template/'system').is_dir(): raise Blocked('Public preset template missing; supply --profile-template')
            websocket=subprocess.check_output(['node','-p','typeof WebSocket'],text=True,**HIDDEN).strip()
            if websocket!='function': raise Blocked('Node 22+ with built-in WebSocket is required for CDP')
            WindowsUI(os.getpid(),folder/'input-check.jsonl').preflight_input()
            receipt=args.exe.parent.parent/'native/validation.json'
            if receipt.exists():
                expected=json.loads(receipt.read_text())
                assert sha256(args.exe.parent/'BambuStudio.dll')==expected['dll_sha256'],'Local runtime DLL changed; rebuild/verify it'
                assert all(source_hash_matches(ROOT/name,sha) for name,sha in expected['source_sha256'].items()),'Native source differs from retained runtime build'
            return {'exe_sha256':sha256(args.exe),'dll_sha256':sha256(args.exe.parent/'BambuStudio.dll'),
                    'source_receipt_verified':receipt.exists(),
                    'automation':'native Win32 menu/dialog commands + actual WebView2 CDP; loopback only'}
        pre=report.run('gui/preflight','environment',preflight) if not args.no_gui else {'status':'NOT_RUN','error':'--no-gui requested'}
        # Load each STL/project directly through Bambu's startup argument. Reuse
        # the first real scenario's native baseline only for selection variants;
        # a separate Save-dialog bootstrap must not gate all desktop scenarios.
        template=destination/'gui-geometry-tilted-box/before.3mf'
        for name,scenario,fixture,variant in scenarios:
            kind='fault_injection_actual_CPP' if name in ('malformed-output','worker-post-failure') else (
                'native_GUI' if name.startswith('reject-') or name=='fresh-process-roundtrip' else 'native_GUI_with_CDP')
            if pre['status']!='PASS':
                report.record('gui/'+name,kind,'NOT_RUN' if args.no_gui else 'BLOCKED',error=pre['error'],logs=pre.get('logs','report.json')); continue
            def run(folder):
                source=fixtures_dir/(fixture['id']+'.stl')
                case_fixture=fixture
                if variant=='generated-project':
                    source=destination/'gui-geometry-tilted-box/sliced-project.3mf'
                    if not source.exists(): raise Blocked('Earlier tilted-box GUI project unavailable; fresh-process test not run')
                    case_fixture={**fixture,'source_project':str(source)}
                elif variant:
                    if not template.exists(): raise Blocked('First geometry baseline unavailable; selection variant not run')
                    source=folder/'input.3mf'; make_project_variant(template,source,variant)
                session=Session(args,folder,source)
                try: session.ready(); return gui_scenario(session,scenario,case_fixture)
                finally: session.close()
            result=report.run('gui/'+name,kind,run)
            if result['status']=='BLOCKED' and any(reason in result['error'] for reason in
                    ('GPU process denied','foreground/input desktop','automation inconclusive')):
                pre=result  # Do not repeatedly launch against a proven environment block.
    except KeyboardInterrupt: report.record('run/interrupted','environment','NOT_RUN',error='User interrupted the run')
    except Exception as error:
        report.record('run/setup','environment','BLOCKED' if isinstance(error,Blocked) else 'FAIL',error=str(error))
        (destination/'setup-error.log').write_text(traceback.format_exc(),encoding='utf-8')
    finally:
        report.save(); print('Report:',destination/'report.md',flush=True)
    counts=report.data['counts']
    return 1 if counts.get('FAIL') else 2 if counts.get('BLOCKED') or counts.get('NOT_RUN') else 0


if __name__=='__main__':
    raise SystemExit(main())
