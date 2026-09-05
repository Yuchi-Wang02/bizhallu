import copy
import contextlib
import io
import json
import sys
import unittest
import shutil
import subprocess
import tempfile
from unittest.mock import patch
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import relation_review as rr


def fixture():
    config=rr.load(rr.CONFIG)
    text='1. Widget A: GBP 12.00. \U0001f4ca 2. Widget B: GBP 8.00.'
    prompt={'messages':[{'role':'system','content':'Use this table.'},{'role':'user','content':'Evidence: Widget A 12; Widget B 8.'}],
            'source_question_record':{'question':'Rank the products.'},
            'prompt_evidence_rows':[{'description':'Widget A','net_revenue':12.0},{'description':'Widget B','net_revenue':8.0}]}
    gen={'generated_text':text,'prompt':'Use this table. Evidence: Widget A 12; Widget B 8.'}
    return config,gen,prompt


def completed_fixture():
    config,gen,prompt=fixture()
    packet=rr.packet_for([rr.project_case(gen,prompt,'B01')],config)
    response=rr.blank_response(packet)
    response.update(reviewer_id='synthetic_test_only',reviewer_type='assistant')
    case=response['cases'][0]
    case.update(status='complete',coverage_checked=True,coverage_note='Synthetic protocol fixture, not natural benchmark labels.')
    case['atoms']=[{'atom_id':'a1','start':3,'end':11,'text':'Widget A','type':'product_name','syntax':'well_formed'}]
    case['relations']=[{'relation_id':'r1','type':'entity_value','atom_ids':['a1'],'claim_group':'g1','count_role':'primary',
        'period':'','period_origin':'not_stated','entity':'Widget A','counterparty':'','metric':'net_revenue','rank_or_comparison':'',
        'value':'12.00','unit':'GBP','row_fidelity':'supported','numeric_check':'exact','verdict':'supported',
        'evidence_refs':['E001'],'search_scope_complete':False,'reason':'Synthetic evidence fixture supports the entity.', 'available_after_char':11}]
    return packet,response


