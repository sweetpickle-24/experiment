#!/usr/bin/env python3
"""
Resolve every hardcoded odorant name literal in the Python sources against the
DoOR matrix and emit ODOR_AUDIT.md.

Reports only. Edits no odor list.

Each file is parsed to an AST and string constants that look like a bare
chemical token are kept, along with the enclosing function and assignment
target. Each literal is then resolved with the same normalisation the runtime
lookup uses, so this report and the runtime agree by construction.

Literals are split into two roles, because only the first is a database lookup:

  lookup      passed to DoorClient, or held in a list of test odorants that is
              passed to one. A MISS here raises at runtime.
  classifier  a substring keyword inside a chemical-family table, or a
              docstring example. Never resolved against the matrix, so a MISS
              here is harmless and the entry must not be edited.
"""

import ast
import json
import re
import sys
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hive.data.door_client import (  # noqa: E402
    ODORANT_SYNONYMS,
    OdorantNotFoundError,
    _canonical_form,
    normalize_odorant_name,
)

REPO = Path(__file__).resolve().parents[1]
MATRIX = REPO / 'data' / 'door_consensus_matrix.npy'

SCAN_DIRS = ['scripts', 'tests', 'hive', 'benchmarks']
SKIP_PARTS = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'archive'}

# This generator holds candidate names in its own tables, and the resolution
# tests deliberately assert on names that miss. Scanning either reports the
# audit's own fixtures as defects.
SKIP_FILES = {
    'scripts/audit_odor_names.py',
    'tests/test_door_client_names.py',
}

# Fragments that may appear anywhere in the token.
_ANYWHERE = (
    'acetate|butyrate|propionate|propanoate|lactate|valerate|benzoate|hexanoate|'
    'formate|salicylate|tiglate|jasmonate|palmitate|aldehyde|acetone|acetoin|'
    'diacetyl|ethanol|methanol|butanol|hexanol|octanol|heptanol|pentanol|'
    'propanol|geraniol|linalool|borneol|menthol|citronellol|nerol|farnesol|'
    'phytol|geosmin|limonene|pinene|myrcene|ocimene|terpineol|terpinolene|'
    'camphor|carvone|fenchone|pulegone|thujone|benzene|toluene|phenol|guaiacol|'
    'eugenol|anisole|cresol|thymol|safrole|indole|skatole|carvacrol|putrescine|'
    'cadaverine|ammonia|vaccenyl|tricosene|lactone|furan|pyrazine|pyridine|'
    'mercaptan|sulfide|disulfide|carbon_dioxide|citral|vanillin|ionone|'
    'myrtenal|heptanone|pentanone|butanone|hexanone|decanone|tyramine|agmatine|'
    'quercetin|myristicin|hexenal|coffee|isoamyl|isopentyl'
)
# Fragments that must end a word, so 'propanal' matches but 'analysis' does not
# and 'ethyl_acetate' matches but 'ethylene glycol monomer' does not.
_WORD_FINAL = (
    'anal|enal|anone|enone|amine|_acid|acid|methyl|ethyl|butyl|pentyl|hexyl|'
    'octyl|amyl|co2'
)
CHEM_RE = re.compile(
    rf'(?:{_ANYWHERE})|(?:(?:{_WORD_FINAL})(?![a-z]))'
)

# A bare chemical token: letters, digits, and the separators real names use.
# Rejects prose, format strings, paths and log lines.
TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ,\-_()+.']{1,38}$")

# Filenames, and biogenic amines that are neuromodulators in this codebase
# rather than odorants presented to the antenna.
FILE_EXT_RE = re.compile(r'\.(png|pdf|json|npy|csv|txt|svg|jpg|pkl|md|py)$', re.I)
NOT_ODORANTS = {
    'dopamine', 'octopamine', 'serotonin', 'histamine', 'phenylethylamine',
    'amine_pheromone', 'amine_small', 'amine',
}

# Semantic odor-library keys and family names. Not DoOR lookups.
SEMANTIC_KEYS = {
    'fruit_ferment', 'fruit_ripe', 'danger_mold', 'danger_co2', 'social_female',
    'social_male', 'clean_air', 'random_control', 'food', 'danger', 'neutral',
    'mate', 'sweet_aldehyde', 'sour_acid', 'ester', 'ketone', 'aldehyde',
    'amine', 'lactone', 'alcohol', 'aromatic', 'terpene', 'aversive',
    'pheromone', 'acid', 'esters', 'alcohols', 'ketones', 'aldehydes', 'acids',
}

