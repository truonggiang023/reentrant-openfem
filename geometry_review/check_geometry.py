"""Independent topology/boundary checks, including floating point trim regression."""
from pathlib import Path
import json,sys,math
from collections import Counter,defaultdict
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE.parent/'opensource_pa12'))
from geometry_core import lattice,clip

def check(c):
    edges=lattice(c);H=c['H_wall'];t=c['thickness'];ys=sorted(set(round(p[1],6) for p,q in edges if abs(p[1]-q[1])<1e-7))
    assert len(ys)==16,ys
    boundary=[]
    for y in [ys[0],ys[-1]]:
        rows=[(p,q) for p,q in edges if abs(p[1]-q[1])<1e-7 and abs(p[1]-y)<1e-6]
        lengths=[abs(q[0]-p[0]) for p,q in rows]
        assert sum(abs(x-H)<1e-5 for x in lengths)==7,lengths
        assert sum(abs(x-H/2)<1e-5 for x in lengths)==1,lengths
        boundary.append(rows)
    # Bottom starts with half a wall at the left cut; top starts with a full wall.
    bottom=sorted(boundary[0]);top=sorted(boundary[1])
    assert abs(bottom[0][0][0]-t/2)<1e-7
    assert top[0][0][0]>t/2+1e-3
    assert not any(abs(p[0]-q[0])<1e-7 for p,q in edges)
    g=defaultdict(set)
    for p,q in edges:g[p].add(q);g[q].add(p)
    seen=set();stack=[next(iter(g))]
    while stack:
        p=stack.pop()
        if p in seen:continue
        seen.add(p);stack.extend(g[p]-seen)
    assert len(seen)==len(g),'Disconnected geometry'
    assert max(map(len,g.values()))<=3,'Unexpected crossing/duplicate topology'
    return dict(segments=len(edges),horizontal_levels=len(ys),intervals=len(ys)-1,
                degree_counts=dict(Counter(map(len,g.values()))),connected=True)

for case in ['envelope','local']:
    c=json.loads((BASE/('image_'+case+'_config.json')).read_text())
    print(case,check(c))
# Regression: an exactly on-boundary horizontal edge must not disappear after
# a few ulps of arithmetic drift. This was the missing top-wall bug.
box=(.4,.4,79.6,63.6)
assert clip((1.,63.60000000000001),(9.,63.60000000000001),box)==((1.,63.6),(9.,63.6))
assert clip((1.,63.601),(9.,63.601),box) is None
print('Geometry checks passed. Metric interpretation of paper dimensions is NOT confirmed.')
