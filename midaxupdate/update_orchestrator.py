from uuid import uuid4
import midaxupdate.application_browser as application_browser
from midaxupdate.midaxlogger import get_logger as logger
import os, sys, time
from midaxupdate.restarterreplacer import RestarterReplacer, ServiceController
import zipfile
from functools import cmp_to_key, reduce
from stat import S_ISREG, ST_CTIME, ST_MODE, S_ISDIR
from midaxupdate.midax_util import delete_tree_or_file

def sorting_func_update_last(x , y):
                if x.app_name == 'UPDATE' and y.app_name != 'UPDATE':
                        return 1
                elif x.app_name != 'UPDATE' and y.app_name == 'UPDATE':
                        return -1
                else:
                        return 0

class UpdateOrchestrator(object):
    def __init__(self, folder_list, channel, browser, working_folder):
        self.uuid = str(uuid4())
        self.working_folder = working_folder
        self.folder_list = folder_list        
        self.channel = channel
        self.browser = browser
        self.apps_to_update = None
        self.apps = None
    

    def get_configured_folders(self):        
        self.folder_list = {**application_browser.get_configured_folders_from_server(self.browser, 'UpdateRoot/{}'.format(self.channel), self.working_folder) , **self.folder_list}        
        return self

    def get_apps(self):
        self.apps = [app for app in application_browser.search_paths_for_apps(self.folder_list)]        
        return self

    def check_for_updates(self):
        for app in self.apps:
            app.current_version = application_browser.get_max_version(self.browser, 'UpdateRoot/{}/{}'.format(self.channel, app.app_name))
            if app.rollback_eventually_needed():
                app.support_rollback = application_browser.supports_rollback(self.browser, 'UpdateRoot/{}/{}'.format(self.channel, app.app_name))
        logger().info("Applications discovered: {}".format([str(app) for app in self.apps]))         
        logger().info("Version report", {'version_report' : reduce(lambda x,y: {**x, **y}, [app.to_version_JSON() for app in self.apps], {})}) 
        self.apps_to_update = [app for app in self.apps if app.needs_update()] 
        self.apps_to_update.sort(key = cmp_to_key(sorting_func_update_last)) #so UPDATE is always last
        if len(self.apps_to_update) > 0:
            logger().info("Applications that need update: {}".format([str(app) for app in self.apps_to_update]))   

        update_app_list = [x for x in self.apps_to_update if x.app_name == 'UPDATE']
        if len(update_app_list) > 0:      
            self.apps_to_update = update_app_list
            logger().info("Starting self update.")  
        return self 

    def delete_old_staging_folders(self, folders_to_keep = 5):
        staging_folders = (os.path.join(app.working_folder, 'staging') for app in self.apps if os.path.isdir(os.path.join(app.working_folder, 'staging')))
        for staging_folder in staging_folders:
            # get all entries in the directory w/ stats
            entries = (os.path.join(staging_folder, fn) for fn in os.listdir(staging_folder))
            entries = ((os.stat(path), path) for path in entries)

            # leave only regular files, insert creation date
            entries = ((stat[ST_CTIME], path)
                    for stat, path in entries if S_ISREG(stat[ST_MODE]) or S_ISDIR(stat[ST_MODE]))
            #NOTE: on Windows `ST_CTIME` is a creation date 
            #  but on Unix it could be something else
            #NOTE: use `ST_MTIME` to sort by a modification date

            for cdate, path in sorted(entries, reverse = True)[folders_to_keep:]:
                logger().info('Will delete {}'.format(path))
                try:
                    delete_tree_or_file(path)
                except OSError as e:
                    logger().error(str(e))
        
        return self
            


    def prepare_update_folders(self):
        for app in self.apps_to_update: 
            app.staging_folder = app.working_folder + '/staging/' + self.uuid + '/' + app.app_name      
            if not os.path.isdir(app.working_folder + '/staging'):
                os.mkdir(app.working_folder + '/staging')
            
            if not os.path.isdir(app.working_folder + '/staging/' + self.uuid):
                os.mkdir(app.working_folder + '/staging/' + self.uuid)

            if not os.path.isdir(app.staging_folder):
                os.mkdir(app.staging_folder)

            if not os.path.isdir(app.staging_folder + '/zip'):
                os.mkdir(app.staging_folder + '/zip')

            if not os.path.isdir(app.staging_folder + '/new'):
                os.mkdir(app.staging_folder + '/new')

        return self

    def get_update_zips(self):
        for app in self.apps_to_update: 
            logger().info("Starting download for {}.zip".format(app.current_version))   
            self.browser.get_file_at_path('UpdateRoot/{}/{}/{}.zip'.format(self.channel, app.app_name, app.current_version), '{}/zip/{}.zip'.format(app.staging_folder, app.current_version))
            app.services_from_server = application_browser.get_services_from_server(self.browser, 'UpdateRoot/{}/{}'.format(self.channel, app.app_name), app.staging_folder)
            logger().info("Downloading {}.zip finished".format(app.current_version))   
        return self

    def unzip(self):
        for app in self.apps_to_update:        
            with zipfile.ZipFile('{}/zip/{}.zip'.format(app.staging_folder, app.current_version), 'r') as zip_ref:
                zip_ref.extractall(os.path.join(app.staging_folder, 'new'))

            if os.path.isfile(os.path.join(app.staging_folder, 'new', '{}.ver'.format(app.app_name))):
                os.remove(os.path.join(app.staging_folder, 'new', '{}.ver'.format(app.app_name)))
                
        return self

    def update(self):
        for app in list(filter(lambda x: x.app_name != 'UPDATE', self.apps_to_update)):
            restarter = RestarterReplacer(app.services, app.working_folder, app.staging_folder)
            logger().info("Starting update for {} to version {}".format(app.app_name, app.current_version))
            restarter.update()
            app.create_cver_file()
            logger().info("Update for {} to version {} finished successfully.".format(app.app_name, app.current_version))
            
        return self

    def double_check_services(self): 
        if len(self.apps_to_update) > 0:           
            for app in self.apps_to_update:
                controller = ServiceController(app.services)  
                controller.start_services(silent = True)  
        
        return self

    def self_update(self):
        for app in list(filter(lambda x: x.app_name == 'UPDATE', self.apps_to_update)):
            restarter = RestarterReplacer(app.services, app.working_folder, app.working_folder + '/staging/' + self.uuid + '/' + app.app_name)
            logger().info("Starting update for {}".format(app.app_name))
            app.create_cver_file()
            restarter.update_self()            
            
        return self

    