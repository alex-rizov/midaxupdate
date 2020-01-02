import win32con
import win32service
import os.path
from itertools import groupby
from operator import itemgetter

def folders_for_midax_services():
    resume = 0
    accessSCM = win32con.GENERIC_READ
    accessSrv = win32service.SC_MANAGER_ALL_ACCESS

    #Open Service Control Manager
    hscm = win32service.OpenSCManager(None, None, accessSCM)
    try:
        #Enumerate Service Control Manager DB
        typeFilter = win32service.SERVICE_WIN32
        stateFilter = win32service.SERVICE_STATE_ALL
        disabled = win32service.SERVICE_DISABLED

        statuses = win32service.EnumServicesStatus(hscm, typeFilter, stateFilter)
        

        for (short_name, desc, status) in statuses:
            if desc.lower().startswith('midax'):
                shandle = win32service.OpenService(hscm, short_name, accessSCM)
                try:
                    (service_type, start_type, error_control, path, load_order_group, tag_id, dependencies, start_name, display_name) = win32service.QueryServiceConfig(shandle)
                    if '/SM' in path:
                        path = path.split('/SM', 1)[0] 
                    
                    path = path.strip('"')
                    
                    if start_type == disabled:
                        continue
                    
                    path = os.path.dirname(os.path.normcase(os.path.normpath(path)))                  

                    if os.path.isdir(path):                        
                        yield path, short_name
                finally:
                    win32service.CloseServiceHandle(shandle)
    finally:
        win32service.CloseServiceHandle(hscm)

def midax_discovery_folders_services():
    return {k:[vi[1] for vi in list(v)] for k,v in groupby(sorted(folders_for_midax_services(), key=itemgetter(0)),key=itemgetter(0))}

