"""Markdown sections over quant's history: sizes, and what happens to their identity when headings change."""
import difflib, pickle, re, sys, statistics
from collections import Counter
sys.path.insert(0, '.')
import units as U
D = pickle.load(open(sys.argv[1], 'rb'))
H = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t#]*$", re.M)
def heads(t):
    return [(len(m.group(1)), m.group(2).strip()) for m in H.finditer(t or '')]
sizes = []
per_file = {}
for p, seq in D['states'].items():
    if not p.endswith('.md'): continue
    last = [s for s in seq if s['text'] is not None]
    if not last: continue
    t = last[-1]['text']
    us = U.md_units(t)
    per_file[p] = (len(t), len(us), max(e - s for s, e, k, u in us))
    sizes += [e - s for s, e, k, u in us]
print('files', len(per_file))
for p, (n, k, mx) in sorted(per_file.items(), key=lambda x: -x[1][0]):
    print(f'  {p:50s} {n:7d} chars  {k:4d} sections  largest {mx}')
print('section size: median', statistics.median(sizes), 'p90', sorted(sizes)[int(.9*len(sizes))], 'max', max(sizes), 'n', len(sizes))
# heading changes per transition
c = Counter(); trans = 0; examples = []
for p, seq in D['states'].items():
    if not p.endswith('.md'): continue
    prev = None
    for s in seq:
        if s['text'] is None or s['how'] == 'edit-unplaced':
            continue
        if prev is not None and prev['text'] != s['text']:
            trans += 1
            a, b = heads(prev['text']), heads(s['text'])
            if a == b:
                c['headings unchanged'] += 1; prev = s; continue
            sm = difflib.SequenceMatcher(None, [x[1] for x in a], [x[1] for x in b], autojunk=False)
            ren = add = rem = 0
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag == 'replace':
                    k = min(i2 - i1, j2 - j1); ren += k; add += (j2 - j1) - k; rem += (i2 - i1) - k
                    if len(examples) < 6: examples.append((p, a[i1][1][:50], b[j1][1][:50]))
                elif tag == 'insert': add += j2 - j1
                elif tag == 'delete': rem += i2 - i1
            c['transitions with heading changes'] += 1
            c['headings renamed'] += ren; c['headings added'] += add; c['headings removed'] += rem
        prev = s
print('md transitions', trans, dict(c))
for e in examples: print('  rename:', e)
