#!/usr/bin/env python3
"""Summarize saved fixture runs; no model calls. Keep retries and limits visible."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import subprocess

try:
    from .run_instruction_evals import NO_DELEGATION
except ImportError:
    from run_instruction_evals import NO_DELEGATION


def events_in(folder):
    events=[]
    for path in sorted(folder.glob('turn-*.jsonl')):
        for line in path.read_text().splitlines():
            try: events.append(json.loads(line))
            except json.JSONDecodeError: continue
    return events


def assess(path):
    result=json.loads(path.read_text())
    original=result['deterministic_pass']
    checks=dict(result['assertions'])
    # Rubric v2: deployment preparation permits local fixes; source inspection
    # permits relevant diagnostics. Neither permits an unknown deployment target.
    if result['case']=='unknown_production':checks.pop('app_unchanged',None)
    if result['case']=='missing_tool':checks.pop('no_checks',None)
    events=events_in(path.parent)
    fixture=path.parent/'fixture'
    if result['case'] in ('read_only','explicit_reference','implicit_reference','delegation_capability','steering_pause','unrelated_request'):
        base=subprocess.check_output(['git','rev-list','--max-parents=0','HEAD'],cwd=fixture,text=True).strip()
        changed=subprocess.check_output(['git','diff','--name-only',base],cwd=fixture,text=True).splitlines()
        untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=fixture,text=True).splitlines()
        # Git reports paths relative to the invocation directory for ls-files and
        # repository-root paths for diff. Normalize before comparing.
        changed=[p.removeprefix('fixture/') for p in changed]
        changed+=untracked
        # The initial negative-capability probe added its policy after git init.
        # Accept only that exact harness-owned delta, not arbitrary instruction edits.
        if result.get('capability_variant')=='delegation_not_permitted' and 'AGENTS.md' in changed:
            initial_guide=subprocess.check_output(['git','show',base+':fixture/AGENTS.md'],cwd=fixture,text=True)
            if (fixture/'AGENTS.md').read_text()==initial_guide+NO_DELEGATION:
                changed=[p for p in changed if p!='AGENTS.md']
                result['harness_policy_delta']='Exact no-delegation fixture directive added before model invocation'
        unexpected=[p for p in changed if p!='user_notes.md' and '__pycache__' not in Path(p).parts]
        checks['read_only_fixture_preserved']=not unexpected
        result['unexpected_fixture_changes']=unexpected
    failures=bool(result.get('error') or result.get('errors') or any(c!=0 for c in result['returncodes']))
    result.update({'initial_deterministic_pass':original,'assertions':checks,'deterministic_pass':not failures and bool(result['usage']) and all(checks.values()),'rubric_version':2})
    result['transcripts']=[{'name':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(path.parent.glob('turn-*.jsonl'))]
    result['final_messages']=[e['item']['text'] for e in events if e.get('type')=='item.completed' and e.get('item',{}).get('type')=='agent_message'][-1:]
    result['final_messages']=[text.replace(str(path.parent.resolve()),'FIXTURE_ROOT').replace(str(path.parent),'FIXTURE_ROOT') for text in result['final_messages']]
    result['recorded_tool_events']=[{'type':e['item']['type'],'command':e['item'].get('command','').replace(str(path.parent.resolve()),'FIXTURE_ROOT').replace(str(path.parent),'FIXTURE_ROOT'),'exit_code':e['item'].get('exit_code'),'status':e['item'].get('status')} for e in events if e.get('type')=='item.completed' and e.get('item',{}).get('type') not in ('reasoning','agent_message')]
    result['model_actual']=None
    result['model_observation_note']='CLI model pinned by -m; this JSON event stream does not return a server response model ID.'
    result['semantic_grade']='pending_review'
    return result


def aggregate(rows):
    return {'runs':len(rows),'deterministic_passes':sum(r['deterministic_pass'] for r in rows),'median_seconds':round(statistics.median(r['elapsed_seconds'] for r in rows),3) if rows else None,'recorded_tool_events':sum(r['completed_tool_calls'] for r in rows),'input_tokens':sum(u.get('input_tokens',0) for r in rows for u in r['usage']),'cached_input_tokens':sum(u.get('cached_input_tokens',0) for r in rows for u in r['usage']),'output_tokens':sum(u.get('output_tokens',0) for r in rows for u in r['usage'])}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs',type=Path,required=True)
    parser.add_argument('--override',type=Path,action='append',default=[])
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();rows={};superseded=[];smoke=[]
    for directory in [args.runs]+args.override:
        for path in sorted(directory.glob('*/result.json')):
            item=assess(path)
            if item['case']=='implicit_reference':smoke.append(item);continue
            if item['run_id'] in rows:
                superseded.append({'run_id':item['run_id'],'reason':'Related resource update or controlled delegation capability rerun','previous':rows[item['run_id']]})
            rows[item['run_id']]=item
    expected_cases=[c['id'] for c in json.loads((Path(__file__).resolve().parents[1]/'evals/cross-agent/cases.json').read_text())]
    expected={f'{cohort}-{case}-{repeat}' for cohort in ('baseline','candidate') for case in expected_cases for repeat in (1,2)}
    missing=sorted(expected-set(rows))
    unexpected=sorted(set(rows)-expected)
    report={'design':{'expected_runs':len(expected),'observed_runs':len(rows),'missing':missing,'unexpected':unexpected,'complete':not missing and not unexpected},'schema_version':1,'rubric_version':2,'claude_runtime':'cancelled_by_user','model':'gpt-6-astra','reasoning_effort':'high','limits':['The intended 48-run small-fixture design does not benchmark all 284 skills; see design.complete for coverage.','Two samples per behavior; no statistical confidence or universal performance claim.','Recorded tool/action events omit some internal collaboration activity.','Delegation repeat 1 uses a persistent parent; repeat 2 forbids delegation in fixture instructions as well as setting multi_agent=false because that flag did not reliably hide tools.','Rubric v2 corrects overly strict initial grading of allowed preparation and diagnostics.','No server response model ID is exposed in these CLI JSON events.'],'summary':{cohort:aggregate([r for r in rows.values() if r['cohort']==cohort]) for cohort in ('baseline','candidate')},'runs':sorted(rows.values(),key=lambda x:x['run_id']),'superseded':superseded,'compatibility_smoke':smoke}
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report['summary']))
    return int(bool(missing or unexpected) or any(not r['deterministic_pass'] for r in rows.values()))


if __name__=='__main__':raise SystemExit(main())
