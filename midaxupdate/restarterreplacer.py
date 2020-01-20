import datetime as d
import os
import time
from midaxupdate.midaxlogger import MidaxLogger
import win32con
import win32service
import win32serviceutil
import subprocess
from shutil import move, copy2
from midaxupdate.midax_util import verify_folder_needs_update


RUNNING = win32service.SERVICE_RUNNING
STARTING = win32service.SERVICE_START_PENDING
STOPPING = win32service.SERVICE_STOP_PENDING
STOPPED = win32service.SERVICE_STOPPED

class SelfRestart(Exception):
    pass

def status_string(status):
    switcher ={
            RUNNING : 'RUNNING',
            STARTING : 'STARTING',
            STOPPING : 'STOPPING',
            STOPPED : 'STOPPED'
    }
    return switcher.get(status, 'INVALID')

class ServiceController(object):
    def __init__(self, service_names):
        accessSCM = win32con.GENERIC_READ
        self.logger = MidaxLogger.midaxlogger()
        self.service_names = service_names
        #Open Service Control Manager
        hscm = win32service.OpenSCManager(None, None, accessSCM)
        try:
            #Enumerate Service Control Manager DB
            typeFilter = win32service.SERVICE_WIN32
            stateFilter = win32service.SERVICE_STATE_ALL            

            statuses = win32service.EnumServicesStatus(hscm, typeFilter, stateFilter)           
            present_names = [short_name for (short_name, desc, status) in statuses]
            self.service_names = [name for name in service_names if name in present_names]
                
        finally:
            win32service.CloseServiceHandle(hscm)
        

    def svcStatus(self, svc_name, machine=None):
        return win32serviceutil.QueryServiceStatus( svc_name, machine)[1]	# scvType, svcState, svcControls, err, svcErr, svcCP, svcWH
    
    def svcStop(self, svc_name, machine=None):
        accessSCM = win32con.GENERIC_READ
        hscm = win32service.OpenSCManager(None, None, accessSCM)
        try:
            shandle = win32service.OpenService(hscm, svc_name, accessSCM)
            try:
                dependent_services = win32service.EnumDependentServices(shandle, win32service.SERVICE_ACTIVE)                
                for (service_name, display_name, service_status) in dependent_services:
                    if (service_status[1] == RUNNING):
                        self.logger.info("Stopping {} service because it is dependency of {}".format(service_name, svc_name))
                        self.svcStop(service_name)
            finally:
                win32service.CloseServiceHandle(shandle)
        finally:
            win32service.CloseServiceHandle(hscm)

        status = win32serviceutil.StopService( svc_name, machine)[1]
        i = 0
        while status == STOPPING:
                time.sleep(1)
                status = self.svcStatus( svc_name, machine)
                i = i + 1
                if i > 60:
                    self.logger.info("Timeout stopping %s service" % svc_name)
                    raise TimeoutError
        return status
    
    def svcStart(self, svc_name, svc_arg = None, machine=None):
        accessSCM = win32con.GENERIC_READ
        hscm = win32service.OpenSCManager(None, None, accessSCM)
        try:
            shandle = win32service.OpenService(hscm, svc_name, accessSCM)
            try:
                (service_type, start_type, error_control, path, load_order_group, tag_id, dependencies, start_name, display_name) = win32service.QueryServiceConfig(shandle)            
                for service_name in dependencies:
                    if (self.svcStatus(service_name, machine) == STOPPED):
                        self.logger.info("Starting {} service because {} depends on it.".format(service_name, svc_name))
                        self.svcStart(service_name)
            finally:
                win32service.CloseServiceHandle(shandle)
        finally:
            win32service.CloseServiceHandle(hscm)

        if not svc_arg is None:
            if isinstance(svc_arg, str):
                # win32service expects a list of string arguments
                svc_arg = [ svc_arg]

        win32serviceutil.StartService( svc_name, svc_arg, machine)
        status = self.svcStatus( svc_name, machine)
        i = 0
        while status == STARTING:
            time.sleep(1)
            status = self.svcStatus( svc_name, machine)
            i = i + 1
            if i > 60:
                self.logger.info("Timeout starting %s service" % svc_name)
                raise TimeoutError

        return status

    def start_dependant_services(self, svc_name):
        accessSCM = win32con.GENERIC_READ
        hscm = win32service.OpenSCManager(None, None, accessSCM)
        try:
            shandle = win32service.OpenService(hscm, svc_name, accessSCM)
            try:  
                dependent_services = win32service.EnumDependentServices(shandle, win32service.SERVICE_INACTIVE)                
                for (service_name, display_name, service_status) in dependent_services:
                    try:
                        if (service_status[1] == STOPPED):
                            self.logger.info("Starting {} service because it is dependent on {}".format(service_name, svc_name))
                            self.svcStart(service_name)
                    except Exception as e:
                        self.logger.error(str(e))
            except Exception as e:
                self.logger.error(str(e))
            finally:
                win32service.CloseServiceHandle(shandle)
        finally:
            win32service.CloseServiceHandle(hscm)


    def stop_services(self):
        for service_name in self.service_names:
            status = self.svcStatus(service_name)
            if (status == RUNNING):                
                self.logger.info("Service %s in %s state. Stopping." % (service_name, status_string(status)))
                self.svcStop(service_name) 
            elif (status == STOPPED):
                self.logger.info("Service %s in %s state. Do nothing." % (service_name, status_string(status)))  
            else:
                self.logger.info("Service %s in %s state. ERROR!" % (service_name, status_string(status)))
                raise PermissionError("Service %s in %s state. ERROR!")

    def start_services(self, silent = False):
        error = None
        for service_name in self.service_names:            
            try:
                status = self.svcStatus(service_name)
                if (status == RUNNING):     
                    if silent is False:           
                        self.logger.info("Service %s in %s state. Do nothing." % (service_name, status_string(status)))                    
                elif (status == STOPPED):
                    self.logger.info("Service %s in %s state. Starting." % (service_name, status_string(status)))  
                    self.svcStart(service_name) 
                else:
                    self.logger.error("Service %s in %s state!" % (service_name, status_string(status))) 

                if silent is True:
                    self.start_dependant_services(service_name)
            except Exception as e: #still try to go through remaining services and start them to leave best possible state
                self.logger.info(str(e))
                error = e
            
        if error is not None:
            raise error

