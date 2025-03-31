from argparse import ArgumentParser
import os
import platform
import shutil
import subprocess
import urllib.parse
import venv
import requests
import urllib
import zipfile

from core.config import ReadDict, ReadValue, parse_file

# Dependencies required for uploading results
DEFAULT_DEPS = ['requests>=2', 'psutil']

DIR_RUN = './run'
DIR_VENV = './run/venv'
DIR_CORE = './run/core'
DIR_TEMP = './run/temp'
DIR_PACKAGES = './run/packages'

def mkdir_clean(dir: str):
    if os.path.isdir(dir):
        for item in os.listdir(dir):
            path = os.path.join(dir, item)
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
    else:
        os.mkdir(dir)

def _install_folder(package: ReadDict) -> ReadDict:
    path = package['path'].as_str()
    config_path = os.path.join(path, 'manifest.json')
    sensors_path = os.path.join(path, 'sensors')

    config = parse_file(config_path, 'manifest').as_dict()
    id = config['pkg'].as_str()

    print(f'Installing package {id!r} from {path}')

    dst_path = os.path.join(DIR_PACKAGES, id)
    config_dst_path = os.path.join(dst_path, 'manifest.json')
    sensors_dst_path = os.path.join(dst_path, 'sensors')

    mkdir_clean(dst_path)

    shutil.copyfile(config_path, config_dst_path)
    shutil.copytree(sensors_path, sensors_dst_path)

    return config

def _install_github(package: ReadDict) -> ReadDict:
    id = package['pkg'].as_str()
    owner = package['owner'].as_str()
    repo = package['repo'].as_str()
    version = package['version'].as_str('latest')

    owner_safe = urllib.parse.quote(owner)
    repo_safe = urllib.parse.quote(repo)

    session = requests.Session()

    print(f'Installing package {id!r} from GitHub')

    if version == 'latest':
        print(f'  Finding latest version on GitHub')

        response = session.get(f'https://api.github.com/repos/{owner_safe}/{repo_safe}/releases/latest')
        response.raise_for_status()
        value = ReadValue(response.json(), 'response').as_dict()
        tag_name = value['tag_name'].as_str()
        if not tag_name.startswith('v'):
            raise ValueError('Invalid tag name')
        version = tag_name[1:]

        print(f'  Latest version is {version}')

    dst_path = os.path.join(DIR_PACKAGES, id)
    config_dst_path = os.path.join(dst_path, 'manifest.json')
    sensors_dst_path = os.path.join(dst_path, 'sensors')

    old_version = None
    if os.path.exists(config_dst_path):
        config = parse_file(config_dst_path, 'manifest').as_dict()
        old_version = config['version'].as_str()

    if version != old_version:
        print(f'  Downloading {version}')

        version_safe = urllib.parse.quote(version)
        download_url = f'https://github.com/{owner_safe}/{repo_safe}/releases/download/v{version_safe}'

        mkdir_clean(dst_path)

        print('  Downloading manifest')
        response = requests.get(download_url + '/manifest.json', stream=True)
        response.raise_for_status()
        with open(config_dst_path, 'wb') as f:
            for chunk in response.iter_content():
                f.write(chunk)

        config = parse_file(config_dst_path).as_dict()
        new_id = config['pkg'].as_str()
        new_version = config['version'].as_str()
        if new_id != id:
            raise ValueError(f'  Package id mismatch: expected {id}, got {new_id}')
        if new_version != version:
            raise ValueError(f'  Package version mismatch: expected {version}, got {new_version}')

        print('  Downloading sensors')
        archive_path = os.path.join(DIR_TEMP, 'sensors.zip')
        response = requests.get(download_url + '/sensors.zip', stream=True)
        response.raise_for_status()
        with open(archive_path, 'wb') as f:
            for chunk in response.iter_content():
                f.write(chunk)

        print('  Unpacking sensors')
        with zipfile.ZipFile(archive_path, 'r') as z:
            z.extractall(sensors_dst_path)
    else:
        print(f'  Already up to date')

    return config # type: ignore

