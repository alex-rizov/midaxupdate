# midaxupdate

## Compilation / packaging

Please update service.spec with local paths before building.
A distributable executable package  for Windows is produced via:

```bash
pyinstaller service.spec
```

## Installation

The midaxupdate.exe should be installed as a service (recommended to be in midax/update folder e.g. C:\midax\update)

```bash
midaxupdate install
```

## Startup

Service manager OR

```bash
midaxupdate start
```

## Usage

Program looks for and updates Midax services (all services with Description starting with 'Midax...').
In order for an application to be considered valid for update, it needs to have in its root folder a .VER file (for example LOYALTY.VER),
which identifies the application. This file ia a an empty stub just used in order to trigger the updater to recognize the folder as a valid application,
based on file name.

By default, unless channels have been defined (see below), the updater then looks by default in the Google Drive folder 
UpdateRoot/DEFAULT/<APP NAME FROM .VER FILE> (UpdateRoot/DEFAULT/LOYALTY in the above
case) to get the zip with the highest version # in its name. It only considers .zip archives which have valid version # names.
```bash
E.g. 25.2.5.2.zip
```

Version #s consist of an arbitrary number of version numericals separated by a dot. 
```bash
E.g. 26 > 25.2.6 > 25.2.5.2.1.1 > 25.2.5.2.1 > 25.2.5.2 > 25.2.5.1 > 25.2.4
```

## FTP (option for sites with no internet access)
Putting a FTP.CFG with a single line of Address:(Port - optional) will make the app check the FTP server instead of Google Drive

When working with FTP, an UpdateLogs folder should also be created in the FTP root with write privileges for anonymous
for the application to upload its logs.

## Instance identification
The app's instance identity consists of a CHAIN-STORE pair.
If in any Midax Service folder a CHAIN.id or STORE.id is discovered, the app assumes this identity for the corresponging portion. 
The identity is assumed for all apps, not just the app where discovered.

By convention, when creating such files manually to give the instance an identity, they should be created in the updater's own 
midax/update folder.

## Channels
In the UpdateRoot on GDrive or FTP a CHANNELS.CFG can be created, consisting of following sections.

```python
[CHANNEL NAME]
Instance Mask 1
Instance Mask 2
```

An instance mask can be any identifier, where wildcards * and ? are supported.

For example instance MIDAX-1 (Chain: MIDAX Store: 1) is matched by the following instance masks
- MIDAX-1
- MIDAX-*
- *-1
- M?DAX-1

If a matching CHANNEL NAME is found, the app will look for UpdateRoot/CHANNEL NAME/APP NAME FROM .VER FILE for its update zips.

## Rollback
By default, the updater does not do rollbacks. If the current installed version is higher than what is found on the server, the current
installed version is not touched. If you'd want it to be replaced with a smaller version # found on the server, the server's 
UpdateRoot/CHANNEL NAME/APP NAME FROM .VER FILE should contain an empty file without extension called ROLLBACK to trigger the 
rollback to a smaller version number. The version rolled back to is still going to be the highest found on the server so any higher 
(potentially unstable) versions need to be deleted before the rollback will happen.

## Logging
The app logs to Google Logging at:
https://console.cloud.google.com/logs/viewer?project=midax-update