def move_files_in_empty_folder_that_match_upd_folder(source, dest, upd):
        if not os.path.isdir(dest):
            os.mkdir(dest)

        for filename in os.listdir(dest):            
            raise ValueError("{} folder is NOT empty! Update cannot go through!".format(dest))

        for filename in os.listdir(upd):
            if (os.path.isfile(os.path.join(upd, filename))) and (os.path.isfile(os.path.join(source, filename))) :
                os.rename(os.path.join(source, filename), os.path.join(dest, filename))

            if (os.path.isdir(os.path.join(upd, filename))) and (os.path.isdir(os.path.join(source, filename))):
                move_files_in_empty_folder_that_match_upd_folder(os.path.join(source, filename), os.path.join(dest, filename), os.path.join(upd, filename))   

def copy_files_in_target_folder_with_subfolders(source, dest):
    if not os.path.isdir(dest):
        os.mkdir(dest)

    for filename in os.listdir(source):
        if os.path.isfile(os.path.join(source, filename)):
            copy2(os.path.join(source, filename), os.path.join(dest, filename))

        if os.path.isdir(os.path.join(source, filename)):
            copy_files_in_target_folder_with_subfolders(os.path.join(source, filename), os.path.join(dest, filename))  

class RestarterReplacer(object):
    def __init__(self, service_names, target_path, staging_dir_path):
        self.logger = MidaxLogger.midaxlogger()
        self.service_controller = ServiceController(service_names)

        target_path = target_path.strip("/\\")
        staging_dir_path = staging_dir_path.strip("/\\")

        target_drive, _ = os.path.splitdrive(target_path)
        staging_drive, _ = os.path.splitdrive(staging_dir_path)

        if target_drive != staging_drive:
            self.logger.info("Target and staging hard drives must be the same!")
            raise ValueError("Target and staging hard drives must be the same!")

        if not (os.path.isdir(target_path)):
            raise NotADirectoryError(target_path)

        if not (os.path.isdir(staging_dir_path)):
            raise NotADirectoryError(target_path)

        self.target_path = target_path
        self.staging_dir_path = staging_dir_path

    def move_current_files_to_old_dir(self): 
        move_files_in_empty_folder_that_match_upd_folder(self.target_path, os.path.join(self.staging_dir_path, 'old'), os.path.join(self.staging_dir_path, 'new'))               

    def move_current_files_to_restore_dir(self):
        move_files_in_empty_folder_that_match_upd_folder(self.target_path, os.path.join(self.staging_dir_path, 'restore'), os.path.join(self.staging_dir_path, 'old'))  

    def copy_new_files_from_staging_dir(self): 
        copy_files_in_target_folder_with_subfolders(os.path.join(self.staging_dir_path, 'new'), self.target_path)               

    def restore_files_from_old_dir(self):        
        copy_files_in_target_folder_with_subfolders(os.path.join(self.staging_dir_path, 'old'), self.target_path)  
            

    
        
    def run_startup_programs(self):
        try:
            with open(os.path.join(self.target_path, 'run.me'), 'r') as f:
                for line in f.read().splitlines():
                    p = subprocess.Popen(line.split(' '), cwd = self.target_path)
                    self.logger.info('Started startup program: {}'.format(line))
                    p.communicate(timeout = 120)
        except FileNotFoundError:
            pass
        except Exception as e:
            self.logger.error(str(e))

  

    def update(self):
        self.logger.info("Starting update from %s into %s." % (self.staging_dir_path, self.target_path))
        if verify_folder_needs_update(self.staging_dir_path + '/new', self.target_path) is False:
            self.logger.info("No need to update. No files in %s/new or they match current working copies in %s!" % (self.staging_dir_path, self.target_path))
            return

        try:
            self.service_controller.stop_services()
            self.move_current_files_to_old_dir()

            try:
                self.copy_new_files_from_staging_dir()
                self.run_startup_programs()
            except Exception as e:
                self.move_current_files_to_restore_dir()
                self.restore_files_from_old_dir()
                raise e
            
        except Exception as e:
            self.logger.error(str(e))
            raise e
        finally:
            self.service_controller.start_services()

    
    def update_self(self):
        self.logger.info("Starting self update from %s into %s." % (self.staging_dir_path, self.target_path))
        if verify_folder_needs_update(self.staging_dir_path + '/new', self.target_path) is False:
            self.logger.info("No need to update. No files in %s/new or they match current working copies in %s! Restarting." % (self.staging_dir_path, self.target_path))
            raise SelfRestart

        try:            
            self.move_current_files_to_old_dir()

            try:
                self.copy_new_files_from_staging_dir()                                
                raise SelfRestart
            except SelfRestart:
                raise
            except Exception as e:                
                self.move_current_files_to_restore_dir()
                self.restore_files_from_old_dir()
                raise

        except SelfRestart:
            raise 
        except Exception as e:
            self.logger.error(str(e))
            raise
        
            
        
        