def install_package(package: ReadDict) -> ReadDict:
    """
    Install a sensor package from given source configuration
    """
    type_ = package['type'].as_str()
    match type_:
        case 'folder':
            return _install_folder(package)
        case 'github':
            return _install_github(package)
        case _:
            raise TypeError(f'Unknown package source type {type_!r}')
        
    return config

def setup_venv(path: str):
    """
    Create a virtual environment
    """
    print('Creating venv in', path)
    venv.create('./run/venv', with_pip=True, upgrade_deps=True)
    print('venv created')

def install_dependencies(python: str, deps: list[str]) -> bool:
    """
    Run pip and install the supplied list of dependency constraints
    """
    print('Installing dependencies')
    proc = subprocess.run((python, '-m', 'pip', 'install', *deps), stderr=subprocess.PIPE)
    if proc.returncode:
        print('Failed to install dependencies')
        return False
    print('Dependencies installed')
    return True


parser = ArgumentParser(
    prog='Simplic Insights Collector',
    description='Reads and sends sensor data to OxS'
)
parser.add_argument('-s', '--settings', default='./settings.json', help='Path to settings.json')
parser.add_argument('--debug', action='store_true', help='Enable debug mode')
parser.add_argument('--clean', action='store_true', help='Clean install packages and dependencies')

args = parser.parse_args()

settings = parse_file(args.settings, 'settings').as_dict()

if not os.path.isdir(DIR_RUN):
    os.mkdir(DIR_RUN)

mkdir_clean(DIR_TEMP)

# Create or empty package directory
if args.clean:
    mkdir_clean(DIR_PACKAGES)
else:
    if not os.path.isdir(DIR_PACKAGES):
        os.mkdir(DIR_PACKAGES)

print('Installing sensor packages')
packages = dict[str, ReadDict]()
for package in settings['packages'].as_list().iter_dict():
    config = install_package(package)
    id = config['pkg'].as_str()
    packages[id] = config

# Collect used sensors
used_packages = set[str]()
for sensor in settings['sensors'].as_list().iter_dict():
    sensor_id = sensor['type'].as_str()
    pkg, id = sensor_id.split(':')
    used_packages.add(pkg)

# Check if all packages have been installed
for package_id in used_packages:
    if package_id not in packages:
        raise KeyError(f'Missing package {package_id!r}')

# Collect dependencies
deps = [dep for dep in DEFAULT_DEPS]
for id, package in packages.items():
    if not os.path.exists(os.path.join(DIR_PACKAGES, id, 'sensors', '__init__.py')):
        raise FileNotFoundError('Missing __init__.py')
    deps.extend(package['dependencies'].as_list().iter_str())

match platform.system():
    case 'Linux':
        python = './run/venv/bin/python'
    case 'Windows':
        python = './run/venv/Scripts/python.exe'
    case _:
        raise RuntimeError('Unsupported OS')

if args.clean:
    clean_venv = True
else:
    if not os.path.isdir(DIR_VENV):
        setup_venv(DIR_VENV)
    clean_venv = not install_dependencies(python, deps)

if clean_venv:
    print('Cleaning venv')
    if os.path.exists(DIR_VENV):
        shutil.rmtree(DIR_VENV)
    setup_venv(DIR_VENV)
    if not install_dependencies(python, deps):
        print('Dependency resolution issue')
        print('Terminating')
        exit(-5)

if os.path.exists(DIR_CORE):
    shutil.rmtree(DIR_CORE)

shutil.copytree('./core', DIR_CORE)
shutil.copyfile('./main.py', os.path.join(DIR_RUN, 'main.py'))

print('Setup complete')

match platform.system():
    case 'Linux':
        python_run = './venv/bin/python'
    case 'Windows':
        python_run = './run/venv/Scripts/python.exe'
    case _:
        raise RuntimeError('Unsupported OS')

subprocess.run(
    (
        python_run, './main.py',
        os.path.abspath(args.settings),
        'debug' if args.debug else 'normal'
    ),
    cwd=DIR_RUN
)

print('Terminating')
