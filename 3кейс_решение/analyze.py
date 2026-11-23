"""Запуск: python3 analyze.py каталог_с_дампом"""
import csv
import sys
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from statistics import median

root = Path(sys.argv[1])

def records(table):
    with (root / 'db_structure' / table).open(encoding='utf-8-sig') as schema:
        fields = next(csv.reader(schema, delimiter=';'))
    with (root / table).open(encoding='utf-8-sig') as data:
        yield from csv.DictReader(data, delimiter=';', fieldnames=fields)

products = {r['id']: r['name'] for r in records('product.csv')}
purchases = defaultdict(list)
trials = defaultdict(list)
seen = set()
for r in records('orders.csv'):
    assert r['id'] not in seen and r['product_id'] in products
    seen.add(r['id'])
    if r['status'] != 'paid':
        continue
    event = (datetime.fromisoformat(r['created_at']), r['product_id'])
    if r['trial'] == 't':
        trials[r['user_id']].append(event)
    elif r['trial'] == 'f' and Decimal(r['amount']) > 0:
        purchases[r['user_id']].append(event)

delays = []
tariffs = Counter()
for user, events in purchases.items():
    first, tariff = min(events)
    tariffs[products[tariff]] += 1
    prior = [stamp for stamp, _ in trials[user] if stamp < first]
    if prior:
        delays.append((first-min(prior)).total_seconds()/86400)
print('Заказы, покупатели, с предшествующим триалом, медиана дней:', len(seen),len(purchases),len(delays),median(delays))
print('Первая покупка по тарифам:',tariffs)
