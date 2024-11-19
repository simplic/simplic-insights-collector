from argparse import ArgumentParser
import json
import os
import shutil
import subprocess
from typing import Any, TypeVar
import venv

DEFAULT_DEPS = ['requests']

_T = TypeVar('_T')
def _cast(name: str, value: Any, to: type[_T]) -> _T:
    if isinstance(value, to):
        return value
    raise TypeError(f'expected {name} to be a {to.__name__}')

def setup_venv(path: str):
    print('Creating venv in', path)
    venv.create('./run/venv', with_pip=True, upgrade_deps=True)
    print('venv created')

def install_dependencies(python: str, deps: list[str]) -> bool:
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
parser.add_argument('-s', '--settings', default='./settings.json')
parser.add_argument('--debug', action='store_true')

args = parser.parse_args()

with open(args.settings, 'rt') as f:
    settings = json.load(f)

pkgs = set[str]()
deps = [dep for dep in DEFAULT_DEPS]
for sensor in settings['sensors']:
    sensor_id = _cast('type', sensor['type'], str)
    pkg, id = sensor_id.split(':')
    pkgs.add(pkg)

for pkg in pkgs:
    folder = os.path.join('sensors', pkg)
    config_file = os.path.join(folder, 'manifest.json')
    with open(config_file, 'rt') as f:
        config = json.load(f)
    if _cast('pkg', config['pkg'], str) != pkg:
        raise ValueError('package name mismatch')
    if not os.path.exists(os.path.join(folder, '__init__.py')):
        raise FileNotFoundError('Missing __init__.py')
    dependencies = _cast('dependencies', config['dependencies'], list)
    deps.extend(_cast('dependency', dep, str) for dep in dependencies)

dir_run = './run'
dir_venv = os.path.join(dir_run, 'venv')
dir_core = os.path.join(dir_run, 'core')
dir_sensors = os.path.join(dir_run, 'sensors')
python = os.path.join(dir_venv, 'bin', 'python')

if not os.path.isdir(dir_run):
    os.mkdir(dir_run)

if not os.path.isdir(dir_venv):
    setup_venv(dir_venv)

if not install_dependencies(python, deps):
    print('Trying clean venv')
    shutil.rmtree(dir_venv)
    if not install_dependencies(python, deps):
        print('There is a dependency resolution issue')

print('Installing sensor scripts')
if os.path.exists(dir_core):
    shutil.rmtree(dir_core)
shutil.copytree('./core', dir_core)
shutil.copyfile('./main.py', os.path.join(dir_run, 'main.py'))
if os.path.exists(dir_sensors):
    shutil.rmtree(dir_sensors)
    os.mkdir(dir_sensors)
for pkg in pkgs:
    src_path = os.path.join('./sensors', pkg)
    dst_path = os.path.join(dir_sensors, pkg)
    shutil.copytree(src_path, dst_path)

print('Setup complete')
subprocess.run(
    (
        './venv/bin/python', './main.py',
        os.path.abspath(args.settings),
        'debug' if args.debug else 'normal'
    ),
    cwd=dir_run)
