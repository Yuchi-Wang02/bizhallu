const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const api=require('../app/relation_review.js');
const config=JSON.parse(fs.readFileSync(path.join(__dirname,'../configs/relation_annotation_v2.json'),'utf8'));
const packet={protocol_id:config.protocol_id,packet_id:'synthetic-test-only',enums:config,cases:[{case_id:'B01',answer:'1. Widget A: 12.00. 📊',evidence_rows:[{row_id:'E001',values:{description:'Widget A',net_revenue:12}}]}]};
function fixture(){const r=api.blankResponse(packet);r.reviewer_id='synthetic-only';r.reviewer_type='assistant';const c=r.cases[0];c.atoms=[{atom_id:'a1',start:3,end:11,text:'Widget A',type:'product_name',syntax:'well_formed'}];c.relations=[{relation_id:'r1',type:'entity_value',atom_ids:['a1'],claim_group:'g1',count_role:'primary',period:'',period_origin:'not_stated',entity:'Widget A',counterparty:'',metric:'net_revenue',rank_or_comparison:'',value:'12.00',unit:'GBP',row_fidelity:'supported',numeric_check:'exact',verdict:'supported',evidence_refs:['E001'],search_scope_complete:false,reason:'Synthetic fixture only.',available_after_char:11}];return r;}
test('blank template cannot be submitted as completed labels',()=>{const r=api.blankResponse(packet);assert.equal(api.validateResponse(r,packet).completed_case_count,0);assert.throws(()=>api.validateResponse(r,packet,true));});
test('UTF-16 selection converts to codepoint offsets including repeated strings',()=>{const text='📊 A A';assert.deepEqual(api.makeAtom(text,5,6,'a1'),{atom_id:'a1',start:4,end:5,text:'A',type:'business_statement',syntax:'unclear'});assert.throws(()=>api.makeAtom(text,1,2,'a1'));});
test('combining characters retain codepoint boundaries',()=>{assert.equal(api.makeAtom('e\u0301 GBP',0,2,'a1').end,2);});
test('partial draft roundtrip preserves exact schema and text',()=>{const r=fixture();assert.deepEqual(JSON.parse(JSON.stringify(r)),r);assert.equal(api.validateResponse(r,packet).ready_for_new_metrics,false);});
test('wrong packet and hidden scores rejected',()=>{const r=fixture();r.packet_id='other';assert.throws(()=>api.validateResponse(r,packet));r.packet_id=packet.packet_id;r.detector_score=1;assert.throws(()=>api.validateResponse(r,packet));});
test('broken offsets and false information timing rejected',()=>{let r=fixture();r.cases[0].atoms[0].end=12;assert.throws(()=>api.validateResponse(r,packet));r=fixture();r.cases[0].relations[0].available_after_char=2;assert.throws(()=>api.validateResponse(r,packet));});
test('row fidelity and relation contradiction are separate',()=>{const r=fixture();r.cases[0].relations[0].verdict='contradicted';api.validateResponse(r,packet);});
test('decisive list marker alone is rejected',()=>{const r=fixture(),c=r.cases[0];c.atoms[0]={atom_id:'a1',start:0,end:2,text:'1.',type:'rank_marker',syntax:'well_formed'};c.relations[0].available_after_char=2;assert.throws(()=>api.validateResponse(r,packet));});
test('unmatched is not a parse-failure category',()=>{const r=fixture(),rel=r.cases[0].relations[0];rel.verdict='unmatched';assert.throws(()=>api.validateResponse(r,packet));rel.search_scope_complete=true;api.validateResponse(r,packet);rel.numeric_check='not_parseable';assert.throws(()=>api.validateResponse(r,packet));});
test('completion requires coverage and rejects orphan atoms',()=>{const r=fixture(),c=r.cases[0];c.status='complete';assert.throws(()=>api.validateResponse(r,packet));c.coverage_checked=true;api.validateResponse(r,packet,true);c.atoms.push({atom_id:'a2',start:0,end:2,text:'1.',type:'rank_marker',syntax:'well_formed'});assert.throws(()=>api.validateResponse(r,packet));});
test('duplicate primary group rejected, repeat accepted',()=>{const r=fixture(),c=r.cases[0];c.relations.push({...c.relations[0],relation_id:'r2'});assert.throws(()=>api.validateResponse(r,packet));c.relations[1].count_role='repeat';api.validateResponse(r,packet);});

test('every protocol value has a reader-facing label without changing schema',()=>{
  for(const key of ['atom_types','syntax_statuses','relation_types','verdicts','row_verdicts','numeric_checks','period_origins','count_roles']) {
    const labels=config[key].map(api.label);
    assert.equal(new Set(labels).size,labels.length);
    for(const value of config[key])assert.notEqual(api.label(value),value);
  }
  const r=fixture(),original=JSON.stringify(r);api.label(r.cases[0].relations[0].verdict);
  assert.equal(JSON.stringify(r),original);
});

test('single-case checkpoint keeps the other case incomplete',()=>{
  const p={...packet,cases:[packet.cases[0],{...packet.cases[0],case_id:'B02'}]},r=api.blankResponse(p);
  r.reviewer_id='synthetic-only';r.reviewer_type='assistant';r.cases[0]=fixture().cases[0];
  r.cases[0].status='complete';r.cases[0].coverage_checked=true;
  const before=JSON.stringify(r),result=api.checkResponse(r,p,'B01',true);
  assert.equal(result.completed_case_count,1);assert.equal(result.requested_case.ready_for_case_adjudication,true);
  assert.equal(result.semantic_accuracy_verified,false);assert.equal(result.ready_for_new_metrics,false);
  assert.equal(JSON.stringify(r),before);
  assert.throws(()=>api.checkResponse(r,p,null,true));assert.throws(()=>api.checkResponse(r,p,'B02',true));
  assert.throws(()=>api.checkResponse(r,p,'B99'));
  r.cases[1].old_label='hidden';assert.throws(()=>api.checkResponse(r,p,'B01',true));
});

test('single-case blank passes draft structure only',()=>{
  const r=api.blankResponse(packet),result=api.checkResponse(r,packet,'B01');
  assert.equal(result.requested_case.ready_for_case_adjudication,false);
  assert.throws(()=>api.checkResponse(r,packet,'B01',true));
});

test('annotation edits invalidate prior full-answer coverage',()=>{
  const r=fixture(),c=r.cases[0];c.status='complete';c.coverage_checked=true;
  const atoms=JSON.stringify(c.atoms),relations=JSON.stringify(c.relations);
  api.invalidateCoverage(c);assert.equal(c.status,'draft');assert.equal(c.coverage_checked,false);
  assert.equal(JSON.stringify(c.atoms),atoms);assert.equal(JSON.stringify(c.relations),relations);
  c.status='complete';assert.throws(()=>api.validateResponse(r,packet,true));
});
