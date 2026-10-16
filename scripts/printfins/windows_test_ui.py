"""Win32 automation restricted to a test-owned Bambu process. No product hooks."""
import ctypes as C
from ctypes import wintypes as W
import json
import os
import time

from stability_support import Blocked, wait_for


class WindowsUI:
    def __init__(self, pid, log):
        if os.name != 'nt': raise Blocked('Windows desktop required')
        self.pid, self.log = pid, log
        self.u = C.WinDLL('user32', use_last_error=True)
        self.callback = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
        declarations = {
            'GetWindowTextW': ([W.HWND,W.LPWSTR,C.c_int],C.c_int),
            'GetClassNameW': ([W.HWND,W.LPWSTR,C.c_int],C.c_int),
            'GetWindowThreadProcessId': ([W.HWND,C.POINTER(W.DWORD)],W.DWORD),
            'GetWindowRect': ([W.HWND,C.POINTER(W.RECT)],W.BOOL),
            'GetClientRect': ([W.HWND,C.POINTER(W.RECT)],W.BOOL),
            'ClientToScreen': ([W.HWND,C.POINTER(W.POINT)],W.BOOL),
            'GetCursorPos': ([C.POINTER(W.POINT)],W.BOOL),
            'SetCursorPos': ([C.c_int,C.c_int],W.BOOL),
            'GetForegroundWindow': ([],W.HWND),
            'SetForegroundWindow': ([W.HWND],W.BOOL),
            'WindowFromPoint': ([W.POINT],W.HWND),
            'GetAncestor': ([W.HWND,W.UINT],W.HWND),
            'ShowWindow': ([W.HWND,C.c_int],W.BOOL),
            'IsWindowVisible': ([W.HWND],W.BOOL),
            'IsWindowEnabled': ([W.HWND],W.BOOL),
            'IsIconic': ([W.HWND],W.BOOL),
            'GetDlgCtrlID': ([W.HWND],C.c_int),
            'GetDlgItem': ([W.HWND,C.c_int],W.HWND),
            'GetParent': ([W.HWND],W.HWND),
            'SendMessageW': ([W.HWND,W.UINT,W.WPARAM,W.LPARAM],W.LPARAM),
            'SendMessageTimeoutW': ([W.HWND,W.UINT,W.WPARAM,W.LPARAM,W.UINT,W.UINT,C.POINTER(C.c_size_t)],W.LPARAM),
            'PostMessageW': ([W.HWND,W.UINT,W.WPARAM,W.LPARAM],W.BOOL),
            'SetWindowTextW': ([W.HWND,W.LPCWSTR],W.BOOL),
            'GetSubMenu': ([W.HMENU,C.c_int],W.HMENU),
            'GetMenuItemCount': ([W.HMENU],C.c_int),
            'GetMenuStringW': ([W.HMENU,W.UINT,W.LPWSTR,C.c_int,W.UINT],C.c_int),
            'GetMenuItemID': ([W.HMENU,C.c_int],W.UINT),
            'GetMenuState': ([W.HMENU,W.UINT,W.UINT],W.UINT),
            'GetMenuItemRect': ([W.HWND,W.HMENU,W.UINT,C.POINTER(W.RECT)],W.BOOL),
            'GetDpiForWindow': ([W.HWND],W.UINT),
            'mouse_event': ([W.DWORD,W.DWORD,W.DWORD,W.DWORD,C.c_size_t],None),
            'keybd_event': ([W.BYTE,W.BYTE,W.DWORD,C.c_size_t],None),
        }
        for name,(args,result) in declarations.items():
            fn=getattr(self.u,name); fn.argtypes=args; fn.restype=result
        self.u.EnumWindows.argtypes=[self.callback,W.LPARAM]
        self.u.EnumChildWindows.argtypes=[W.HWND,self.callback,W.LPARAM]
        try: self.u.SetProcessDpiAwarenessContext(C.c_void_p(-4))
        except (AttributeError,OSError): pass

    def record(self, action, **data):
        with self.log.open('a',encoding='utf-8') as stream:
            stream.write(json.dumps({'time':time.time(),'action':action,**data})+'\n')

    def owner(self, hwnd):
        pid=W.DWORD(); self.u.GetWindowThreadProcessId(hwnd,C.byref(pid)); return pid.value

    def send(self, hwnd, message, wparam=0, lparam=0):
        assert self.owner(hwnd)==self.pid, 'Refusing another process window'
        result=C.c_size_t()
        if not self.u.SendMessageTimeoutW(hwnd,message,wparam,lparam,2,2000,C.byref(result)):
            raise TimeoutError('Test-owned native window stopped responding')
        return result.value

    def describe(self, hwnd):
        text=C.create_unicode_buffer(4096); cls=C.create_unicode_buffer(256); rect=W.RECT()
        self.u.GetWindowTextW(hwnd,text,len(text)); self.u.GetClassNameW(hwnd,cls,len(cls)); self.u.GetWindowRect(hwnd,C.byref(rect))
        return {'handle':int(hwnd),'text':text.value,'class':cls.value,'id':self.u.GetDlgCtrlID(hwnd),
                'rect':[rect.left,rect.top,rect.right,rect.bottom], 'enabled':bool(self.u.IsWindowEnabled(hwnd))}

    def windows(self, parent=None):
        result=[]
        @self.callback
        def visit(hwnd,_):
            if self.owner(hwnd)==self.pid and self.u.IsWindowVisible(hwnd): result.append(self.describe(hwnd))
            return True
        if parent: self.u.EnumChildWindows(parent,visit,0)
        else: self.u.EnumWindows(visit,0)
        return result

    def main(self):
        return next((w['handle'] for w in self.windows() if w['class']=='wxWindowNR' and w['text'].endswith(' - BambuStudio')),None)

    def foreground(self, hwnd):
        assert self.owner(hwnd)==self.pid, 'Refusing another process window'
        root=self.u.GetAncestor(hwnd,2)
        # Restoring an already visible/maximized frame changes its geometry.
        # Leave active test windows alone, including modal dialogs and menus.
        if self.u.IsIconic(root): self.u.ShowWindow(root,9)
        if self.owner(self.u.GetForegroundWindow())==self.pid: return
        self.u.SetForegroundWindow(root)
        try:
            wait_for(lambda:self.owner(self.u.GetForegroundWindow())==self.pid,2,
                     'Foreground activation did not complete')
        except TimeoutError:
            self.record('focus-blocked',target=self.describe(root),foreground=int(self.u.GetForegroundWindow() or 0))
            raise Blocked('Cannot focus the test-owned window; foreground/input desktop unavailable')

    def preflight_input(self):
        point=W.POINT()
        if not self.u.GetCursorPos(C.byref(point)) or not self.u.SetCursorPos(point.x,point.y):
            raise Blocked('Interactive Windows cursor unavailable (restricted/locked desktop); no workaround attempted')

    def point(self, hwnd, x=None, y=None):
        if self.describe(hwnd)['class']=='#32768':
            # The active native menu must keep its existing owner/focus.
            if self.owner(self.u.GetForegroundWindow())!=self.pid:
                raise Blocked('Native menu lost foreground ownership')
        else: self.foreground(hwnd)
        rect=W.RECT(); self.u.GetClientRect(hwnd,C.byref(rect))
        point=W.POINT((rect.right//2 if x is None else x),(rect.bottom//2 if y is None else y))
        self.u.ClientToScreen(hwnd,C.byref(point))
        if not self.u.SetCursorPos(point.x,point.y): raise Blocked('SetCursorPos denied')
        hit=self.u.WindowFromPoint(point)
        if self.owner(hit)!=self.pid: raise Blocked('Test window is occluded; refusing to click another process')
        # Allow native hover processing before clicking; mouse movement can
        # open a submenu, which a following click would toggle shut again.
        time.sleep(.2)
        return point

    def click(self, hwnd, x=None, y=None):
        point=self.point(hwnd,x,y)
        if self.owner(self.u.GetForegroundWindow())!=self.pid or self.owner(self.u.WindowFromPoint(point))!=self.pid:
            raise Blocked('Click target lost foreground ownership')
        self.record('click',target=self.describe(hwnd),x=point.x,y=point.y)
        self.u.mouse_event(2,0,0,0,0)
        time.sleep(.05)
        self.u.mouse_event(4,0,0,0,0)

    def keys(self, *keys):
        if self.owner(self.u.GetForegroundWindow())!=self.pid: raise Blocked('Keystroke target lost focus')
        for key in keys: self.u.keybd_event(key,0,0,0)
        for key in reversed(keys): self.u.keybd_event(key,0,2,0)
        self.record('keys',keys=keys)

    def find_control(self, text, parent=None):
        parent=parent or self.main()
        return next((w['handle'] for w in self.windows(parent) if w['text'].replace('&','').strip()==text),None)

    def menu(self, file=False, close=True):
        main=wait_for(self.main,message='Bambu main window not found')
        self.foreground(main)
        self.dismiss_menu()
        top=self.describe(main)['rect'][1]
        bars=[w for w in self.windows(main) if w['class']=='wxWindowNR' and w['text']=='control'
              and w['rect'][2]-w['rect'][0]>500 and 0<=w['rect'][1]-top<70]
        if not bars: raise Blocked('Cannot identify the native top menu toolbar')
        bar=min(bars,key=lambda w:w['rect'][1]); scale=self.u.GetDpiForWindow(main)/96
        self.click(bar['handle'],round((25 if file else 78)*scale),round(15*scale))
        popup=self.popup()
        handle=self.send(popup,0x1e1)
        def entries(menu):
            result=[]
            for index in range(self.u.GetMenuItemCount(menu)):
                text=C.create_unicode_buffer(1024); self.u.GetMenuStringW(menu,index,text,len(text),0x400)
                item={'text':text.value.split('\t')[0].replace('&','').rstrip('.\u2026').strip(),
                      'menu':int(menu),'index':index,
                      'id':self.u.GetMenuItemID(menu,index),'enabled':not bool(self.u.GetMenuState(menu,index,0x400)&3)}
                sub=self.u.GetSubMenu(menu,index)
                if sub: item['children']=entries(sub)
                result.append(item)
            return result
        tree=entries(handle); self.record('menu',file=file,items=tree)
        if close: self.dismiss_menu()
        return tree

    def dismiss_menu(self):
        # Escape once per visible submenu, rather than leaving a popup active.
        for _ in range(5):
            if not any(w['class']=='#32768' for w in self.windows()): return
            self.keys(0x1b)
            time.sleep(.1)
        raise TimeoutError('Menu did not close')

    def popup(self, menu=None):
        try:
            return wait_for(lambda:next((w['handle'] for w in self.windows() if w['class']=='#32768'
                and (menu is None or self.send(w['handle'],0x1e1)==menu)),None),5,'Native menu/submenu did not open')
        except TimeoutError:
            self.snapshot(self.log.parent/'menu-unavailable.json')
            raise Blocked('Native menu/submenu unavailable; automation inconclusive (see menu-unavailable.json)')

    def click_menu_item(self, item):
        popup=self.popup(item['menu'])
        rect=W.RECT()
        if not self.u.GetMenuItemRect(None,item['menu'],item['index'],C.byref(rect)):
            raise Blocked('Native menu item rectangle unavailable')
        origin=W.POINT(0,0)
        if not self.u.ClientToScreen(popup,C.byref(origin)):
            raise Blocked('Native menu coordinates unavailable')
        x,y=(rect.left+rect.right)//2-origin.x,(rect.top+rect.bottom)//2-origin.y
        if item.get('children'):
            self.point(popup,x,y)  # Let Windows open the submenu by hovering.
            self.popup(item['children'][0]['menu'])
        else: self.click(popup,x,y)

    def command(self, name, file=False, required=True):
        def search(items):
            for item in items:
                if item['text'].casefold()==name.casefold(): return [item]
                found=search(item.get('children',[]))
                if found: return [item]+found
        path=search(self.menu(file,close=False))
        if not path:
            self.dismiss_menu()
            raise Blocked('Native menu entry unavailable: '+name)
        if not all(item['enabled'] for item in path):
            self.dismiss_menu()
            if not required: return False
            raise AssertionError('Native menu entry is disabled: '+name)
        item=path[-1]
        assert item['id'] not in (0,0xffffffff)
        # wx popup callbacks depend on the active popup and its owner. Posting
        # WM_COMMAND after dismissing it bypasses that routing (Save did nothing).
        self.record('native_menu_command',name=name,id=item['id'],via='popup-click')
        for item in path: self.click_menu_item(item)
        return True

    def dialog(self, title='PrintFins'):
        return next((w['handle'] for w in self.windows() if w['text']==title and w['class']=='#32770'),None)

    def dialog_text(self, hwnd):
        return '\n'.join(w['text'] for w in self.windows(hwnd) if w['text'])

    def close_dialog(self, hwnd):
        assert self.owner(hwnd)==self.pid
        self.record('close_window',handle=hwnd)
        assert self.u.PostMessageW(hwnd,0x10,0,0)

    def file_dialog(self, path, save=True):
        path=path.resolve()
        # Caller only supplies fresh paths inside its new isolated run directory.
        dialog=wait_for(lambda:next((w['handle'] for w in self.windows() if w['class']=='#32770'
            and any(c['class']=='Edit' for c in self.windows(w['handle']))),None),15,'File dialog not found')
        self.foreground(dialog)
        controls=self.windows(dialog)
        edits=[w for w in controls if w['class']=='Edit' and w['enabled'] and w['rect'][2]>w['rect'][0]]
        def score(edit):
            parent=self.describe(self.u.GetParent(edit['handle']))
            return ('ComboBox' in parent['class'],edit['rect'][1])
        edit=max(edits,key=score)
        value=C.create_unicode_buffer(str(path))
        assert self.send(edit['handle'],0x0c,0,C.cast(value,C.c_void_p).value)
        self.record('file_dialog',save=save,path=str(path),edit=edit)
        button=self.u.GetDlgItem(dialog,1)
        if not button: button=self.find_control('Save' if save else 'Open',dialog)
        if not button: raise Blocked('File dialog action button not found')
        self.click(button)
        wait_for(lambda:not any(w['handle']==dialog for w in self.windows()),15,'File dialog did not close')

    def snapshot(self, target):
        target.write_text(json.dumps([dict(w,children=self.windows(w['handle'])) for w in self.windows()],indent=2),encoding='utf-8')
