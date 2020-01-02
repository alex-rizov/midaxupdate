from midaxupdate.ftp_browser import FTPBrowser
from midaxupdate.gdrive_browser import GDriveBrowser
from midaxupdate.midax_util import parse_hostport

class BrowserFactory(object):
    @classmethod
    def create(cls, gdrive_creds = None, ftp_remote = None):
        if ftp_remote is not None:            
            return FTPBrowser(*parse_hostport(ftp_remote))
        elif gdrive_creds is not None:
            return GDriveBrowser(gdrive_creds)
        else:
            raise FileNotFoundError('No valid remote - no GDrive credentials or FTP host.')
        