class RelationReviewTests(unittest.TestCase):
    def test_projection_ignores_labels_gold_scores_and_ids(self):
        config,gen,prompt=fixture()
        expected=rr.project_case(gen,prompt,'B01')
        for value in [None,{'secret':'DO_NOT_DISCLOSE'},[1,2,3]]:
            changed_g={**gen,'gold_answer':value,'annotations':value,'detector_scores':value,'question_id':'secret-id','split':'test'}
            changed_p={**prompt,'gold_answer':value,'gold_facts':value,'old_labels':value,'detector_outcome':value}
            self.assertEqual(expected,rr.project_case(changed_g,changed_p,'B01'))
        serialized=json.dumps(expected)
        self.assertNotIn('DO_NOT_DISCLOSE',serialized)
        self.assertEqual(set(expected),rr.CASE_KEYS)

    def test_evidence_metadata_leakage_rejected(self):
        _,gen,prompt=fixture()
        prompt['prompt_evidence_rows'][0]['detector_score']=.9
        with self.assertRaises(ValueError):rr.project_case(gen,prompt,'B01')

    def test_blank_is_not_completed_or_scoring_ready(self):
        packet,_=completed_fixture()
        blank=rr.blank_response(packet)
        result=rr.validate_response(blank,packet)
        self.assertEqual(result['completed_case_count'],0)
        self.assertFalse(result['ready_for_detector_metrics'])
        with self.assertRaises(ValueError):rr.validate_response(blank,packet,True)

    def test_completed_fixture_is_not_independent_human_evidence(self):
        packet,response=completed_fixture()
        result=rr.validate_response(response,packet,True)
        self.assertTrue(result['ready_for_adjudication'])
        self.assertFalse(result['independent_human_review_verified'])
        self.assertFalse(result['ready_for_detector_metrics'])

    def test_single_case_submission_does_not_complete_remaining_cases(self):
        packet,response=completed_fixture()
        first=copy.deepcopy(response['cases'][0])
        config=rr.load(rr.CONFIG)
        packet=rr.packet_for([packet['cases'][0],{**packet['cases'][0],'case_id':'B02'}],config)
        response=rr.blank_response(packet)
        response.update(reviewer_id='synthetic-only',reviewer_type='assistant')
        response['cases'][0]=first
        before=copy.deepcopy(response)
        result=rr.check_response(response,packet,'B01',True)
        self.assertEqual(result['completed_case_count'],1)
        self.assertTrue(result['requested_case']['ready_for_case_adjudication'])
        self.assertFalse(result['ready_for_adjudication'])
        self.assertFalse(result['semantic_accuracy_verified'])
        self.assertFalse(result['independent_human_review_verified'])
        self.assertFalse(result['ready_for_detector_metrics'])
        self.assertEqual(response,before)
        with self.assertRaises(ValueError):rr.check_response(response,packet,None,True)
        with self.assertRaises(ValueError):rr.check_response(response,packet,'B02',True)
        with self.assertRaises(ValueError):rr.check_response(response,packet,'B99')
        # Selecting one case must not bypass validation of the imported file.
        response['cases'][1]['detector_score']=.5
        with self.assertRaises(ValueError):rr.check_response(response,packet,'B01',True)

    def test_single_case_blank_is_only_a_draft(self):
        packet,_=completed_fixture()
        response=rr.blank_response(packet)
        result=rr.check_response(response,packet,'B01')
        self.assertEqual(result['requested_case']['status'],'draft')
        self.assertFalse(result['requested_case']['ready_for_case_adjudication'])
        with self.assertRaises(ValueError):rr.check_response(response,packet,'B01',True)

    def test_cli_rejects_ignored_case_option(self):
        proc=subprocess.run([sys.executable,str(rr.ROOT/'src/relation_review.py'),'validate','--case-id','B01'],
                            capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(proc.returncode,2)
        self.assertIn('only for check-response',proc.stderr)

    def test_cli_blank_failure_is_structured_and_read_only(self):
        packet,_=completed_fixture()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            packet_path=root/'packet.json';response_path=root/'response.json'
            rr.write_json(packet_path,packet);rr.write_json(response_path,rr.blank_response(packet))
            before={p.name:p.read_bytes() for p in root.iterdir()}
            stdout=io.StringIO()
            with patch.object(rr,'PACKET_DIR',root),patch.object(sys,'argv',[
                'relation_review.py','check-response','--responses',str(response_path),
                '--case-id','B01','--require-complete']),contextlib.redirect_stdout(stdout):
                with self.assertRaises(SystemExit) as failure:rr.main()
            self.assertEqual(failure.exception.code,1)
            result=json.loads(stdout.getvalue())
            self.assertEqual(result['status'],'response_validation_failed')
            self.assertEqual(result['num_failures'],1)
            self.assertFalse(result['ready_for_detector_metrics'])
            self.assertEqual(before,{p.name:p.read_bytes() for p in root.iterdir()})

    def test_wrong_packet_or_hidden_fields_rejected(self):
        packet,response=completed_fixture()
        for key,value in [('packet_id','wrong'),('old_label','correct')]:
            changed={**response,key:value}
            with self.assertRaises(ValueError):rr.validate_response(changed,packet)

    def test_unicode_offsets_and_repeated_occurrences(self):
        config,gen,prompt=fixture();gen['generated_text']='\U0001f4ca A A e\u0301'
        packet=rr.packet_for([rr.project_case(gen,prompt,'B01')],config)
        response=rr.blank_response(packet);case=response['cases'][0]
        case['atoms']=[{'atom_id':'a1','start':2,'end':3,'text':'A','type':'product_name','syntax':'well_formed'},
                       {'atom_id':'a2','start':4,'end':5,'text':'A','type':'product_name','syntax':'well_formed'}]
        rr.validate_response(response,packet)
        case['atoms'][0]['start']=3
        with self.assertRaises(ValueError):rr.validate_response(response,packet)

    def test_duplicate_ids_unknown_types_and_bool_offsets_rejected(self):
        packet,response=completed_fixture()
        for mutate in [lambda c:c['atoms'].append(copy.deepcopy(c['atoms'][0])),
                       lambda c:c['atoms'][0].update(type='malformed_number'),
                       lambda c:c['atoms'][0].update(start=True)]:
            value=copy.deepcopy(response);mutate(value['cases'][0])
            with self.assertRaises(ValueError):rr.validate_response(value,packet)

    def test_wrong_information_endpoint_rejected(self):
        packet,response=completed_fixture()
        response['cases'][0]['relations'][0]['available_after_char']=2
        with self.assertRaises(ValueError):rr.validate_response(response,packet)

    def test_standalone_rank_marker_cannot_receive_relation_verdict(self):
        packet,response=completed_fixture();case=response['cases'][0]
        case['atoms'][0].update(start=0,end=2,text='1.',type='rank_marker')
        case['relations'][0].update(available_after_char=2,type='ranked_entity_value',rank_or_comparison='1')
        with self.assertRaises(ValueError):rr.validate_response(response,packet)

    def test_unmatched_requires_complete_scope_and_parseable_claim(self):
        packet,response=completed_fixture();rel=response['cases'][0]['relations'][0]
        rel['verdict']='unmatched'
        with self.assertRaises(ValueError):rr.validate_response(response,packet)
        rel['search_scope_complete']=True;rr.validate_response(response,packet)
        rel['numeric_check']='not_parseable'
        with self.assertRaises(ValueError):rr.validate_response(response,packet)

    def test_bad_or_missing_evidence_references_rejected(self):
        packet,response=completed_fixture()
        for refs in [[],['E999'],['E001','E001']]:
            response['cases'][0]['relations'][0]['evidence_refs']=refs
            with self.assertRaises(ValueError):rr.validate_response(response,packet)

    def test_same_row_fidelity_can_coexist_with_wrong_binding(self):
        packet,response=completed_fixture();rel=response['cases'][0]['relations'][0]
        rel['verdict']='contradicted'
        rr.validate_response(response,packet)
        self.assertEqual(rel['row_fidelity'],'supported')

    def test_repeat_requires_one_primary_and_linked_atoms(self):
        packet,response=completed_fixture();case=response['cases'][0]
        case['relations'].append({**case['relations'][0],'relation_id':'r2'})
        with self.assertRaises(ValueError):rr.validate_response(response,packet)
        case['relations'][1]['count_role']='repeat';rr.validate_response(response,packet)
        case['relations'][0]['count_role']='repeat'
        with self.assertRaises(ValueError):rr.validate_response(response,packet)

    def test_complete_requires_coverage_and_reviewer(self):
        packet,response=completed_fixture()
        response['cases'][0]['coverage_checked']=False
        with self.assertRaises(ValueError):rr.validate_response(response,packet)
        response['cases'][0]['coverage_checked']=True;response['reviewer_id']=''
        with self.assertRaises(ValueError):rr.validate_response(response,packet)

    def test_html_embedding_does_not_execute_answer_markup(self):
        config,gen,prompt=fixture();gen['generated_text']='__REVIEW_JS__ __PACKET_JSON__ </script><script>alert(1)</script>'
        packet=rr.packet_for([rr.project_case(gen,prompt,'B01')],config)
        text=rr.render(packet)
        embedded=text.split('<script id="packet-data" type="application/json">',1)[1].split('</script>',1)[0]
        self.assertNotIn('<script',embedded)
        self.assertEqual(json.loads(embedded),packet)
        self.assertNotIn('innerHTML',rr.SCRIPT.read_text(encoding='utf-8'))

    def test_template_has_unique_ids_and_no_remote_assets(self):
        class Elements(HTMLParser):
            def __init__(self):super().__init__();self.ids=[];self.remote=[]
            def handle_starttag(self,tag,attrs):
                attrs=dict(attrs)
                if 'id' in attrs:self.ids.append(attrs['id'])
                if 'src' in attrs or (tag=='link' and 'href' in attrs):self.remote.append(attrs)
        parser=Elements();parser.feed(rr.TEMPLATE.read_text(encoding='utf-8'))
        self.assertEqual(len(parser.ids),len(set(parser.ids)))
        self.assertFalse(parser.remote)
        import re
        referenced=set(re.findall(r"\$\('([^']+)'\)",rr.SCRIPT.read_text(encoding='utf-8')))
        self.assertTrue(referenced<=set(parser.ids), referenced-set(parser.ids))

    def test_packet_commitment_detects_changed_answer(self):
        packet,_=completed_fixture();packet['cases'][0]['answer']+='changed'
        with self.assertRaises(ValueError):rr.validate_packet(packet)

    def test_failed_validation_replaces_prior_green_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            out=root/'reports/bizhallu_relation_calibration_v2_validation.json'
            rr.write_json(out,{'status':'prior_green','num_failures':0})
            with patch.object(rr,'ROOT',root),patch.object(rr,'validate_bundle',side_effect=ValueError('synthetic source mismatch')):
                result=rr.validate_and_record()
            self.assertEqual(result['num_failures'],1)
            self.assertEqual(rr.load(out)['status'],'relation_calibration_validation_failed')

    def test_browser_python_contract_parity(self):
        node=shutil.which('node')
        if not node:self.skipTest('Node unavailable; JavaScript CI runs separately')
        packet,response=completed_fixture()
        variants=[response,rr.blank_response(packet)]
        for mutate in [lambda r:r.update(packet_id='wrong'),
                       lambda r:r['cases'][0]['relations'][0].update(available_after_char=1),
                       lambda r:r['cases'][0]['relations'][0].update(verdict='unmatched'),
                       lambda r:r['cases'][0]['relations'][0].update(verdict='contradicted'),
                       lambda r:r['cases'][0]['atoms'][0].update(type='malformed_number'),
                       lambda r:r['cases'][0].update(coverage_checked=False)]:
            item=copy.deepcopy(response);mutate(item);variants.append(item)
        expected=[]
        for item in variants:
            try:rr.validate_response(item,packet);expected.append(True)
            except ValueError:expected.append(False)
        script="const fs=require('fs'),a=require('./app/relation_review.js'),p=JSON.parse(fs.readFileSync(0,'utf8'));console.log(JSON.stringify(p.variants.map(r=>{try{a.validateResponse(r,p.packet);return true;}catch(e){return false;}})));"
        proc=subprocess.run([node,'-e',script],cwd=rr.ROOT,input=json.dumps({'packet':packet,'variants':variants}),capture_output=True,text=True,encoding='utf-8',check=True)
        self.assertEqual(json.loads(proc.stdout),expected)


if __name__=='__main__':unittest.main()
