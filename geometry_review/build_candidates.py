"""Build two explicitly labelled geometry hypotheses. No solver is submitted."""
from pathlib import Path
import json,sys
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE.parent/'opensource_pa12'))
from build_radioss import write
for case in ['envelope','local']:
    c=json.loads((BASE/('image_'+case+'_config.json')).read_text())
    write(BASE/('image_'+case+'_candidate'),c)
print('Both files are geometry-review candidates; neither is paper-validated.')
