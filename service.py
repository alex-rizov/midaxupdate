import win32serviceutil
import win32service
import win32event
import win32api
import servicemanager
import socket
import time
import logging
import sys
import os
import subprocess 
from midaxupdate.update_runner import UpdaterRunner
from midaxupdate.restarterreplacer import SelfRestart
from midaxupdate.midax_util import delete_old_bundle_dirs

RUN_INTERVAL_SECONDS = 300

class AppServerSvc (win32serviceutil.ServiceFramework):
    _svc_name_ = "MidaxUpdateService"
    _svc_display_name_ = "Midax Update Service"
    _svc_description_ = "Updating Midax Apps and version reporting."

    def __init__(self,args):
        win32serviceutil.ServiceFramework.__init__(self,args)
        self.hWaitStop = win32event.CreateEvent(None,0,0,None)
        socket.setdefaulttimeout(60)
        self.isAlive = True
        self.update_runner = None

    def SvcStop(self):
        self.isAlive = False
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        self.isAlive = True
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_,''))
        self.main() 
        self.update_runner.log('Service shutting down.')                   

    def main(self):
        if getattr(sys, 'frozen', False):
    # If the application is run as a bundle, the pyInstaller bootloader
    # extends the sys module by a flag frozen=True and sets the app 
    # path into variable _MEIPASS'.
            application_path = sys._MEIPASS
            try:
                delete_old_bundle_dirs(path_to_current = application_path)
            except:
                pass
        else:
            application_path = os.path.dirname(os.path.abspath(__file__))      

        
        
        self.update_runner = UpdaterRunner(os.path.dirname(win32api.GetModuleFileName(None)), application_path)
        self.update_runner.log('Service starting.')  
        wait_result = win32event.WAIT_TIMEOUT
        while  wait_result == win32event.WAIT_TIMEOUT:                         
            try:            
                self.update_runner.run()
            except SelfRestart:
                subprocess.Popen(["cmd.exe", "/C", "net", "stop", self._svc_name_, "&&", "net", "start", self._svc_name_])
                self.update_runner.log("Shutting myself down") 
                self.update_runner.log('Waiting on shutdown command.') 
            except Exception:
                raise
            finally:
                wait_result = win32event.WaitForSingleObjectEx(self.hWaitStop, RUN_INTERVAL_SECONDS * 1000, True)
        
            


if __name__ == '__main__':
    argv = sys.argv
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(AppServerSvc)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        if 'install' in argv and '--startup' not in argv:
            index_of_install = argv.index('install')
            argv.insert(index_of_install, 'auto')
            argv.insert(index_of_install, '--startup')     
        win32serviceutil.HandleCommandLine(AppServerSvc, argv=argv)
