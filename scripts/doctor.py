#!/usr/bin/env python3
# Managed by linux-dev-bootstrap
"""Read-only hardware/tool inventory. No benchmarks, network requests or credential reads."""
import argparse
import csv
import io
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess

TOOLS=['bash','git','curl','python3','uv','node','npm','codex','tmux','rg','fd','rsync','gawk','tar','xz',
       'gcc','g++','make','cmake','pkg-config','docker','nvcc','nvidia-smi']
DEFAULT_REQUIRED=['bash','git','curl','python3','uv','node','npm','codex','tmux','rg','fd','rsync','gawk','tar','xz','blesh']

def command(args, timeout=8):
    try:
        p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
        text=(p.stdout or p.stderr).strip()
        # Terminal control bytes from any external command are never printed.
        text=''.join(c for c in text if c.isprintable() or c=='\n')
        return p.returncode,text[:3000]
    except (OSError,subprocess.TimeoutExpired) as exc:return 1,str(exc)

def read(path):
    try:return Path(path).read_text()
    except OSError:return ''

def inventory(home):
    release={}
    for line in read('/etc/os-release').splitlines():
        if '=' in line:
            key,value=line.split('=',1)
            try:release[key]=' '.join(shlex.split(value))
            except ValueError:release[key]=value
    cpus=read('/proc/cpuinfo').splitlines()
    model=next((line.split(':',1)[1].strip() for line in cpus if line.startswith(('model name','Hardware'))),'unknown')
    mem={}
    for line in read('/proc/meminfo').splitlines():
        key,_,value=line.partition(':')
        if value.split() and value.split()[0].isdigit():mem[key]=int(value.split()[0])*1024
    try:available_cpus=len(os.sched_getaffinity(0))
    except AttributeError:available_cpus=os.cpu_count()
    try:load=list(os.getloadavg())
    except OSError:load=None
    disk=shutil.disk_usage(home)
    hw={'os':release.get('PRETTY_NAME',platform.system()),'kernel':platform.release(),
        'architecture':platform.machine(),'libc':' '.join(platform.libc_ver()),'cpu_model':model,
        'logical_cpus':os.cpu_count(),'available_cpus':available_cpus,'load_1_5_15':load,
        'ram_total_gib':round(mem.get('MemTotal',0)/2**30,2),
        'ram_available_gib':round(mem.get('MemAvailable',0)/2**30,2),
        'home_disk':{'path':str(home),'total_gib':round(disk.total/2**30,2),'free_gib':round(disk.free/2**30,2)},
        'gpus':[],'gpu_status':'nvidia-smi unavailable (optional)'}
    smi=shutil.which('nvidia-smi')
    if smi:
        code,text=command([smi,'--query-gpu=index,name,driver_version,memory.total','--format=csv,noheader,nounits'],5)
        if code==0:
            for row in csv.reader(io.StringIO(text)):
                if len(row)>=4:
                    hw['gpus'].append({'index':row[0].strip(),'name':row[1].strip(),
                                      'driver':row[2].strip(),'vram_mib':row[3].strip()})
            hw['gpu_status']='ok' if hw['gpus'] else 'No NVIDIA GPUs reported'
        else:hw['gpu_status']='query failed: '+text[:200]
    return hw

def collect(required,home=None):
    home=Path(home) if home else Path.home()
    tools={}
    for name in TOOLS:
        executable=shutil.which(name) or (shutil.which('fdfind') if name=='fd' else None)
        if not executable:
            tools[name]={'available':False,'path':None,'version':None,'error':'not installed'};continue
        flag='-V' if name=='tmux' else '--version'
        code,text=command([executable,flag])
        # nvcc's relevant release appears after its copyright banner.
        version=next((line for line in text.splitlines() if 'release ' in line),text.splitlines()[0] if text else '') if name=='nvcc' else (text.splitlines()[0] if text else '')
        tools[name]={'available':code==0,'path':executable,'version':version,'error':'' if code==0 else text[:200]}
    ble=home/'.local/share/blesh/ble.sh'
    if ble.is_file():code,text=command(['bash',str(ble),'--version'])
    else:code,text=1,'not installed'
    tools['blesh']={'available':code==0,'path':str(ble) if ble.is_file() else None,
                    'version':text.splitlines()[0] if code==0 and text else None,'error':'' if code==0 else text[:200]}
    nvm=os.environ.get('DEV_DOCTOR_NVM_VERSION')
    tools['nvm']={'available':bool(nvm),'path':os.environ.get('NVM_DIR'),'version':nvm,'error':'' if nvm else 'not loaded'}
    configuration=[]
    if (home/'.config/jayson-dev/env.sh').exists():
        login=next((home/name for name in ['.bash_profile','.bash_login'] if (home/name).exists()),home/'.profile')
        for path in [home/'.bashrc',login,home/'.config/jayson-dev/env.sh',home/'.config/jayson-dev/bash.sh',home/'.local/bin/dev-run',home/'.local/bin/dev-doctor']:
            code,text=command(['bash','-n',str(path)]) if path.exists() else (1,'missing')
            configuration.append({'path':str(path),'ok':code==0,'error':'' if code==0 else text[:200]})
    missing=[name for name in required if not tools.get(name,{}).get('available')]
    success=not missing and all(item['ok'] for item in configuration)
    return {'schema_version':1,'hardware':inventory(home),'tools':tools,'configuration':configuration,
            'required_tools':required,'missing_required':missing,'ok':success}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json',action='store_true',help='machine-readable report')
    parser.add_argument('--require',default=','.join(DEFAULT_REQUIRED),help='comma-separated tools required for success')
    args=parser.parse_args()
    required=[name for name in args.require.split(',') if name]
    unknown=set(required)-set(TOOLS)-{'blesh','nvm'}
    if unknown:parser.error('Unknown required tools: '+','.join(sorted(unknown)))
    report=collect(required)
    if args.json:print(json.dumps(report,ensure_ascii=False,indent=2))
    else:
        h=report['hardware']
        print('=== HARDWARE (read-only) ===')
        print(f"OS: {h['os']} | kernel: {h['kernel']} | arch: {h['architecture']} | libc: {h['libc']}")
        print(f"CPU: {h['cpu_model']} | logical: {h['logical_cpus']} | available slots: {h['available_cpus']} | load: {h['load_1_5_15']}")
        print(f"RAM: {h['ram_available_gib']}/{h['ram_total_gib']} GiB available/total")
        d=h['home_disk'];print(f"Home disk: {d['path']} | {d['free_gib']}/{d['total_gib']} GiB free/total")
        for gpu in h['gpus']:print(f"GPU {gpu['index']}: {gpu['name']} | driver {gpu['driver']} | VRAM {gpu['vram_mib']} MiB")
        if not h['gpus']:print('GPU: '+h['gpu_status'])
        print('\n=== TOOL VERSIONS ===')
        for name,tool in report['tools'].items():
            state='OK' if tool['available'] else ('FAIL' if name in required else 'OPTIONAL')
            print(f"{state:8} {name:12} {tool['version'] or tool['error']}"+(f" | {tool['path']}" if tool['path'] else ''))
        print('\n=== CONFIGURATION ===')
        for item in report['configuration']:print(('OK   ' if item['ok'] else 'FAIL ')+item['path']+(' '+item['error'] if item['error'] else ''))
        if not report['configuration']:print('Managed configuration not present; inventory only.')
        print('\nRESULT: '+('PASS' if report['ok'] else 'FAIL')+(' | missing: '+','.join(report['missing_required']) if report['missing_required'] else ''))
    return 0 if report['ok'] else 1

if __name__=='__main__':raise SystemExit(main())
