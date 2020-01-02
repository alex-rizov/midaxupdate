import os
from midaxupdate.midaxlogger import get_logger as logger 
import configparser
import fnmatch
from midaxupdate.my_id import MyId

CHANNELFILE = 'CHANNELS.cfg'
class ChannelDiscovery(object):
    def __init__(self, browser, id):
        self.browser = browser
        self.id = id

    def get_channel(self):        
        if os.path.isfile(os.path.join(os.getcwd(), CHANNELFILE)):
            os.remove(os.path.join(os.getcwd(), CHANNELFILE))

        self.browser.get_file_at_path('UpdateRoot/{}'.format(CHANNELFILE), os.path.join(os.getcwd(), CHANNELFILE))
        config = configparser.ConfigParser(allow_no_value=True)
        config.read(os.path.join(os.getcwd(), CHANNELFILE))  
        
        def filter_channels(v):
            return len(list(filter(lambda x: fnmatch.fnmatch(self.id, x), config[v])))

        matches = list(filter(filter_channels, config))
        
        logger().info("Channel matches: {}".format(matches))  
        if len(matches) > 0:
            return matches[0]
        else:
            return 'DEFAULT'
            

CHAINFILE = 'CHAIN.id'
STOREFILE = 'STORE.id'
class IdGetter(object):
    
    def __init__(self, folder_service_dict, working_folder):
        self.folder_list = folder_service_dict.keys()    
        self.working_folder = working_folder    
    
    def get_id(self):       

        chain = 'DEFAULT'
        store = 'DEFAULT'
        chain_found = None
        store_found = None
        
        for folder in self.folder_list:
            if os.path.isfile(os.path.join(folder, CHAINFILE)) and os.stat(os.path.join(folder, CHAINFILE)).st_size > 0:
                with open(os.path.join(folder, CHAINFILE), 'r') as f:
                    chain = f.read()
                    chain_found = 'Chain ID {} found from folder {}.'.format(chain, folder)

            if os.path.isfile(os.path.join(folder, STOREFILE)) and os.stat(os.path.join(folder, STOREFILE)).st_size > 0:
                with open(os.path.join(folder, STOREFILE), 'r') as f:
                    store = f.read()
                    store_found = 'Store ID {} found from folder {}.'.format(store, folder)


        if chain == 'DEFAULT' and os.path.isfile(os.path.join(self.working_folder, 'id', CHAINFILE)) and os.stat(os.path.join(self.working_folder, 'id', CHAINFILE)).st_size > 0:
            with open(os.path.join(self.working_folder, 'id', CHAINFILE), 'r') as f:
                chain = f.read()
                chain_found = 'Chain ID {} found from folder {}.'.format(chain, os.path.join(self.working_folder, 'id'))

        if store == 'DEFAULT' and os.path.isfile(os.path.join(self.working_folder, 'id', STOREFILE)) and os.stat(os.path.join(self.working_folder, 'id', STOREFILE)).st_size > 0:
            with open(os.path.join(self.working_folder, 'id', STOREFILE), 'r') as f:
                store = f.read()
                store_found = 'Store ID {} found from folder {}.'.format(store, os.path.join(self.working_folder, 'id'))

        MyId.set_id(chain, store)
        if chain_found is not None:
            logger().info(chain_found)

        if store_found is not None:
            logger().info(store_found)

        logger().info('Instance ID is {}'.format(MyId.get_id()))

        if not os.path.isdir(os.path.join(self.working_folder, 'id')):
                os.mkdir(os.path.join(self.working_folder, 'id'))

        with open(os.path.join(self.working_folder, 'id', CHAINFILE), 'w') as f:
            f.write(chain)

        with open(os.path.join(self.working_folder, 'id', STOREFILE), 'w') as f:
            f.write(store)
        
        return '{}'.format(MyId.get_id())
                
