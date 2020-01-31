from midaxupdate.restarterreplacer import SelfRestart, copy_files_in_target_folder_with_subfolders
from midaxupdate.midax_folder_discovery import midax_discovery_folders_services
from midaxupdate.ids_channels import IdGetter, ChannelDiscovery, MyId
from midaxupdate.browser import BrowserFactory
from midaxupdate.gdrive_browser import GDriveBrowser
from midaxupdate.update_orchestrator import UpdateOrchestrator
from midaxupdate.midaxlogger import MidaxLogger, get_logger
import logging
import os
import sys


FTPFILE = 'FTP.cfg'
class UpdaterRunner(object):
        def __init__(self, working_folder, app_folder):
                self.working_folder = working_folder
                self.app_folder = app_folder
                copy_files_in_target_folder_with_subfolders(os.path.join(self.app_folder, "creds"), os.path.join(self.working_folder, "creds"))
                MidaxLogger.initialize(format='%(asctime)s [%(filename)s:%(lineno)s - %(funcName)20s() %(levelname)s] %(message)s', level=logging.DEBUG, file = os.path.join(working_folder, "log/MidaxUpdate.log"), stackdriver_creds = os.path.join(self.working_folder, 'creds/logger'))                              
                self.logger = get_logger()
                self.logger.info('Working folder is {}, package folder is {}'.format(working_folder, app_folder))                

        def run(self):
                try:
                        paths_services = midax_discovery_folders_services()
                        IdGetter(paths_services, self.working_folder).get_id()
                        
                        #Create UPDATE.ver to mark this as the UPDATE application according to spec.
                        with open(os.path.join(self.working_folder, 'UPDATE.ver'), 'a'):
                                pass

                        ftp_remote = None
                        if os.path.isfile(os.path.join(self.working_folder, FTPFILE)):
                                with open(os.path.join(self.working_folder, FTPFILE), 'r') as f:
                                        ftp_remote = f.read()

                        browser = BrowserFactory.create(gdrive_creds = os.path.join(self.working_folder, "creds/reader"), ftp_remote = ftp_remote)
                        channel = ChannelDiscovery(browser, MyId.get_id(), self.working_folder).get_channel()                        
                        
                        update = UpdateOrchestrator(midax_discovery_folders_services(), channel, browser, self.working_folder).get_configured_folders() \
                                .get_apps() \
                                        .delete_old_staging_folders() \
                                                .check_for_updates() \
                                                        .prepare_update_folders() \
                                                                .get_update_zips() \
                                                                        .unzip() \
                                                                                .self_update() \
                                                                                        .update() \
                                                                                                .double_check_services() 
                        
                        browser.store_file_at_path('UpdateLogs/{}.log'.format(MyId.get_id()), os.path.join(self.working_folder, "log/MidaxUpdate.log"))
                        browser.close()
                                                                                
                except SelfRestart:
                        raise
                except Exception as e:
                        self.logger.error(str(e))                          
        
        def log(self, text):
                self.logger.info(text)


if __name__ == "__main__":
    UpdaterRunner(os.getcwd(), os.getcwd()).run()