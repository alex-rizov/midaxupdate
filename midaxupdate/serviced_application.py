import configparser
import os
from midaxupdate.midax_util import normalize_version, is_version

class ServicedAppFactory(object):    
    @classmethod
    def create(cls, app_name, working_folder, discovered_services):
        if app_name == 'LOYALTY':
            return LoyaltyApp(app_name, working_folder, discovered_services)
        else:
            return ServicedApp(app_name, working_folder, discovered_services)


class ServicedApp(object):
    def __init__(self, app_name, working_folder, discovered_services = None):
        self.app_name = app_name
        self.working_folder = working_folder.strip("/\\")
        self.running_version = '0.0.0.0' 
        self.configured_services = []
        if discovered_services is None:
            self.discovered_services = []
        else:   
            self.discovered_services = discovered_services

        self.services_from_server = []
        
        self.current_version = None 
        self.staging_folder = None     
        self.support_rollback = False 
        
    @property
    def services(self):
        return list(dict.fromkeys(self.configured_services + self.discovered_services + self.services_from_server))

    def parse_cver_file(self, path):         
        config = configparser.ConfigParser(allow_no_value=True)
        config.read('{}/updcache_{}.cver'.format(path, self.app_name))    
        
        try:
            for key in config['VERSION']:
                self.running_version = key
        except:
            pass
    
        try:
            self.configured_services = [key for key in config['SERVICES']]    
        except:
            pass 
        
        return self

    def create_cver_file(self):
        config = configparser.ConfigParser(allow_no_value=True)
        config['VERSION'] = {self.current_version : None}
        config['SERVICES'] = { service: None for service in self.configured_services}        
        with open(os.path.join(self.working_folder, 'updcache_' + self.app_name + '.cver'), 'w') as configfile:
           config.write(configfile)


    def __str__(self):
        return "{{app_name = {}, working_folder = {}, services = {}, running_version = {}, current_version = {}}}".format(self.app_name, self.working_folder, self.services, self.running_version, self.current_version)

    def rollback_eventually_needed(self):
        if self.current_version is None or self.running_version is None or self.current_version == '0.0.0.0':
            return False
        if normalize_version(self.current_version) < normalize_version(self.running_version):
            return True

        return False

    def needs_update(self):
        if self.current_version is None or self.running_version is None or self.current_version == '0.0.0.0':
            return False
        if normalize_version(self.current_version) > normalize_version(self.running_version):
            return True
        elif self.support_rollback and normalize_version(self.current_version) != normalize_version(self.running_version):
            return True
        else:
            return False

    def to_version_JSON(self):
        return { self.app_name : self.running_version
        }

class LoyaltyApp(ServicedApp):
    def __init__(self, app_name, working_folder, discovered_services):
        super().__init__(app_name, working_folder, discovered_services)