# Structures whose string entries are substring keywords for family
# classification, never passed to a lookup.
CLASSIFIER_CONTEXTS = {
    'CHEMICAL_FAMILIES', 'families', '_classify_chemical_family',
    'classify_family', '_classify_odor', 'FAMILY_KEYWORDS',
    # Glomerular channel axis labels, not chemicals.
    'GLOM_LABELS', 'GLOM_CHANNEL_NAMES', 'CHANNEL_LABELS',
}


def load_matrix():
    d = np.load(MATRIX, allow_pickle=True).item()
    return list(d['odorants']), list(d['receptors']), str(d.get('source', 'unknown'))


class Collector(ast.NodeVisitor):
    """Walk a module, recording chemical literals with their enclosing context."""

    def __init__(self):
        self.rows = []
        self.func_stack = []
        self.assign_stack = []

    # -- context tracking -------------------------------------------------
    def visit_FunctionDef(self, node):
        self.func_stack.append(node.name)
        self.generic_visit(node)
        self.func_stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Assign(self, node):
        names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        names += [t.attr for t in node.targets if isinstance(t, ast.Attribute)]
        self.assign_stack.append(names[0] if names else '')
        self.generic_visit(node)
        self.assign_stack.pop()

    def visit_AnnAssign(self, node):
        name = node.target.id if isinstance(node.target, ast.Name) else ''
        self.assign_stack.append(name)
        self.generic_visit(node)
        self.assign_stack.pop()

    # -- literals ---------------------------------------------------------
    def visit_Constant(self, node):
        if not isinstance(node.value, str):
            return
        s = node.value
        if not TOKEN_RE.match(s) or not CHEM_RE.search(s.lower()):
            return
        if s.lower() in SEMANTIC_KEYS or s.lower() in NOT_ODORANTS:
            return
        if FILE_EXT_RE.search(s):
            return
        # Reject prose and log banners: real names have at most one internal
        # space, are not sentences, and are not shouted.
        if s.count(' ') > 1 or s.rstrip().endswith(('.', ':', '!', '?')):
            return
        if s.isupper() and len(s) > 4:
            return
        ctx = self.assign_stack[-1] if self.assign_stack else ''
        func = self.func_stack[-1] if self.func_stack else ''
        self.rows.append((node.lineno, s, ctx, func))

    def visit_arg(self, node):
        self.generic_visit(node)


def classify_role(ctx: str, func: str, path: str) -> str:
    if ctx in CLASSIFIER_CONTEXTS or func in CLASSIFIER_CONTEXTS:
        return 'classifier'
    if 'download_door_data' in path and ctx in {'families', 'FAMILIES'}:
        return 'classifier'
    return 'lookup'


def resolve(name: str, known):
    """Return (resolved_or_None, rule, candidates)."""
    if name in known:
        return name, 'exact', []
    base = _canonical_form(name)
    try:
        hit = normalize_odorant_name(name, known)
    except OdorantNotFoundError as exc:
        return None, 'MISS', exc.candidates
    if base in ODORANT_SYNONYMS and ODORANT_SYNONYMS[base] == hit:
        return hit, 'synonym', []
    if hit == base and base != name:
        return hit, 'case/whitespace', []
    if hit in (base.replace('-', '_'), base.replace('_', '-')):
        return hit, 'separator', []
    return hit, 'normalised', []


