from hashlib import md5
import os.path
import re, os, sys, time
from filecmp import dircmp
from stat import S_ISREG, ST_CTIME, ST_MODE, S_ISDIR

def file_md5(fname):
    hash_md5 = md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def split_path(path):
        path = path.strip("/\\")
        folders = []
        while 1:
                path, folder = os.path.split(path)

                if folder != "":
                        folders.append(folder)
                else:
                        if path != "":
                                folders.append(path)

                        break

        folders.reverse()
        return folders

def normalize_version(v):
        return [int(x) for x in re.sub(r'(\.0+)*$','', v).split(".")]

def is_version(version):
    try:
        _ = normalize_version(version)
        return True
    except:
        return False    

def verify_folder_needs_update(new_folder, running_folder):
        """
    Compare two directory trees content.
    Return False if they differ, True is they are the same.
    """
        compared = dircmp(new_folder, running_folder)
        if (compared.left_only or compared.diff_files 
        or compared.funny_files):
                return True
        for subdir in compared.common_dirs:
                if verify_folder_needs_update(os.path.join(new_folder, subdir), os.path.join(running_folder, subdir)):
                        return True
        return False


def delete_tree_or_file(folder_path):
        if os.path.isdir(folder_path) != True and os.path.isfile(folder_path) != True:
                raise OSError('{} not a folder or file.'.format(folder_path))

        if os.path.isfile(folder_path):
                os.remove(folder_path)
                return
        
        # get all entries in the directory w/ stats
        entries = (os.path.join(folder_path, fn) for fn in os.listdir(folder_path))
        entries = ((os.stat(path), path) for path in entries)

        
        paths = (path
                for stat, path in entries)

        for path in paths:
                delete_tree_or_file(path)

        if len(os.listdir(folder_path)) > 0:
                raise OSError('Folder {} not empty.'.format(folder_path))

        os.rmdir(folder_path)


def delete_old_bundle_dirs(path_to_current):
        base_dir = os.path.join('C:/', 'ProgramData', 'Midax', 'Update')
        if os.path.exists(base_dir):
                for child_dir in os.listdir(base_dir):
                        full_dir = os.path.join(base_dir, child_dir)
                        if not os.path.isdir(full_dir):
                                continue

                        if os.path.normpath(full_dir) == os.path.normpath(path_to_current):
                                continue

                        delete_tree_or_file(full_dir)

host_port_regex = re.compile(r'''
(                            # first capture group = Addr
  \[                         # literal open bracket                       IPv6
    [:a-fA-F0-9]+            # one or more of these characters
  \]                         # literal close bracket
  |                          # ALTERNATELY
  (?:                        #                                            IPv4
    \d{1,3}\.                # one to three digits followed by a period
  ){3}                       # ...repeated three times
  \d{1,3}                    # followed by one to three digits
  |                          # ALTERNATELY
  [-a-zA-Z0-9.]+              # one or more hostname chars ([-\w\d\.])      Hostname
)                            # end first capture group
(?:                          
  :                          # a literal :
  (                          # second capture group = PORT
    \d+                      # one or more digits
  )                          # end second capture group
 )?                          # ...or not.''', re.X)

def parse_hostport(hp):
    # regex from above should be defined here.
    m = host_port_regex.match(hp)
    addr, port = m.group(1, 2)
    try:
        return (addr, int(port))
    except TypeError:
        # port is None
        return (addr, None)