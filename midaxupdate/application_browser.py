import os
from midaxupdate.midaxlogger import get_logger as logger
from midaxupdate.serviced_application import ServicedAppFactory
from midaxupdate.midax_util import normalize_version, is_version
import io



def search_paths_for_apps(services_paths_dict):     
    for path, discovered_services in services_paths_dict.items():
        path = path.strip("/\\")
        if not os.path.isdir(path):
            logger().error(path + " does not exist on machine.")
            continue
        
        verfiles = None
        verfiles = [file for file in os.listdir(path) if file.lower().endswith('.ver')]
        if len(verfiles)==0:
            logger().info("No .ver-file exists in folder {}".format(path))
            continue

        for verfile in verfiles:                
            app_name = verfile.upper()[:-4]                                                                       
            yield ServicedAppFactory.create(app_name = app_name, working_folder = path, discovered_services = discovered_services).parse_cver_file(path)


def browse_remote_versions(browser, path):                 
    for item in browser.browse_path(path):  
        logger().info("Found item {}".format(item))      
        if item.endswith('.zip') and is_version(item[:-4]):
            yield item[:-4]

def supports_rollback(browser, path):                 
    for item in browser.browse_path(path):
        if item == 'ROLLBACK':
            return True

    return False

def get_max_version(browser, path):
    try:
        return max([version for version in browse_remote_versions(browser, path)], key=normalize_version)
    except:
        return '0.0.0.0'

SERVICESFILE = 'SERVICES.CFG'
def get_services_from_server(browser, path, staging_folder_path):
    try:
        if os.path.isfile(os.path.join(staging_folder_path, SERVICESFILE)):
            os.remove(os.path.join(staging_folder_path, SERVICESFILE))

        try:
            browser.get_file_at_path('{}/{}'.format(path, SERVICESFILE), os.path.join(staging_folder_path, SERVICESFILE))
        except:
            return []
        
        try:
            with open(os.path.join(staging_folder_path, SERVICESFILE), 'r') as f:
                return f.read().splitlines()
        except FileNotFoundError:
            return []       

    except Exception as e:
        logger().error(str(e))
        return []

FOLDERSFILE = 'FOLDERS.CFG'
def get_configured_folders_from_server(browser, path, download_folder_path):
    try:
        if os.path.isfile(os.path.join(download_folder_path, FOLDERSFILE)):
            os.remove(os.path.join(download_folder_path, FOLDERSFILE))

        try:
            browser.get_file_at_path('{}/{}'.format(path, FOLDERSFILE), os.path.join(download_folder_path, FOLDERSFILE))
        except:
            return {}
        
        try:
            with open(os.path.join(download_folder_path, FOLDERSFILE), 'r') as f:
                return dict.fromkeys([os.path.normcase(os.path.normpath(path)) for path in f.read().splitlines() if os.path.isdir(path)], [])
        except FileNotFoundError:
            return {}        

    except Exception as e:
        logger().error(str(e))
        return {}

