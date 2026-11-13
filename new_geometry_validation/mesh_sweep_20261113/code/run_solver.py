"""Run Starter/Engine with the release's bundled library paths, preserving logs."""
import argparse
import json
import re
import os
from pathlib import Path
import subprocess


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    parser.add_argument('--root',type=Path,default=Path(os.environ.get('OPENCOURANT_ROOT','/workspace/dependencies/opencourant/OpenCourant')))
    parser.add_argument('--threads',type=int,default=2)
    parser.add_argument('--starter-only',action='store_true')
    parser.add_argument('--vtk',action='store_true',help='Convert all animation frames for ParaView')
    parser.add_argument('--allow-initial-penetrations',action='store_true',help='Allow only inspected Starter warning 343; all warnings remain in logs/status')
    args=parser.parse_args()
    if args.threads<1: parser.error('threads must be positive')
    root=args.root.resolve(); work=args.directory.resolve()
    env=os.environ.copy()
    platform='win64' if os.name=='nt' else 'linux64'
    paths=[root/'extlib/hm_reader'/platform,root/'extlib/h3d/lib'/platform]
    env.update(RAD_CFG_PATH=str(root/'hm_cfg_files'),RAD_H3D_PATH=str(paths[1]),
               OMP_NUM_THREADS=str(args.threads),OMP_STACKSIZE='128m')
    if os.name=='nt':
        paths.extend([root/'extlib/intelOneAPI_runtime/win64',root/'exec'])
        env['PATH']=os.pathsep.join([str(x) for x in paths]+[env.get('PATH','')])
    else:env['LD_LIBRARY_PATH']=os.pathsep.join([str(x) for x in paths]+[env.get('LD_LIBRARY_PATH','')])
    def binary(stage):
        filename=stage+'_win64.exe' if os.name=='nt' else stage+'_linux64_gf'
        p=root/'exec'/filename
        if not p.is_file():parser.error('Missing executable: '+str(p))
        if os.name!='nt':p.chmod(p.stat().st_mode|0o100)
        return p
    stages=[('starter','compression_0000.rad')]
    if not args.starter_only: stages.append(('engine','compression_0001.rad'))
    result={}
    for stage,deck in stages:
        executable=binary(stage)
        if stage=='engine' and any(work.glob('compressionT*')):
            parser.error('Existing engine results detected; use a fresh run directory')
        log=work/f'{stage}.log'
        command=[str(executable),'-i',deck,'-nt',str(args.threads)]
        print('Running',stage,'in',work,flush=True)
        with log.open('w') as stream:
            completed=subprocess.run(command,cwd=work,env=env,stdout=stream,stderr=subprocess.STDOUT)
        result[stage]={'exit_code':completed.returncode,'log':str(log),'executable':str(executable)}
        (work/'run_status.json').write_text(json.dumps(result,indent=2)+'\n')
        if completed.returncode:
            print(log.read_text(errors='replace')[-6000:])
            raise SystemExit(completed.returncode if completed.returncode>0 else 1)
        text=log.read_text(errors='replace')
        bad=('ERROR TERMINATION' in text or re.search(r'ERROR ID\s*:',text) or 'RUN KILLED' in text or 'USER BREAK' in text)
        if stage=='starter':
            listing=(work/'compression_0000.out').read_text(errors='replace')
            ids=sorted(set(int(x) for x in re.findall(r'WARNING ID\s*:\s*(\d+)',listing)))
            allowed={343} if args.allow_initial_penetrations else set()
            result[stage]['warning_ids']=ids
            result[stage]['initial_penetration_warning_accepted']=343 in ids and args.allow_initial_penetrations
            (work/'run_status.json').write_text(json.dumps(result,indent=2)+'\n')
            bad=bad or not re.search(r'\b0 ERROR\(S\)',listing) or bool(set(ids)-allowed)
            finished=('NORMAL TERMINATION' in text or 'TERMINATION WITH WARNING' in text)
        else:
            finished='NORMAL TERMINATION' in text
        if bad or not finished:
            print(text[-6000:]); raise SystemExit(1)
        print(stage,'exit=0; see',log,flush=True)
    if not args.starter_only:
        converter=binary('th_to_csv')
        for history in sorted(work.glob('compressionT[0-9][0-9]')):
            with (work/(history.name+'_convert.log')).open('w') as stream:
                subprocess.run([str(converter),history.name],cwd=work,env=env,
                               stdout=stream,stderr=subprocess.STDOUT,check=True)

        if args.vtk:
            converter=binary('anim_to_vtk')
            vtk=work/'vtk';vtk.mkdir(exist_ok=True)
            for animation in sorted(work.glob('compressionA[0-9][0-9][0-9]')):
                with (vtk/(animation.name+'.vtk')).open('w') as stream:
                    subprocess.run([str(converter),animation.name],cwd=work,env=env,
                                   stdout=stream,stderr=subprocess.PIPE,check=True)

if __name__=='__main__': main()
