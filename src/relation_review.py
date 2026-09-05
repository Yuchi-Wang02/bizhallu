"""Local score-blind calibration packet and strict response validation; no predictions."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT/'configs/relation_annotation_v2.json'
PACKET_DIR = ROOT/'outputs/relation_calibration_v2'
ADMIN_DIR = ROOT/'outputs/relation_calibration_admin_v2'
PUBLIC_REPORT = ROOT/'reports/bizhallu_relation_calibration_v2_report.json'
TEMPLATE = ROOT/'app/relation_review_template.html'
SCRIPT = ROOT/'app/relation_review.js'
PACKET_KEYS = {'protocol_id','packet_id','offset_unit','rules','enums','cases'}
CASE_KEYS = {'case_id','question','answer','messages','evidence_rows','evidence_scope_note'}
ATOM_KEYS = {'atom_id','start','end','text','type','syntax'}
RELATION_KEYS = {'relation_id','type','atom_ids','claim_group','count_role','period','period_origin','entity','counterparty','metric',
                 'rank_or_comparison','value','unit','row_fidelity','numeric_check','verdict','evidence_refs','search_scope_complete',
                 'reason','available_after_char'}
RESPONSE_CASE_KEYS = {'case_id','status','prior_exposure','coverage_checked','coverage_note','atoms','relations'}
RESPONSE_KEYS = {'protocol_id','packet_id','reviewer_id','reviewer_type','legacy_labels_seen','cases'}
EVIDENCE_COLUMNS = {'country','year_month','stock_code','description','net_revenue','gross_positive_revenue','cancellation_revenue','invoice_count'}


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8-sig').splitlines() if line.strip()]


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',',':'), allow_nan=False)


def sha(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def text_sha(path):
    return hashlib.sha256(path.read_text(encoding='utf-8-sig').replace('\r\n','\n').encode()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=True,allow_nan=False)+'\n',encoding='utf-8')


def unique(rows, key):
    values = {r[key]:r for r in rows}
    if len(values)!=len(rows) or any(not k for k in values):
        raise ValueError('Duplicate or empty IDs')
    return values


def project_case(generation, prompt, case_id):
    messages = [{'role':m['role'],'content':m['content']} for m in prompt['messages']]
    if [m['role'] for m in messages] != ['system','user']:
        raise ValueError('Expected system and user messages')
    # Preserve the actual evidence order shown to the model; no answer-sorted view.
    if any(m['content'] not in generation['prompt'] for m in messages):
        raise ValueError('Saved model input does not contain the source messages')
    for row in prompt['prompt_evidence_rows']:
        require(set(row)<=EVIDENCE_COLUMNS, 'Unexpected evidence metadata; blind projection rejected')
    return {'case_id':case_id, 'question':prompt['source_question_record']['question'],
            'answer':generation['generated_text'], 'messages':messages,
            'evidence_rows':[{'row_id':f'E{i+1:03}', 'values':dict(row)} for i,row in enumerate(prompt['prompt_evidence_rows'])],
            'evidence_scope_note':'Only the evidence shown in the original prompt is available. Do not assume the displayed rows cover the entire catalog or every causal explanation.'}


def packet_for(cases, config):
    packet = {'protocol_id':config['protocol_id'], 'offset_unit':'unicode_code_points_0_based_end_exclusive',
              'rules':config['business_rules'],
              'enums':{k:config[k] for k in ['atom_types','syntax_statuses','relation_types','verdicts','row_verdicts','numeric_checks','period_origins','count_roles']},
              'cases':cases}
    packet['packet_id'] = sha(packet)
    validate_packet(packet)
    return packet


def blank_response(packet):
    return {'protocol_id':packet['protocol_id'],'packet_id':packet['packet_id'],
            'reviewer_id':'','reviewer_type':'','legacy_labels_seen':'unknown',
            'cases':[{'case_id':c['case_id'],'status':'draft','prior_exposure':'unknown','coverage_checked':False,
                      'coverage_note':'','atoms':[],'relations':[]} for c in packet['cases']]}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def exact_keys(value, keys, name):
    require(isinstance(value,dict) and set(value)==keys, f'{name}: unexpected or missing fields')


def validate_packet(packet):
    exact_keys(packet, PACKET_KEYS, 'packet')
    require(packet['packet_id']==sha({k:v for k,v in packet.items() if k!='packet_id'}), 'Packet commitment mismatch')
    require(packet['offset_unit']=='unicode_code_points_0_based_end_exclusive', 'Wrong offset unit')
    unique(packet['cases'],'case_id')
    for case in packet['cases']:
        exact_keys(case, CASE_KEYS, 'case projection')
        require(isinstance(case['question'],str) and isinstance(case['answer'],str) and bool(case['answer']), 'Missing question/answer')
        require([m['role'] for m in case['messages']]==['system','user'], 'Message scope')
        for m in case['messages']:
            exact_keys(m, {'role','content'}, 'message')
        unique(case['evidence_rows'],'row_id')
        for row in case['evidence_rows']:
            exact_keys(row, {'row_id','values'}, 'evidence row')
            require(isinstance(row['values'],dict), 'Invalid table row')
            require(set(row['values'])<=EVIDENCE_COLUMNS, 'Unexpected evidence column')
            require(all(v is None or isinstance(v,str) or (type(v) in [int,float] and math.isfinite(v)) for v in row['values'].values()), 'Evidence must contain finite scalar values')


def validate_response(response, packet, require_complete=False):
    """Schema/coverage attestation checks, not automated correctness adjudication."""
    validate_packet(packet)
    exact_keys(response, RESPONSE_KEYS, 'response')
    for k in ['protocol_id','packet_id']:
        require(response[k]==packet[k], 'Response belongs to a different protocol/packet')
    require(isinstance(response['reviewer_id'],str), 'Reviewer ID must be text')
    require(response['reviewer_type'] in ['', 'owner_self_reported','independent_reviewer_self_reported','assistant'], 'Reviewer type invalid')
    require(response['legacy_labels_seen'] in ['yes','no','unknown'], 'Exposure invalid')
    source = unique(packet['cases'],'case_id')
    reviewed = unique(response['cases'],'case_id')
    require(set(source)==set(reviewed), 'All packet cases must be represented exactly once')
    atom_count = relation_count = completed = 0
    enums = packet['enums']
    for cid, case in reviewed.items():
        exact_keys(case, RESPONSE_CASE_KEYS, 'response case')
        require(case['status'] in ['draft','complete'], 'Case status invalid')
        require(case['prior_exposure'] in ['yes','no','unknown'], 'Case exposure invalid')
        require(type(case['coverage_checked']) is bool and isinstance(case['coverage_note'],str), 'Coverage type invalid')
        atoms = unique(case['atoms'],'atom_id')
        require(len({(a['start'],a['end'],a['type']) for a in atoms.values()})==len(atoms), 'Duplicate atom occurrence')
        for atom in atoms.values():
            exact_keys(atom, ATOM_KEYS, 'atom')
            require(type(atom['start']) is int and type(atom['end']) is int, 'Offsets must be integers')
            require(0<=atom['start']<atom['end']<=len(source[cid]['answer']), 'Offset out of bounds')
            require(source[cid]['answer'][atom['start']:atom['end']]==atom['text'], 'Span text does not match character range')
            require(atom['type'] in enums['atom_types'] and atom['syntax'] in enums['syntax_statuses'], 'Neutral type/syntax invalid')
        relations = unique(case['relations'],'relation_id')
        refs = {r['row_id'] for r in source[cid]['evidence_rows']}
        group_primary = {}
        for rel in relations.values():
            exact_keys(rel, RELATION_KEYS, 'relation')
            require(rel['type'] in enums['relation_types'] and rel['count_role'] in enums['count_roles'], 'Relation type/count role invalid')
            require(rel['verdict'] in enums['verdicts'] and rel['row_fidelity'] in enums['row_verdicts'], 'Verdict invalid')
            require(rel['numeric_check'] in enums['numeric_checks'] and rel['period_origin'] in enums['period_origins'], 'Numeric/period origin invalid')
            for key in ['claim_group','period','entity','counterparty','metric','rank_or_comparison','value','unit','reason']:
                require(isinstance(rel[key],str), f'{key} must be text; preserve lexical numbers')
            require(bool(rel['claim_group'].strip()), 'Claim group required')
            ids = rel['atom_ids']
            require(isinstance(ids,list) and bool(ids) and len(set(ids))==len(ids) and set(ids)<=set(atoms), 'Dangling or duplicate atom references')
            require(type(rel['available_after_char']) is int and rel['available_after_char']==max(atoms[a]['end'] for a in ids), 'Information endpoint must include all linked answer atoms')
            require(isinstance(rel['evidence_refs'],list) and len(set(rel['evidence_refs']))==len(rel['evidence_refs']) and set(rel['evidence_refs'])<=refs, 'Invalid evidence references')
            require(type(rel['search_scope_complete']) is bool, 'Scope declaration must be boolean')
            if rel['verdict']=='unmatched' or rel['row_fidelity']=='unmatched':
                require(rel['search_scope_complete'] and rel['reason'].strip(), 'Unmatched needs explicit complete search scope and reason')
                require(rel['numeric_check']!='not_parseable', 'Unparsed numbers must not become unmatched')
            if rel['verdict'] in ['supported','contradicted'] or rel['row_fidelity'] in ['supported','contradicted']:
                require(bool(rel['evidence_refs']) and bool(rel['reason'].strip()), 'Decisive judgment needs evidence and reason')
            if rel['verdict'] in ['supported','contradicted']:
                require(any(atoms[a]['type']!='rank_marker' for a in ids), 'A list marker alone cannot carry a decisive business relation')
                if rel['type']=='ranked_entity_value':
                    require(rel['entity'].strip() and rel['rank_or_comparison'].strip(), 'Rank binding requires the generated entity and rank/comparison')
            if rel['count_role']=='primary':
                require(rel['claim_group'] not in group_primary, 'Multiple primary counts for the same claim group')
                group_primary[rel['claim_group']]=rel['relation_id']
        for rel in relations.values():
            if rel['count_role']!='primary':
                require(rel['claim_group'] in group_primary, 'Repeat/contradiction needs a primary relation in its group')
        if case['status']=='complete':
            require(bool(response['reviewer_id'].strip()) and bool(response['reviewer_type']), 'Reviewer provenance required')
            require(case['coverage_checked'], 'Complete case requires explicit full-answer coverage attestation')
            require(bool(relations) or bool(case['coverage_note'].strip()), 'Empty completed answer requires explanation')
            require(all(r['reason'].strip() for r in relations.values()), 'Completed relations require reasons, including abstentions')
            linked = {aid for r in relations.values() for aid in r['atom_ids']}
            require(linked==set(atoms), 'Completed case contains unlinked atoms')
            completed += 1
        atom_count += len(atoms)
        relation_count += len(relations)
    if require_complete:
        require(completed==len(source), 'Review is incomplete; empty/draft templates are not labels')
    return {'case_count':len(source),'completed_case_count':completed,'atom_count':atom_count,'relation_count':relation_count,
            'ready_for_adjudication':completed==len(source), 'independent_human_review_verified':False,
            'ready_for_detector_metrics':False}


def check_response(response, packet, case_id=None, require_complete=False):
    """Check a first-case submission without treating the other drafts as reviewed."""
    result = validate_response(response, packet, require_complete and case_id is None)
    if case_id is not None:
        cases = unique(response['cases'], 'case_id')
        require(case_id in cases, 'Requested case does not exist in this packet')
        case = cases[case_id]
        if require_complete:
            require(case['status']=='complete', 'Requested case is still a draft; not submitted for review')
        result['requested_case'] = {
            'case_id':case_id, 'status':case['status'],
            'atom_count':len(case['atoms']), 'relation_count':len(case['relations']),
            'ready_for_case_adjudication':case['status']=='complete',
        }
    result['validation_scope'] = 'structure_and_self_reported_coverage_only'
    result['semantic_accuracy_verified'] = False
    return result


def safe_script_json(value):
    return json.dumps(value,ensure_ascii=True,allow_nan=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')


def render(packet):
    template = TEMPLATE.read_text(encoding='utf-8')
    require(template.count('__PACKET_JSON__')==1 and template.count('__REVIEW_JS__')==1, 'Template anchors invalid')
    return template.replace('__REVIEW_JS__',SCRIPT.read_text(encoding='utf-8'),1).replace('__PACKET_JSON__',safe_script_json(packet),1)


def build():
    # Existing local prompt renderer validates evidence faithfully; pandas is
    # already part of the local pipeline and is not needed for public checks.
    from build_prompts import markdown_table, ordered_rows
    config = load(CONFIG)
    generations_path = ROOT/'outputs/qwen_full100_generations.jsonl'
    prompts_path = ROOT/'outputs/qwen_input_prompts.jsonl'
    questions_path = ROOT/'data/processed/business_questions_gold.jsonl'
    generations = unique(jsonl(generations_path),'question_id')
    prompts = unique(jsonl(prompts_path),'question_id')
    questions = unique(jsonl(questions_path),'question_id')
    selected = config['selection']['fixed_question_ids']
    require(len(selected)==len(set(selected))==5, 'Calibration requires exactly five fixed questions')
    ordered = sorted(selected,key=lambda q:sha([config['selection']['ordering_salt'],q]))
    cases, mapping = [], []
    for i,qid in enumerate(ordered):
        gen,prompt,q = generations[qid],prompts[qid],questions[qid]
        require(gen['question_id']==prompt['question_id']==qid and gen['prompt_id']==prompt['prompt_id'], 'Source join failed')
        require(q['split'] in ['dev','test'], 'Historical dev/test only')
        require(prompt['source_question_record']['question']==q['question'], 'Question drift')
        require(prompt['prompt_evidence_rows']==ordered_rows(q)[0], 'Evidence scope/order drift')
        require(prompt['evidence_table_markdown']==markdown_table(prompt['prompt_evidence_rows']), 'Structured/text evidence mismatch')
        require(prompt['evidence_table_markdown'] in prompt['messages'][1]['content'], 'Evidence not in model message')
        cid=f'B{i+1:02}'
        cases.append(project_case(gen,prompt,cid))
        mapping.append({'case_id':cid,'question_id':qid,'split':q['split'],'question_type':q['question_type'],'answer_sha256':sha(gen['generated_text'])})
    packet = packet_for(cases,config)
    blank = blank_response(packet)
    template_status = validate_response(blank,packet)
    PACKET_DIR.mkdir(parents=True,exist_ok=True)
    # Never overwrite reviewer edits; only generated inputs are managed here.
    if (PACKET_DIR/'packet.json').exists():
        require(load(PACKET_DIR/'packet.json')==packet, 'Existing packet differs; create a new protocol/output version')
    write_json(PACKET_DIR/'packet.json',packet)
    template_path = PACKET_DIR/'review_template.json'
    if template_path.exists():
        require(load(template_path)==blank, 'Review template was edited; preserving it, use a new output version')
    write_json(template_path,blank)
    (PACKET_DIR/'review.html').write_text(render(packet),encoding='utf-8')
    write_json(ADMIN_DIR/'mapping.json',{'protocol_id':packet['protocol_id'],'packet_id':packet['packet_id'],'mapping':mapping})
    report = {'status':'C1_calibration_packet_prepared_not_reviewed','protocol_id':packet['protocol_id'],'packet_id':packet['packet_id'],
        'case_count':5,'question_type_count':len({r['question_type'] for r in mapping}),
        'contains_missing_dev_question': 'q_0048' in selected,
        'selection':'Purposive historical calibration; two already-public ranking cases; not representative or independently blind.',
        'template_status':template_status,
        'reviewer_input_fields':sorted(CASE_KEYS),
        'excluded_fields':['gold_answer','gold_facts','old_annotation_spans','old_labels','detector_scores','detector_outcomes','split','source_question_id'],
        'source_text_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):text_sha(p) for p in [CONFIG,TEMPLATE,SCRIPT,Path(__file__),questions_path]},
        'local_source_text_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):text_sha(p) for p in [generations_path,prompts_path]},
        'local_outputs':{'packet':'outputs/relation_calibration_v2/packet.json','page':'outputs/relation_calibration_v2/review.html',
                         'template':'outputs/relation_calibration_v2/review_template.json','admin_mapping':'outputs/relation_calibration_admin_v2/mapping.json'},
        'boundaries':config['boundaries'], 'prepared_for_owner_trial':True,'interface_acceptance':'pending_visual_and_owner_trial','ready_for_new_metrics':False,
        'visual_review':'not_performed_browser_security_boundary; structural_and_node_tests_only'}
    write_json(PUBLIC_REPORT,report)
    return report


def validate_bundle(require_local=False):
    report,config = load(PUBLIC_REPORT),load(CONFIG)
    require(report['protocol_id']==config['protocol_id'] and report['case_count']==len(config['selection']['fixed_question_ids'])==5, 'Protocol/coverage drift')
    for name,checksum in report['source_text_sha256'].items():
        require(text_sha(ROOT/name)==checksum, 'Public source fingerprint changed')
    require(report['template_status']=={'case_count':5,'completed_case_count':0,'atom_count':0,'relation_count':0,
        'ready_for_adjudication':False,'independent_human_review_verified':False,'ready_for_detector_metrics':False}, 'Blank packet is not a reviewed label set')
    require(report['ready_for_new_metrics'] is False, 'Metrics gate must remain closed')
    scope='public_protocol_and_source_fingerprints_only'
    if require_local:
        for name,checksum in report['local_source_text_sha256'].items():
            require(text_sha(ROOT/name)==checksum, 'Local source fingerprint changed')
        packet,blank = load(PACKET_DIR/'packet.json'),load(PACKET_DIR/'review_template.json')
        validate_packet(packet)
        require(packet['rules']==config['business_rules'] and packet['enums']=={k:config[k] for k in packet['enums']}, 'Reviewer rules/enums drift')
        require(packet['packet_id']==report['packet_id'], 'Packet hash mismatch')
        require(validate_response(blank,packet)==report['template_status'], 'Template changed')
        require(blank==blank_response(packet), 'Template must remain entirely blank')
        admin=load(ADMIN_DIR/'mapping.json')
        require(admin['packet_id']==packet['packet_id'], 'Admin mapping is stale')
        require(set(r['question_id'] for r in admin['mapping'])==set(config['selection']['fixed_question_ids']), 'Selection mismatch')
        generations=unique(jsonl(ROOT/'outputs/qwen_full100_generations.jsonl'),'question_id')
        prompts=unique(jsonl(ROOT/'outputs/qwen_input_prompts.jsonl'),'question_id')
        for c,row in zip(packet['cases'],admin['mapping']):
            require(c==project_case(generations[row['question_id']],prompts[row['question_id']],row['case_id']), 'Local case projection mismatch')
        require((PACKET_DIR/'review.html').read_text(encoding='utf-8')==render(packet), 'HTML contains data/code not in the approved packet/template')
        scope='five_source_questions_answers_and_score_blind_projection_replayed; no_completed_reviews'
    return {'status':'relation_calibration_packet_validated','validation_scope':scope,'num_failures':0,
            'independent_human_review_verified':False,'ready_for_new_metrics':False}


def validate_and_record(require_local=False):
    try:
        result=validate_bundle(require_local)
        result['validated_report_text_sha256']=text_sha(PUBLIC_REPORT)
    except (ValueError,KeyError,TypeError,OSError,IndexError) as exc:
        result={'status':'relation_calibration_validation_failed','num_failures':1,
                'validation_scope':'local_requested' if require_local else 'public_only',
                'failure':str(exc) if isinstance(exc,ValueError) else type(exc).__name__,
                'independent_human_review_verified':False,'ready_for_new_metrics':False}
    name='bizhallu_relation_calibration_v2_local_validation.json' if require_local else 'bizhallu_relation_calibration_v2_validation.json'
    write_json(ROOT/'reports'/name,result)
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['build','validate','check-response'])
    parser.add_argument('--require-local',action='store_true')
    parser.add_argument('--responses',type=Path)
    parser.add_argument('--require-complete',action='store_true')
    parser.add_argument('--case-id',help='Check one submitted case, leaving other cases as drafts')
    args=parser.parse_args()
    if args.command!='check-response' and (args.case_id is not None or args.responses is not None or args.require_complete):
        parser.error('--case-id, --responses and --require-complete are only for check-response')
    if args.command=='build':
        result=build()
        print(json.dumps({k:result[k] for k in ['status','case_count','packet_id','template_status']},indent=2))
    elif args.command=='validate':
        result=validate_and_record(args.require_local)
        print(json.dumps(result,indent=2))
        if result['num_failures']:raise SystemExit(1)
    else:
        if args.responses is None:
            parser.error('--responses is required for check-response')
        try:
            result=check_response(load(args.responses),load(PACKET_DIR/'packet.json'),args.case_id,args.require_complete)
        except (ValueError,KeyError,TypeError,OSError,IndexError) as exc:
            print(json.dumps({'status':'response_validation_failed','num_failures':1,
                'failure':str(exc) if isinstance(exc,ValueError) else type(exc).__name__,
                'semantic_accuracy_verified':False,'independent_human_review_verified':False,
                'ready_for_detector_metrics':False},indent=2))
            raise SystemExit(1)
        print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
