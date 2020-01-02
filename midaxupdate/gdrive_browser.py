from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from io import FileIO
from midaxupdate.midax_util import split_path
from midaxupdate.midaxlogger import MidaxLogger

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

class GDriveBrowser(object):
    def __init__(self, creds_folder):
        self.creds_folder = creds_folder.strip("/\\")
        self.logger = MidaxLogger.midaxlogger()

        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.    
        # If there are no (valid) credentials available, let the user log in.
        if os.path.exists(self.creds_folder + '/token.pickle'):
            with open(self.creds_folder + '/token.pickle', 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                creds = service_account.Credentials.from_service_account_file(
                    self.creds_folder + '/credentials.json', scopes=SCOPES)
                # Save the credentials for the next run
                with open(self.creds_folder + '/token.pickle', 'wb') as token:
                    pickle.dump(creds, token)

        self.service = build('drive', 'v3', credentials=creds)
    
    def get_file_with_id(self, id, target_location): 
        request = self.service.files().get_media(fileId=id)
        fh = FileIO(target_location,'wb')
        downloader = MediaIoBaseDownload(fh, request, chunksize=1024 * 1024)
        done = False                                                     
        while done is False:
            status, done = downloader.next_chunk(num_retries = 10)                                  
                        
            
    def get_file_at_path(self, path, target_location):                   
        path_items = split_path(path)

        for path_item in path_items:
            if path_item is path_items[0]:
                qstring = "mimeType = 'application/vnd.google-apps.folder' and name = '{}'".format(path_item)
            elif path_item is path_items[-1]:
                qstring = "name = '{}'".format(path_item)
            else:
                qstring = "mimeType = 'application/vnd.google-apps.folder' and '{}' in parents and name = '{}'".format(parent_id, path_item)

            results = self.service.files().list(q=qstring, supportsAllDrives = True, includeItemsFromAllDrives = True, pageSize=1, fields="nextPageToken, files(id)").execute()
            items = results.get('files', [])
            if len(items) == 0:                
                raise FileNotFoundError("Item {} does not exist on remote.".format(path_item))               
            parent_id = items[0]['id']            
        
        self.get_file_with_id(parent_id, target_location)

    def browse_path(self, path):                 
        path_items = split_path(path)

        for path_item in path_items:            
            if path_item is path_items[0]:
                qstring = "mimeType = 'application/vnd.google-apps.folder' and name = '{}'".format(path_item)            
            else:
                qstring = "mimeType = 'application/vnd.google-apps.folder' and '{}' in parents and name = '{}'".format(parent_id, path_item)

            results = self.service.files().list(q=qstring, supportsAllDrives = True, includeItemsFromAllDrives = True, pageSize=30, fields="nextPageToken, files(id)").execute()
            items = results.get('files', [])
            if len(items) == 0: 
                self.logger.info("Item {} not found on remote.".format(path_item))               
                return        
            
            parent_id = items[0]['id']            
    
        qstring = "mimeType != 'application/vnd.google-apps.folder' and '{}' in parents".format(parent_id) 
        page_token = None
        while True:
            results = self.service.files().list(q=qstring, supportsAllDrives = True, pageToken = page_token, includeItemsFromAllDrives = True, pageSize=30, fields="nextPageToken, files(name)").execute()
            items = results.get('files', [])
            for item in items:
                yield item['name']

            page_token = results.get('nextPageToken')
            if not page_token:
                break

    def store_file_at_path(self, path, target_location):                                     
        pass

    def close(self):
        pass
