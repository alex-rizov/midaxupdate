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
import logging
import google.cloud.logging
from midaxupdate.my_id import MyId

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/logging.write']

class CustomFormatter(logging.Formatter):
    def format(self, record):
        logmsg = super(CustomFormatter, self).format(record)
        if record.args is not None and isinstance(record.args, dict):
            return {'instance-id': MyId.toJSON(), 'msg': logmsg, 'args':record.args}
        else:
            return {'instance-id': MyId.toJSON(), 'msg': logmsg}

class StackdriverLogger(object):
    def __init__(self, creds_folder):
        self.creds_folder = creds_folder.strip("/\\")        

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

        self.client = google.cloud.logging.Client(credentials = creds, project = creds.project_id)

    def get_default_handler(self):
        handler = self.client.get_default_handler()
        handler.setFormatter(CustomFormatter())
        return handler
    
    

