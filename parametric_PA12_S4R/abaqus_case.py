# -*- coding: utf-8 -*-
"""Import an exact generated INP into CAE and create an input-file job, not submit."""
from __future__ import print_function
import argparse,os,sys
BASE=os.path.dirname(os.path.abspath(__file__));sys.path.insert(0,BASE)
from write_model import build
from geometry_family import case_config

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--config',default=os.path.join(BASE,'baseline.json'));parser.add_argument('--out')
    argv=sys.argv[1:]
    if '--' in argv:argv=argv[argv.index('--')+1:]
    args,unknown=parser.parse_known_args(argv)
    config=case_config(os.path.abspath(args.config));out=os.path.abspath(args.out or os.path.join(BASE,'abaqus_output',config['case_id']))
    try:from abaqus import mdb
    except ImportError:mdb=None
    job='PA12_'+config['case_id']
    if mdb is not None and (job in mdb.models or job in mdb.jobs):raise ValueError('Model/job exists; choose a fresh CAE session or another case ID')
    meta=build(config,out);inp=os.path.join(out,meta['input_file'])
    print('Wrote exact S4R/R3D4 INP:',inp)
    if mdb is None:
        print('No CAE kernel: native INP generated only. No solver was executed.');return
    old=os.getcwd();os.chdir(out)
    try:
        from abaqusConstants import SINGLE,DEFAULT
        try:mdb.ModelFromInputFile(name=job,inputFileName=inp)
        except Exception as error:print('CAE import warning; exact INP remains available:',error)
        mdb.JobFromInputFile(name=job,inputFileName=inp,explicitPrecision=SINGLE,nodalOutputPrecision=SINGLE,numCpus=1,numDomains=1,multiprocessingMode=DEFAULT)
        mdb.saveAs(pathName=os.path.join(out,job+'.cae'))
        print('Saved CAE and exact input-file job. Data Check / Submit manually.')
    finally:os.chdir(old)

if __name__=='__main__':main()
