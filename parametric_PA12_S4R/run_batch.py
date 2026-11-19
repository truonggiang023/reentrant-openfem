"""Create each CAE in a separate Abaqus process; no job submission is added."""
from pathlib import Path
import argparse,json,subprocess,sys,os,shlex
BASE=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--dataset',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
p.add_argument('--abaqus',default='abaqus');p.add_argument('--execute',action='store_true');p.add_argument('--limit',type=int)
a=p.parse_args();manifest=json.loads((a.dataset/'manifest.json').read_text());cases=manifest['cases'][:a.limit] if a.limit else manifest['cases']
if a.execute:
    if a.out.exists():raise ValueError('Choose a NEW batch output folder')
    a.out.mkdir(parents=True)
for row in cases:
    case=(a.dataset/row['case_file']).resolve();dest=(a.out/row['case_id']).resolve()
    cmd=[a.abaqus,'cae','noGUI='+str(BASE/'abaqus_case.py'),'--','--config',str(case),'--out',str(dest)]
    print(subprocess.list2cmdline(cmd) if os.name=='nt' else shlex.join(cmd),flush=True)
    if a.execute:
        with (a.out/(row['case_id']+'.log')).open('w') as log:
            result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
        with (a.out/'batch_status.csv').open('a') as f:f.write('%s,%d\n'%(row['case_id'],result.returncode))
        if result.returncode:raise SystemExit('Case failed; inspect its log. No zero ML label was assigned.')