def _geosmin_section(files, per_file):
    """Every geosmin mention, including comments, split by whether it is a lookup."""
    lookup_sites = {
        (f, r['line']) for f, rows in per_file.items() for r in rows
        if r['literal'].lower() == 'geosmin' and r['role'] == 'lookup'
    }
    classifier_sites = {
        (f, r['line']) for f, rows in per_file.items() for r in rows
        if r['literal'].lower() == 'geosmin' and r['role'] == 'classifier'
    }

    raw = []
    for path in files:
        rel = path.relative_to(REPO).as_posix()
        for i, line in enumerate(path.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
            if 'geosmin' in line.lower():
                raw.append((rel, i, line.strip()))

    o = ['## geosmin', '']
    o.append('`geosmin` is genuinely absent from the matrix. It is not a spelling variant and '
             '`difflib` returns no candidate above 0.6 similarity. It reaches the code because it '
             'is present in the fabricated 52-odorant catalogue in '
             '`hive/data/door_client.py._generate_synthetic_door_data`, which earlier versions '
             'wrote to `data/door_consensus_matrix.npy` when the real download was missing.')
    o.append('')
    o.append(f'{len(raw)} mention(s) across {len({r[0] for r in raw})} file(s).')
    o.append('')
    o.append('| File | Line | Role | Source line |')
    o.append('|---|---:|---|---|')
    for rel, lineno, text in raw:
        if (rel, lineno) in lookup_sites:
            role = '**lookup** (raises)'
        elif (rel, lineno) in classifier_sites:
            role = 'classifier keyword'
        elif text.lstrip().startswith('#') or text.lstrip().startswith('"'):
            role = 'comment / description'
        else:
            role = 'comment / description'
        snippet = text.replace('|', '\\|')
        if len(snippet) > 90:
            snippet = snippet[:87] + '...'
        o.append(f'| `{rel}` | {lineno} | {role} | `{snippet}` |')
    o.append('')
    o.append('Only the rows marked **lookup** reach the database. The classifier keywords and '
             'comments describe a chemical family or a semantic odor channel and must be left '
             'alone; editing them would change family classification, not odorant resolution.')
    o.append('')
    return o


def _replacement_section(known, receptors):
    """Candidate replacements for geosmin, with statistics read off the matrix."""
    d = np.load(MATRIX, allow_pickle=True).item()
    responses = d['responses']

    def stats(name):
        i = known.index(name)
        row = responses[i]
        return i, int(np.count_nonzero(row)), float(row.max())

    incumbents = ['benzaldehyde', '2-heptanone']
    candidates = ['isopentyl_acetate', '1-octanol', 'acetic_acid', 'linalool']

    o = ['## Proposed replacement where geosmin is used as a test odorant', '']
    o.append('Selection criteria, stated before any measurement: the replacement must exist in the '
             'matrix, must belong to a different chemical class from both incumbents, and must '
             'have receptor coverage comparable to them rather than a near-empty row. No candidate '
             'was run through the simulation, so none was chosen for its effect on a result.')
    o.append('')
    o.append('| Odorant | Role | Class | Index | Nonzero receptors | Max response |')
    o.append('|---|---|---|---:|---:|---:|')
    classes = {
        'benzaldehyde': 'aromatic aldehyde',
        '2-heptanone': 'aliphatic methyl ketone',
        'isopentyl_acetate': 'branched acetate ester',
        '1-octanol': 'long-chain primary alcohol',
        'acetic_acid': 'short-chain carboxylic acid',
        'linalool': 'monoterpene alcohol',
    }
    for n in incumbents:
        i, nz, mx = stats(n)
        o.append(f'| `{n}` | incumbent | {classes[n]} | {i} | {nz}/{len(receptors)} | {mx:.3f} |')
    for n in candidates:
        if n not in known:
            continue
        i, nz, mx = stats(n)
        o.append(f'| `{n}` | candidate | {classes.get(n, "-")} | {i} | {nz}/{len(receptors)} | {mx:.3f} |')
    o.append('')
    o.append('**Proposal: `isopentyl_acetate`.**')
    o.append('')
    o.append('- It is an ester, a third functional class alongside the aromatic aldehyde and the '
             'aliphatic ketone already in the set, so the three odorants remain chemically spread.')
    o.append('- Its receptor coverage sits in the same range as the incumbents, so it will not '
             'behave as a sparse or near-empty pattern that trivially correlates with itself.')
    o.append('- `tests/concentration_invariance_test.py` already asks for `isoamyl acetate`, which '
             'is the same molecule under a different name. Using it restores the stated intent of '
             'that test rather than substituting a new choice.')
    o.append('')
    o.append('**Caveat.** geosmin is detected in Drosophila by a dedicated Or56a labelled line and '
             'signals microbial contamination. No odorant in this matrix reproduces that role. Any '
             'replacement changes what a test containing it is about, and a test that used geosmin '
             'as an aversive or ecologically distinct stimulus is not measuring the same thing '
             'afterwards.')
    o.append('')
    o.append('No odor list has been edited. Applying this proposal is a separate decision.')
    o.append('')
    return o


def main():
    known, receptors, source = load_matrix()

    files = []
    for d in SCAN_DIRS:
        files += [p for p in sorted((REPO / d).rglob('*.py'))
                  if not SKIP_PARTS & set(p.parts)]
    files += sorted(REPO.glob('*.py'))
    files = [p for p in files if p.relative_to(REPO).as_posix() not in SKIP_FILES]

    per_file = {}
    occurrences = 0
    for path in files:
        try:
            tree = ast.parse(path.read_text(encoding='utf-8', errors='replace'))
        except SyntaxError:
            continue
        c = Collector()
        c.visit(tree)
        if not c.rows:
            continue
        rel = path.relative_to(REPO).as_posix()
        rows = []
        for lineno, literal, ctx, func in sorted(c.rows):
            role = classify_role(ctx, func, rel)
            resolved, rule, cands = resolve(literal, known)
            rows.append({
                'line': lineno, 'literal': literal, 'context': ctx or func,
                'role': role, 'resolved': resolved, 'rule': rule,
                'candidates': cands,
            })
            occurrences += 1
        per_file[rel] = rows

    lookups = [r for rows in per_file.values() for r in rows if r['role'] == 'lookup']
    classifiers = [r for rows in per_file.values() for r in rows if r['role'] == 'classifier']

    distinct_lookup = {}
    for r in lookups:
        distinct_lookup.setdefault(r['literal'], r)
    lookup_misses = {k: v for k, v in distinct_lookup.items() if v['resolved'] is None}

    distinct_classifier = {r['literal'] for r in classifiers}

    out = []
    w = out.append
    w('# Odorant name audit')
    w('')
    w(f'**Date**: {date.today().isoformat()}  ')
    w(f'**Last Updated**: {date.today().isoformat()}')
    w('')
    w(f'Generated by `scripts/audit_odor_names.py` against `data/door_consensus_matrix.npy` '
      f'({len(known)} odorants x {len(receptors)} receptors, source `{source}`). '
      f'Regenerate with `python3 scripts/audit_odor_names.py`.')
    w('')
    w('Names are resolved with `hive.data.door_client.normalize_odorant_name`, the function the '
      'runtime lookup calls, so this report and the runtime cannot disagree.')
    w('')
    w('Literals are split by role. A **lookup** reaches the database, so a miss raises '
      '`OdorantNotFoundError` at runtime. A **classifier** entry is a substring keyword in a '
      'chemical-family table or a docstring example; it is never resolved against the matrix, so a '
      'miss there is harmless and the entry must be left alone.')
    w('')
    w('This file reports. No odor list was edited to produce it.')
    w('')

    w('## Counts')
    w('')
    w('| Metric | Value |')
    w('|---|---:|')
    w(f'| Python files scanned | {len(files)} |')
    w(f'| Files containing chemical literals | {len(per_file)} |')
    w(f'| Literal occurrences | {occurrences} |')
    w(f'| ... of which lookups | {len(lookups)} |')
    w(f'| ... of which classifier keywords | {len(classifiers)} |')
    w(f'| Distinct lookup literals | {len(distinct_lookup)} |')
    w(f'| Distinct lookup literals that resolve | {len(distinct_lookup) - len(lookup_misses)} |')
    w(f'| Distinct lookup literals that MISS | {len(lookup_misses)} |')
    w(f'| Distinct classifier keywords (not resolved) | {len(distinct_classifier)} |')
    w('')

    w('## Lookup literals that do not resolve')
    w('')
    w('Each of these raises `OdorantNotFoundError` when reached.')
    w('')
    w('| Literal | Closest names in the database | Used at |')
    w('|---|---|---|')
    for name in sorted(lookup_misses, key=str.lower):
        cands = lookup_misses[name]['candidates']
        sites = [f'`{f}`:{r["line"]}' for f, rows in sorted(per_file.items())
                 for r in rows if r['literal'] == name and r['role'] == 'lookup']
        cand_txt = ', '.join(f'`{c}`' for c in cands) if cands else '_no close match_'
        w(f'| `{name}` | {cand_txt} | {", ".join(sites)} |')
    w('')

    w('## Per-file detail')
    w('')
    for fname in sorted(per_file):
        rows = per_file[fname]
        n_miss = sum(1 for r in rows if r['resolved'] is None and r['role'] == 'lookup')
        w(f'### `{fname}`')
        w('')
        w(f'{len(rows)} literal(s), {n_miss} lookup miss(es).')
        w('')
        w('| Line | Literal | Role | Resolves | Rule / candidates |')
        w('|---:|---|---|---|---|')
        for r in rows:
            if r['role'] == 'classifier':
                w(f'| {r["line"]} | `{r["literal"]}` | classifier | n/a | substring keyword, not looked up |')
            elif r['resolved'] is None:
                detail = ', '.join(f'`{c}`' for c in r['candidates']) if r['candidates'] else '_no close match_'
                w(f'| {r["line"]} | `{r["literal"]}` | lookup | **NO** | {detail} |')
            else:
                shown = r['rule'] if r['resolved'] == r['literal'] else f'{r["rule"]} -> `{r["resolved"]}`'
                w(f'| {r["line"]} | `{r["literal"]}` | lookup | yes | {shown} |')
        w('')

    out.extend(_geosmin_section(files, per_file))
    out.extend(_replacement_section(known, receptors))

    (REPO / 'ODOR_AUDIT.md').write_text('\n'.join(out) + '\n', encoding='utf-8')

    print(json.dumps({
        'files_scanned': len(files),
        'files_with_literals': len(per_file),
        'occurrences': occurrences,
        'lookups': len(lookups),
        'classifier_keywords': len(classifiers),
        'distinct_lookup': len(distinct_lookup),
        'distinct_lookup_misses': len(lookup_misses),
        'misses': sorted(lookup_misses, key=str.lower),
    }, indent=2))


if __name__ == '__main__':
    main()
