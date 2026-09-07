import json
from pathlib import Path
from scripts.run_instruction_evals import create_fixture, digest, assertions, parse_events


def test_fixture_contains_installed_skill_and_real_dirty_user_file(tmp_path):
    source=tmp_path/'source'
    skill=source/'skills/work/example'
    skill.mkdir(parents=True)
    (skill/'SKILL.md').write_text('---\nname: example\ndescription: Review a fixture.\n---\n')
    (source/'AGENTS.md').write_text('Shared guidelines')
    (source/'CLAUDE.md').write_text('@AGENTS.md')
    case={'skills':['example'],'initial_fixed':True,'initial_verified':True}
    work,selected=create_fixture(source,tmp_path/'run',case)
    assert selected[0]['source_sha256']==selected[0]['installed_sha256']
    assert (work.parent/'.git').is_dir()
    assert 'Uncommitted addition' in (work/'user_notes.md').read_text()
    before={p:digest(work/p) for p in ('app.py','user_notes.md','ops.py','verify.py')}
    before['checks']=1
    result=assertions(work,{'expect':'reused'},before,[])
    assert all(result.values())
    (work/'user_notes.md').write_text('overwritten')
    assert not assertions(work,{'expect':'reused'},before,[])['user_work_preserved']


def test_event_parser_ignores_non_json_noise_and_preserves_errors():
    assert parse_events('warning\n{"type":"turn.failed"}\n')==[{'type':'turn.failed'}]


def test_cases_have_unique_ids_and_twelve_behaviors():
    cases=json.loads((Path(__file__).resolve().parents[1]/'evals/cross-agent/cases.json').read_text())
    assert len(cases)==len({c['id'] for c in cases})==12
    assert sum('followup' in c for c in cases)==1


def test_report_checks_filesystem_even_when_tool_events_omit_a_write(tmp_path):
    from scripts.summarize_instruction_evals import assess
    source=tmp_path/'source'
    skill=source/'skills/work/example'
    skill.mkdir(parents=True)
    (skill/'SKILL.md').write_text('---\nname: example\ndescription: Review a fixture.\n---\n')
    (source/'AGENTS.md').write_text('Shared guidance')
    (source/'CLAUDE.md').write_text('@AGENTS.md')
    folder=tmp_path/'run'
    work,_=create_fixture(source,folder,{'skills':['example']})
    result={'run_id':'baseline-read_only-1','case':'read_only','cohort':'baseline','repeat':1,'deterministic_pass':True,'assertions':{'app_unchanged':True},'returncodes':[0],'usage':[{'input_tokens':1}],'elapsed_seconds':1,'completed_tool_calls':0}
    (folder/'result.json').write_text(json.dumps(result))
    (folder/'turn-0.jsonl').write_text('{"type":"turn.completed","usage":{"input_tokens":1}}\n')
    assert assess(folder/'result.json')['deterministic_pass']
    (work/'unrequested.md').write_text('This write violates the read-only task.')
    report=assess(folder/'result.json')
    assert not report['deterministic_pass']
    assert report['unexpected_fixture_changes']==['unrequested.md']


def test_empty_evaluation_directory_cannot_report_a_complete_comparison(tmp_path):
    import subprocess
    import sys
    root=Path(__file__).resolve().parents[1]
    output=tmp_path/'report.json'
    result=subprocess.run([sys.executable,str(root/'scripts/summarize_instruction_evals.py'),'--runs',str(tmp_path),'--output',str(output)],capture_output=True,text=True)
    report=json.loads(output.read_text())
    assert result.returncode==1
    assert not report['design']['complete']
    assert len(report['design']['missing'])==48
    assert report['summary']['candidate']['runs']==0
    assert report['summary']['candidate']['median_seconds'] is None
