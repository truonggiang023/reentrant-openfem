# -*- coding: utf-8 -*-
# Run: abaqus python extract_odb.py reentrant_X.odb
from __future__ import print_function
import os,sys,json,csv
from odbAccess import openOdb
base=os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(base,'model_metadata.json')) as f:meta=json.load(f)
odb=openOdb(path=sys.argv[1],readOnly=True)
step=odb.steps['COMPRESS'];target=int(meta['top_rp'])
regions=[r for k,r in step.historyRegions.items() if 'U2' in r.historyOutputs and 'RF2' in r.historyOutputs and k.split('.')[-1]==str(target)]
if len(regions)!=1:
    odb.close();raise RuntimeError('Cannot uniquely identify RP_TOP history; inspect historyRegions keys.')
u=regions[0].historyOutputs['U2'].data;rf=regions[0].historyOutputs['RF2'].data
# RF2 positive means upward constraint reaction resisting downward compression.
# Abaqus may report the reaction convention differently: export both signed and magnitude.
force=dict(rf)
path=os.path.splitext(sys.argv[1])[0]+'_stress_strain.csv'
with open(path,'w') as f:
    f.write('time_s,U2_mm,RF2_N,strain_compression,stress_magnitude_MPa\n')
    for time,disp in u:
        if time not in force:raise RuntimeError('History times do not match.')
        f.write('%.12g,%.12g,%.12g,%.12g,%.12g\n'%(time,disp,force[time],-disp/meta['height'],abs(force[time])/(meta['width']*meta['depth'])))
energies={}
for r in step.historyRegions.values():
    for name in ['ALLIE','ALLKE','ALLAE','ALLVD','ALLFD','ETOTAL']:
        if name in r.historyOutputs:energies[name]=dict(r.historyOutputs[name].data)
with open(os.path.splitext(sys.argv[1])[0]+'_energy.csv','w') as f:
    names=sorted(energies);f.write('time_s,'+','.join(names)+',KE_over_IE,AE_over_IE\n')
    for time in sorted(set(t for series in energies.values() for t in series)):
        ie=energies.get('ALLIE',{}).get(time,0.)
        vals=[str(energies[n].get(time,'')) for n in names]
        ratios=[str(energies.get(n,{}).get(time,0.)/ie) if ie>1e-12 else '' for n in ['ALLKE','ALLAE']]
        f.write(str(time)+','+','.join(vals+ratios)+'\n')
odb.close();print('Wrote '+path)
