import configparser
from datetime import datetime
import json
import os
import shutil
from sys import stdout
import time
from urllib.request import urlretrieve, urlopen

REPOS = {
    'mad-ady/doom-odroid-go': '20180822',
    #'OtherCrashOverride/doom-odroid-go': 'latest',
    'OtherCrashOverride/go-play': 'latest',
    #'OtherCrashOverride/MicroPython_ESP32_psRAM_LoBo-odroid-go': 'latest',
    'OtherCrashOverride/prosystem-odroid-go': 'latest',
    'OtherCrashOverride/stella-odroid-go': 'latest',
    'Schuemi/fMSX-go': '20180816',  #prereleases are not returned by github latest release endpoint
}

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
    config_file.close()

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
    set_config_value(CONFIG_FILE, 'info', 'version', '20180823')
    
def urlretrieve_progress(count, block_size, total_size):
    global start_time
    if count == 0:
        start_time = time.time()
        return
    duration = time.time() - start_time
    progress_size = int(count * block_size)
    speed = int(progress_size / (1024 * duration))
    percent = min(int(count * block_size * 100 / total_size), 100)
    stdout.write("\r...%d%%, %d MB/ %d MB, %d KB/s, %d seconds passed" % (percent, progress_size / (1024 * 1024), total_size, speed, duration))
    stdout.flush()

def download_file(url, target_dir):
    print('Downloading {0}'.format(url))
    # If target_dir is working dir, just pass filename as target_path
    if target_dir == '':
        target_path = os.path.basename(url)
    else:
        target_path = '{0}/{1}'.format(target_dir, os.path.basename(url))
    local_filepath, headers = urlretrieve(url, target_path, urlretrieve_progress)
    print('')
    return local_filepath

def install_firwmare_dependencies(repo):
    # Repo specific dependencies: create dir structure, move bios files if found in current dir
    repo = repo.split('/')[1]
    if repo == 'doom-odroid-go':
        mkdir_p('{0}/doom'.format(DATA_DIR))
    if repo == 'fMSX-go':
        mkdir_p('{0}/msx'.format(DATA_DIR))
        mkdir_p('{0}/msx/bios'.format(ROMS_DIR))
        mkdir_p('{0}/msx/games'.format(ROMS_DIR))
        if os.path.isfile('DISK.ROM'):
            shutil.move('DISK.ROM', '{0}/msx/bios'.format(ROMS_DIR))
        if os.path.isfile('MSX2.ROM'):
            shutil.move('MSX2.ROM', '{0}/msx/bios'.format(ROMS_DIR))
        if os.path.isfile('MSX2EXT.ROM'):
            shutil.move('MSX2EXT.ROM', '{0}/msx/bios'.format(ROMS_DIR))
    if repo == 'go-play':
        mkdir_p('{0}/col'.format(DATA_DIR))
        mkdir_p('{0}/gb'.format(DATA_DIR))
        mkdir_p('{0}/gbc'.format(DATA_DIR))
        mkdir_p('{0}/gg'.format(DATA_DIR))
        mkdir_p('{0}/nes'.format(DATA_DIR))
        mkdir_p('{0}/sms'.format(DATA_DIR))
        mkdir_p('{0}/col'.format(ROMS_DIR))
        mkdir_p('{0}/gb'.format(ROMS_DIR))
        mkdir_p('{0}/gbc'.format(ROMS_DIR))
        mkdir_p('{0}/gg'.format(ROMS_DIR))
        mkdir_p('{0}/nes'.format(ROMS_DIR))
        mkdir_p('{0}/sms'.format(ROMS_DIR))
        if os.path.isfile('BIOS.col'):
            shutil.move('BIOS.col', '{0}/col/BIOS.col'.format(ROMS_DIR))
    if repo == 'odroid-go-spectrum-emulator':
        mkdir_p('{0}/spectrum'.format(ROMS_DIR))
    if repo == 'prosystem-odroid-go':
        mkdir_p('{0}/a78'.format(ROMS_DIR))
    if repo == 'stella-odroid-go':
        mkdir_p('{0}/a26'.format(ROMS_DIR))

def install_firmware(repo, firmware_url, tag_name):
    download_file(firmware_url, FIRMWARE_DIR)
    install_firwmare_dependencies(repo)
    set_config_value(CONFIG_FILE, 'installed_releases', repo, tag_name)

def install_romart(force=False):
    # Check if romart already exists and skip download. Set force parameter to True to download regardless.
    print('=== Rom Art ===')
    if os.path.isdir(ROMART_DIR) and not force:
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
    
    #print(url)
    response = json.loads(urlopen(url).read().decode('utf-8'))
    print('Found release {0}'.format(response['tag_name']))
    
    # Look for a fw file in the release
    # TODO: this assumes there is only 1, returns the last found
    fw_idx = None
    fw_url = None
    tag_name = None
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
    if os.path.exists('{0}/col'.format(DATA_DIR)) and not os.path.isfile('{0}/col/BIOS.col'.format(ROMS_DIR)):
        print('* ColecoVison requires a BIOS.col in {0}/col'.format(ROMS_DIR))
    if os.path.exists('{0}/msx/bios'.format(ROMS_DIR)) and not (os.path.isfile('{0}/msx/bios/DISK.ROM'.format(ROMS_DIR)) and os.path.isfile('{0}/msx/bios/MSX2.ROM'.format(ROMS_DIR)) and os.path.isfile('{0}/msx/bios/MSX2EXT.ROM'.format(ROMS_DIR))):
        print('* fMSX-go requires BIOS files MSX2.ROM, MSX2EXT.ROM and DISK.ROM in {0}/msx/bios'.format(ROMS_DIR))
    print('* Hold B on first boot to reinstall your preferred app')


prepare_sd_card()
install_romart()

for repo in REPOS:
    print('=== {0} ==='.format(repo))
    firmware_url, release_tag_name = get_firmware_release(repo, REPOS[repo])
    
    if release_tag_name is not None:
        installed_tag_name = get_installed_release(repo)
        if release_tag_name == installed_tag_name:
            print('Skipping install, requested release matches installed version')
        else:
            install_firmware(repo, firmware_url, release_tag_name)
    else:
        print('ERROR: app firmware release not found, skipping install')

finalize_sd_card()
