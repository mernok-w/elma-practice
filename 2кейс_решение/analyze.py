"""python3 analysis.py путь/к/students.csv"""
import csv
import sys
from pathlib import Path
from collections import defaultdict, Counter

out = Path(__file__).resolve().parent
groups = defaultdict(list)
for row in csv.DictReader(open(sys.argv[1], encoding='utf-8-sig')):
    groups[row['ProcessInstanceId']].append(row)
routes = defaultdict(list)
edges = Counter()
for pid, rows in groups.items():
    rows.sort(key=lambda r: int(r['EventIndex']))
    assert [int(r['EventIndex']) for r in rows] == list(range(1,len(rows)+1))
    assert (rows[0]['EventType'], rows[-1]['EventType']) == ('process_started','process_completed')
    route = tuple(r['ActivityName'] for r in rows)
    routes[route].append(pid)
    edges.update(zip(route,route[1:]))
with (out/'variants.csv').open('w', encoding='utf-8',newline='') as f:
    w = csv.writer(f)
    w.writerow(['Variant','Route','NumberOfCases','Share'])
    for i,(route,ids) in enumerate(sorted(routes.items(),key=lambda item:-len(item[1])),1):
        w.writerow([i,' > '.join(route),len(ids),len(ids)/len(groups)])
        print(i,ids[0],len(ids))
with (out/'student_transitions.csv').open('w', encoding='utf-8',newline='') as f:
    w = csv.writer(f)
    w.writerow(['SourceActivity','TargetActivity'])
    w.writerows(sorted(edges))
assert sum(edges.values()) == sum(map(len,groups.values()))-len(groups)
print(edges)
