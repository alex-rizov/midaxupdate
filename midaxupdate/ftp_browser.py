from __future__ import print_function
import pickle
import os.path
from ftplib import FTP
from io import FileIO
from midaxupdate.midax_util import split_path
from midaxupdate.midaxlogger import MidaxLogger



class FTPBrowser(object):
    def __init__(self, remote_address, port): 
        if port is None:
            port = 21       
        self.logger = MidaxLogger.midaxlogger()
        self.ftp = FTP()        
        self.ftp.connect(host = remote_address, port = port)
        self.ftp.login()      
            
    def get_file_at_path(self, path, target_location):                                     
        self.ftp.retrbinary('RETR {}'.format(path), open(target_location, 'wb').write)

    def browse_path(self, path):                     
        for (filename, props) in self.ftp.mlsd(path):
            yield filename

    def store_file_at_path(self, path, target_location): 
        with open(target_location, 'rb') as file:                       
            self.ftp.storbinary('STOR {}'.format(path), file)

    def close(self):
        try:
            self.ftp.quit()
        except:
            self.ftp.close()
        

