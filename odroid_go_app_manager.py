import configparser
from datetime import datetime
import json
import os
import shutil
from sys import stdout
import time
from urllib.request import urlretrieve, urlopen

APP_MGR_VERSION = '20181019'
APP_LIST = 'odroid_go_apps.json'
CONFIG_FILE = 'odroid_go_app_manager.cfg'
FIRMWARE_DIR = 'odroid/firmware'
DATA_DIR = 'odroid/data'
ODROID_DIR = 'odroid'
ROMART_DIR = 'romart'
ROMS_DIR = 'roms'

def mkdir_p(dir):
    os.makedirs(dir, exist_ok=True)

def read_config_file(config_file):
    # Create config file is doesn't exist
    if not os.path.isfile(config_file):
        new_config = open(config_file, 'w')
        new_config.close()
    
    config = configparser.ConfigParser()
    config.read(config_file)
    return config

def save_config_file(config_file_path, config):
    with open(config_file_path, 'w') as config_file:
        config.write(config_file)

def get_config_value(config_file, section, key):
    config = read_config_file(config_file)
    if section in config:
        config_value = config[section][key]
    else:
        config_value = None
    return config_value

def set_config_value(config_file, section, key, value):
    config = read_config_file(config_file)
    if section not in config:
        config.add_section(section)
    config.set(section, key, str(value))
    save_config_file(CONFIG_FILE, config)

def prepare_sd_card(mode=None):
    print('Preparing SD card')
    
    if mode == 'remove_all':
        # Remove all standard directories and config
        shutil.rmtree(ODROID_DIR, True)
        shutil.rmtree(ROMART_DIR, True)
        shutil.rmtree(ROMS_DIR, True)
        if os.path.isfile(CONFIG_FILE):
            os.remove(CONFIG_FILE)
    if mode == 'remove_firmware':
        # Remove firmware directory and config, leave roms and save data in place
        shutil.rmtree(FIRMWARE_DIR, True)
        if os.path.isfile(CONFIG_FILE):
            os.remove(CONFIG_FILE)
        
    mkdir_p(FIRMWARE_DIR)
    mkdir_p(DATA_DIR)
    
    set_config_value(CONFIG_FILE, 'info', 'last_run_date', datetime.now())
    set_config_value(CONFIG_FILE, 'info', 'version', APP_MGR_VERSION)
    
def urlretrieve_progress(count, block_size, total_size):
    global start_time
    if count == 0:
        start_time = time.time()
        return
    duration = time.time() - start_time
    progress_size = count * block_size
    speed = progress_size / (1024 * duration)
    percent = min(count * block_size * 100 / total_size, 100)
    stdout.write("\r...{0:.0f}%, {1:.1f} MB / {2:.1f} MB, {3:.0f} KB/s, {4:.1f} seconds elapsed".format(percent, progress_size / (1024 * 1024), total_size / (1024 * 1024), speed, duration))
    stdout.flush()

def download_file(url, target_dir):
    print('Downloading {0}'.format(url))
    # If target_dir is working dir, just pass filename as target_path
    if target_dir == '':
        target_path = os.path.basename(url)
    else:
        target_path = '{0}/{1}'.format(target_dir, os.path.basename(url))
    #try:
    local_filepath, headers = urlretrieve(url, target_path, urlretrieve_progress)
    #except:
    #    print('Download failed')
    #    local_filepath = None
    #finally:
    print('')
    return local_filepath

def get_app_list():
    try:
        app_list_filepath = download_file('https://raw.githubusercontent.com/argoolsbee/odroid-go-firmware-app-manager/master/odroid_go_apps.json', '')
    except:
        print('Could not download app list. Using local copy if available')
        app_list_filepath = APP_LIST
    print(app_list_filepath)
    with open(app_list_filepath, encoding='utf-8') as json_data:
        app_list_json = json.load(json_data)
    
    app_list_json = sorted(app_list_json.items(), key=lambda x: x[1]['display_name'])
    
    return app_list_json

def install_firwmare_dependencies(repo, app):
    # Repo specific dependencies: create dir structure, move bios files if found in current dir
    print('Installing dependencies')
    deps = app['dependencies']
    
    for directory in deps['directories']:
        print('Creating directory: {0}'.format(directory))
        mkdir_p(directory)
        
    for file in deps['files']:
        target_filepath = '{0}/{1}'.format(file['target_directory'], file['name'])
        if file['target_directory'] == ROMART_DIR and os.path.isdir(ROMART_DIR):
            print('Skipping rom art install, directory found')
        elif os.path.isfile(target_filepath):
            print('File found in target directory. Skipping file: {0}'.format(file['target_directory']))
        elif os.path.isfile(file['name']):
            print('File found in working directory. Moving to target directory.')
            mkdir_p(file['target_directory'])
            shutil.move(file['name'], file['target_directory'])
        elif 'content' in file:
            print('Creating file: {0}'.format(target_filepath))
            mkdir_p(file['target_directory'])
            with open(target_filepath, 'w') as dep_file:
                for line in file['content']:
                     dep_file.write('{0}\n'.format(line))
        elif 'sources' in file:
            mkdir_p(file['target_directory'])
            for idx, source in enumerate(file['sources']):
                print('Downloading dependency: {0}'.format(file['sources'][idx]))
                dep_filepath = download_file(source, file['target_directory'])
                if dep_filepath is not None:
                    print('File downloaded: {0}'.format(dep_filepath))
                    # If archive, unpack to target_directory
                    if any(x in dep_filepath for x in ['.tgz', '.zip']):
                        print('Unpacking file')
                        archive = shutil.unpack_archive(dep_filepath)
                        os.remove(dep_filepath)
                        if file['target_directory'] == 'romart':
                            set_config_value(CONFIG_FILE, 'romart', 'version', dep_filepath[-8:])
                    break
                else:
                    print('Download failed. Attempting next source.')
        else:
            print('WARNING: Unable to automatically install dependent file: {0}'.format(file['name']))
            print('         Put file {0} in directory {1}'.format(file['name'], file['target_directory']))
    
    if 'instructions' in deps:
        print('App instructions: {0}'.format(deps['instructions']))

