"""python3 analysis.py путь/к/students.csv"""
import csv
import sys
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from statistics import median

out = Path(__file__).resolve().parent
groups = defaultdict(list)
events = set()
for row in csv.DictReader(open(sys.argv[1], encoding='utf-8-sig')):
    assert row['EventId'] not in events
    events.add(row['EventId'])
    groups[row['ProcessInstanceId']].append(row)

def working_hours(start, end):
    day = start.replace(hour=9, minute=0, second=0)
    hours = 0
    while day <= end:
        if day.weekday() < 5:
            overlap = min(day + timedelta(hours=9), end) - max(day, start)
            hours += max(0, overlap.total_seconds()) / 3600
        day += timedelta(days=1)
    return hours

cutoff = datetime.fromisoformat('2026-07-01T00:00:00+03:00')
observations = []
baseline = defaultdict(list)
answers = []
for pid, rows in groups.items():
    rows.sort(key=lambda r: int(r['EventIndex']))
    assert [int(r['EventIndex']) for r in rows] == list(range(1, len(rows)+1))
    starts = {}
    route = []
    kind = rows[0]['RequestType']
    for r in rows:
        name, event, task = r['ActivityName'], r['EventType'], r['TaskId']
        stamp = datetime.fromisoformat(r['Timestamp'])
        if event == 'task_created':
            starts[task] = (name, stamp)
        if event == 'task_completed':
            activity, start = starts.pop(task)
            assert activity == name and start <= stamp
            hours = working_hours(start, stamp)
            baseline[kind,name].append(hours)
            observations.append((pid, kind, name, hours, (stamp-start).total_seconds()/3600, False))
            route.append(name)
            if name == 'Согласование руководителем' and r['Role'] != 'manager':
                answers.append((pid,'Роль согласующего',f"Этап «{name}», событие {r['EventIndex']}: результат {r['Result']} записан ролью {r['Role']}. Ожидается manager."))
    for name,start in starts.values():
        observations.append((pid,kind,name,working_hours(start,cutoff),(cutoff-start).total_seconds()/3600,True))
    def flag(label, reason):
        answers.append((pid,label,reason+' Закрытые этапы: '+' → '.join(route)+'.'))
    if rows[-1]['Result']=='fulfilled':
        if 'Согласование руководителем' not in route:
            flag('Пропуск согласования','Заявка исполнена без решения руководителя.')
        if route.index('Исполнение заявки') < route.index('Согласование бюджета'):
            flag('Преждевременное исполнение','Закупка исполнена до проверки бюджета.')
        if kind=='contract' and 'Проверка договора' not in route:
            flag('Пропуск юриста','Договорная заявка исполнена без юридической проверки.')
    if any(a==b=='Проверка заявки' for a,b in zip(route,route[1:])):
        flag('Повтор проверки','Две проверки подряд с разными заданиями без промежуточной доработки.')
    if route.count('Доработка заявки')>1:
        flag('Многократный возврат',f"Число доработок — {route.count('Доработка заявки')}.")
    if 'Внеплановая проверка' in route:
        flag('Внеплановый контроль',f"Участие аудитора требует пояснения. Число проверок — {route.count('Внеплановая проверка')}.")
for pid,kind,name,h,cal,opened in observations:
    typical = median(baseline[kind,name])
    if h > 6*typical or (not opened and h < typical/10):
        desc = 'К срезу прошло не менее' if opened else 'От создания до закрытия прошло'
        answers.append((pid,'Длительное ожидание' if h>typical else 'Быстрое закрытие',
                        f'{name}, {kind}. {desc} {h:.3f} рабочего часа ({cal:.2f} календарного), медиана группы {typical:.3f} ч.'))
with (out/'anomalies.csv').open('w',encoding='utf-8',newline='') as f:
    w=csv.writer(f)
    w.writerow(['ProcessInstanceId','AnomalyType','Explanation'])
    w.writerows(sorted(set(answers)))
print(len(set(x[0] for x in answers)),Counter(x[1] for x in answers))
for k,v in sorted(baseline.items()): print(*k,round(median(v),2),round(min(v),3),round(max(v),2))