def install_firmware(repo, app, firmware_url, tag_name):
    firmware_filepath = download_file(firmware_url, FIRMWARE_DIR)
    install_firwmare_dependencies(repo, app)
    set_config_value(CONFIG_FILE, 'installed_releases', repo, tag_name)

def install_romart(force_install=False):
    # Check if romart already exists and skip download. Set force_install parameter to True to download regardless.
    print('=== Rom Art ===')
    if os.path.isdir(ROMART_DIR) and not force_install:
        print('Skipping install, rom art directory found')
    else:
        shutil.rmtree(ROMART_DIR, True)
        try:
            romart_filepath = download_file('http://tree.cafe/romart-20180810.tgz', '')
        except:
            romart_filepath = download_file('https://dn.odroid.com/ODROID_GO/romart-20180810.tgz', '')
        romart_filename, romart_file_extension = os.path.splitext(romart_filepath)
        try:
            print('Unpacking rom art')
            archive = shutil.unpack_archive(romart_filepath)
            os.remove(romart_filepath)
            
            set_config_value(CONFIG_FILE, 'romart', 'version', romart_filename[-8:])
        except:
            print('WARNING: unable to unpack rom art archive: {0}'.format(romart_filepath))

def get_firmware_release(repo, release):
    #TODO: bitbucket support (https://bitbucket.org/DavidKnight247/odroid-go-spectrum-emulator, https://bitbucket.org/odroid_go_stuff/arduventure)
    
    url = 'https://api.github.com/repos/{0}/releases/'.format(repo)
    if release == 'latest':
        print('Getting latest release')
        url += 'latest'
    else:
        print('Getting release {0}'.format(release))
        url += 'tags/{0}'.format(release)
    
    github_client_id = get_config_value(CONFIG_FILE, 'github_auth', 'client_id')
    github_client_secret = get_config_value(CONFIG_FILE, 'github_auth', 'client_secret')
    
    if github_client_id and github_client_secret:
        url += '?client_id={0}&client_secret={1}'.format(github_client_id, github_client_secret)
    
    print(url)
    fw_idx = None
    fw_url = None
    tag_name = None
    try:
        response = json.loads(urlopen(url).read().decode('utf-8'))
        
        print('Found release {0}'.format(response['tag_name']))
        
        # Look for a fw file in the release
        # TODO: this assumes there is only 1, returns the last found
        for idx, asset in enumerate(response['assets']):
            if asset['browser_download_url'].endswith('.fw'):
                fw_idx = idx
                fw_url = response['assets'][fw_idx]['browser_download_url']
                tag_name = response['tag_name']
                #print('Release Notes:')
                #print(response['body'])
        
        if fw_idx is None:
            print('Firmware file not found in release')
            #TODO: get next latest release?
    except:
        print('Release not found')

    return fw_url, tag_name

def get_installed_release(repo):
    config = read_config_file(CONFIG_FILE)
    tag_name = None
    try:
        tag_name = get_config_value(CONFIG_FILE, 'installed_releases', repo)
    except:
        print('{0} not found in config'.format(repo))
    return tag_name

def finalize_sd_card():
    print('=== Post Install Steps ===')
    #if os.path.exists('{0}/col'.format(DATA_DIR)) and not os.path.isfile('{0}/col/BIOS.col'.format(ROMS_DIR)):
    #    print('* ColecoVison requires a BIOS.col in {0}/col'.format(ROMS_DIR))
    #if os.path.exists('{0}/msx/bios'.format(ROMS_DIR)) and not (os.path.isfile('{0}/msx/bios/DISK.ROM'.format(ROMS_DIR)) and os.path.isfile('{0}/msx/bios/MSX2.ROM'.format(ROMS_DIR)) and os.path.isfile('{0}/msx/bios/MSX2EXT.ROM'.format(ROMS_DIR))):
    #    print('* fMSX-go requires BIOS files MSX2.ROM, MSX2EXT.ROM and DISK.ROM in {0}/msx/bios'.format(ROMS_DIR))
    print('* Hold B on first boot to reinstall your preferred app')


prepare_sd_card()

app_list = get_app_list()

for idx, (repo, app) in enumerate(app_list, start=1):
    print('=== {1} ==='.format(idx, app['display_name']))
    firmware_url, release_tag_name = get_firmware_release(repo, app['default_release'])

    if release_tag_name is not None:
        installed_tag_name = get_installed_release(repo)
        if release_tag_name == installed_tag_name:
            print('Skipping install, requested release matches installed version')
        else:
            #try:
            install_firmware(repo, app, firmware_url, release_tag_name)
            #except:
            #    print('Install failed')
    else:
        print('ERROR: app firmware release not found, skipping install')

finalize_sd_card()
