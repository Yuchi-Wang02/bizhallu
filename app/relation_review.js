(function (root) {
  'use strict';
  const clone = value => JSON.parse(JSON.stringify(value));
  const LABELS = {
    period:'时期',country:'国家',product_code:'商品代码',product_name:'商品名称',amount:'金额',percentage:'百分比',
    rank_marker:'列表序号',comparison_phrase:'比较措辞',metric_phrase:'指标措辞',business_statement:'业务陈述',
    well_formed:'格式规范',malformed:'格式不规范',unclear:'格式不明确',not_applicable:'不适用',
    entity_value:'实体与数值',ranked_entity_value:'产品、排名与数值',comparison:'比较关系',period_change:'期间变化',
    reconciliation:'金额核对',share:'占比',business_conclusion:'业务结论',
    supported:'证据支持',contradicted:'证据矛盾',unmatched:'完整范围内未匹配',needs_review:'待复核',
    exact:'精确匹配',display_rounding_match:'显示舍入匹配',within_legacy_tolerance_only:'仅在旧容差内',
    outside_legacy_tolerance:'超出旧容差',not_parseable:'无法解析',
    answer:'回答中陈述',question:'继承自题面',not_stated:'未陈述',
    primary:'主要关系',repeat:'重复陈述',contradiction:'同组矛盾陈述',draft:'草稿',complete:'已提交供复核'
  };
  const label = value => LABELS[value] || value;
  function invalidateCoverage(caseReview) {
    caseReview.status='draft';
    caseReview.coverage_checked=false;
  }
  function requireValue(ok, message) { if (!ok) throw new Error(message); }
  function keys(value, expected) {
    requireValue(value && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).sort().join('|') === [...expected].sort().join('|'), '存在不允许的字段或缺失字段');
  }
  const ATOM = ['atom_id','start','end','text','type','syntax'];
  const RELATION = ['relation_id','type','atom_ids','claim_group','count_role','period','period_origin','entity','counterparty','metric','rank_or_comparison','value','unit','row_fidelity','numeric_check','verdict','evidence_refs','search_scope_complete','reason','available_after_char'];
  function unique(rows, key) {
    requireValue(Array.isArray(rows), '记录必须为数组');
    const map = new Map();
    for (const row of rows) { requireValue(typeof row[key] === 'string' && row[key] && !map.has(row[key]), 'ID 重复或缺失'); map.set(row[key], row); }
    return map;
  }
  function blankResponse(packet) {
    return {protocol_id:packet.protocol_id,packet_id:packet.packet_id,reviewer_id:'',reviewer_type:'',legacy_labels_seen:'unknown',
      cases:packet.cases.map(c => ({case_id:c.case_id,status:'draft',prior_exposure:'unknown',coverage_checked:false,coverage_note:'',atoms:[],relations:[]}))};
  }
  function makeAtom(text, start16, end16, id) {
    requireValue(Number.isInteger(start16) && Number.isInteger(end16) && start16 >= 0 && end16 > start16 && end16 <= text.length, '请选择回答中的非空片段');
    const splitsSurrogate = pos => pos > 0 && pos < text.length && /[\uD800-\uDBFF]/.test(text[pos-1]) && /[\uDC00-\uDFFF]/.test(text[pos]);
    requireValue(!splitsSurrogate(start16) && !splitsSurrogate(end16), '字符边界不能切开 Unicode 字符');
    return {atom_id:id,start:[...text.slice(0,start16)].length,end:[...text.slice(0,end16)].length,text:text.slice(start16,end16),type:'business_statement',syntax:'unclear'};
  }
  function validateResponse(value, packet, requireComplete = false) {
    keys(value, ['protocol_id','packet_id','reviewer_id','reviewer_type','legacy_labels_seen','cases']);
    requireValue(value.protocol_id === packet.protocol_id && value.packet_id === packet.packet_id, '草稿不是这个审查包的版本');
    requireValue(typeof value.reviewer_id === 'string' && ['', 'owner_self_reported','independent_reviewer_self_reported','assistant'].includes(value.reviewer_type), '审查者信息无效');
    requireValue(['yes','no','unknown'].includes(value.legacy_labels_seen), '既往接触信息无效');
    const source = unique(packet.cases,'case_id'), cases = unique(value.cases,'case_id'), e = packet.enums;
    requireValue([...source.keys()].sort().join('|') === [...cases.keys()].sort().join('|'), '案例覆盖不完整');
    let completed = 0;
    for (const [cid,c] of cases) {
      keys(c,['case_id','status','prior_exposure','coverage_checked','coverage_note','atoms','relations']);
      requireValue(['draft','complete'].includes(c.status) && ['yes','no','unknown'].includes(c.prior_exposure), '案例状态无效');
      requireValue(typeof c.coverage_checked === 'boolean' && typeof c.coverage_note === 'string', '完整性记录无效');
      const atoms = unique(c.atoms,'atom_id'), relations = unique(c.relations,'relation_id');
      const text = [...source.get(cid).answer], occurrences = new Set(), groups = new Set();
      const evidence = new Set(source.get(cid).evidence_rows.map(r => r.row_id));
      for (const a of atoms.values()) {
        keys(a,ATOM);
        requireValue(Number.isInteger(a.start) && Number.isInteger(a.end) && a.start >= 0 && a.end > a.start && a.end <= text.length && text.slice(a.start,a.end).join('') === a.text, '字符位置或原文不匹配');
        requireValue(e.atom_types.includes(a.type) && e.syntax_statuses.includes(a.syntax), '事实类型或格式判断不允许');
        const occurrence = [a.start,a.end,a.type].join('|'); requireValue(!occurrences.has(occurrence),'同一事实片段重复'); occurrences.add(occurrence);
      }
      for (const r of relations.values()) {
        keys(r,RELATION);
        requireValue(e.relation_types.includes(r.type) && e.count_roles.includes(r.count_role) && e.verdicts.includes(r.verdict) && e.row_verdicts.includes(r.row_fidelity) && e.numeric_checks.includes(r.numeric_check) && e.period_origins.includes(r.period_origin), '关系类别或判断不允许');
        for (const k of ['claim_group','period','entity','counterparty','metric','rank_or_comparison','value','unit','reason']) requireValue(typeof r[k] === 'string', '关系字段必须为文本');
        requireValue(r.claim_group.trim() && Array.isArray(r.atom_ids) && r.atom_ids.length && new Set(r.atom_ids).size === r.atom_ids.length && r.atom_ids.every(a => atoms.has(a)), '关系须关联有效且不重复的事实片段');
        requireValue(Number.isInteger(r.available_after_char) && r.available_after_char === Math.max(...r.atom_ids.map(a => atoms.get(a).end)), '关系使用了更晚的事实，信息位置必须更新');
        requireValue(Array.isArray(r.evidence_refs) && new Set(r.evidence_refs).size === r.evidence_refs.length && r.evidence_refs.every(id => evidence.has(id)) && typeof r.search_scope_complete === 'boolean', '证据引用或范围声明无效');
        if (r.verdict === 'unmatched' || r.row_fidelity === 'unmatched') { requireValue(r.search_scope_complete && r.reason.trim(), 'unmatched 需要完整搜索范围及解释'); requireValue(r.numeric_check !== 'not_parseable','无法解析的数字不能判为 unmatched'); }
        if (['supported','contradicted'].includes(r.verdict) || ['supported','contradicted'].includes(r.row_fidelity)) requireValue(r.evidence_refs.length && r.reason.trim(), '明确判断需要证据行和理由');
        if (['supported','contradicted'].includes(r.verdict)) {
          requireValue(r.atom_ids.some(id=>atoms.get(id).type!=='rank_marker'),'单独列表序号不能承载明确业务关系判断');
          if(r.type==='ranked_entity_value') requireValue(r.entity.trim() && r.rank_or_comparison.trim(),'排名关系需要生成的实体和排名/比较');
        }
        if (r.count_role === 'primary') { requireValue(!groups.has(r.claim_group), '同一计数组不能有多个 primary'); groups.add(r.claim_group); }
      }
      for (const r of relations.values()) if (r.count_role !== 'primary') requireValue(groups.has(r.claim_group),'重复或矛盾关系需要同组 primary');
      if (c.status === 'complete') {
        requireValue(value.reviewer_id.trim() && value.reviewer_type && c.coverage_checked, '提交前需填写审查者并确认逐句完整性');
        requireValue(relations.size || c.coverage_note.trim(), '无关系时需解释原因');
        requireValue([...relations.values()].every(r => r.reason.trim()), '每个关系都需要理由，包括 needs_review');
        const linked = new Set([...relations.values()].flatMap(r => r.atom_ids)); requireValue(linked.size === atoms.size,'仍有未关联到关系的事实片段');
        completed++;
      }
    }
    if (requireComplete) requireValue(completed === source.size, '仍有未完成案例；空模板不是标签');
    return {completed_case_count:completed,ready_for_new_metrics:false};
  }
  function checkResponse(value, packet, caseId = null, requireComplete = false) {
    const result=validateResponse(value,packet,requireComplete && caseId===null);
    if(caseId!==null) {
      const c=value.cases.find(row=>row.case_id===caseId);
      requireValue(c,'本审查包没有这个案例');
      if(requireComplete)requireValue(c.status==='complete','本案例仍为草稿，尚未提交供复核');
      result.requested_case={case_id:caseId,status:c.status,atom_count:c.atoms.length,relation_count:c.relations.length,ready_for_case_adjudication:c.status==='complete'};
    }
    result.validation_scope='structure_and_self_reported_coverage_only';
    result.semantic_accuracy_verified=false;
    result.independent_human_review_verified=false;
    result.ready_for_detector_metrics=false;
    return result;
  }
  const api = {blankResponse,makeAtom,validateResponse,checkResponse,label,invalidateCoverage};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.RelationReview = api;
  if (typeof document === 'undefined') return;
  const packet = JSON.parse(document.getElementById('packet-data').textContent);
  let review = blankResponse(packet), active = 0, editing = null, dirty = false;
  const $ = id => document.getElementById(id);
  const current = () => review.cases.find(c => c.case_id === packet.cases[active].case_id);
  const notice = text => { $('notice').textContent = text; };
  function run(action) { try { action(); } catch (error) { notice(error.message); } }
  function fresh(rows,prefix,key) { let n=1; const ids=new Set(rows.map(r=>r[key])); while(ids.has(prefix+n)) n++; return prefix+n; }
  function touch(resetCoverage = true) { dirty=true; current().status='draft'; if(resetCoverage){invalidateCoverage(current());$('coverage').checked=false;} updateProgress(); }
  function element(tag,text) { const n=document.createElement(tag); if(text!==undefined)n.textContent=text; return n; }
  function options(select, values, chosen) { select.replaceChildren(); for(const v of values) { const opt=element('option',label(v)); opt.value=v; opt.title=v; select.append(opt); } select.value=chosen; }
  function updateProgress() { $('progress').textContent=`${review.cases.filter(c=>c.status==='complete').length} / ${packet.cases.length} 已提交供复核`; $('case-status').textContent=`${label(current().status)} · ${current().atoms.length} 个片段 · ${current().relations.length} 个关系`; }
  function renderAtoms() {
    $('atoms').replaceChildren();
    for (const a of current().atoms) {
      const tr=element('tr'); tr.append(element('td',`${a.atom_id} [${a.start}, ${a.end})`),element('td',a.text));
      for(const [key,values] of [['type',packet.enums.atom_types],['syntax',packet.enums.syntax_statuses]]) {
        const td=element('td'),select=element('select'); select.setAttribute('aria-label',`${a.atom_id} ${key}`); options(select,values,a[key]); select.onchange=()=>{a[key]=select.value;touch();}; td.append(select); tr.append(td);
      }
      const td=element('td'),button=element('button','删除'); button.onclick=()=>run(()=>{requireValue(!current().relations.some(r=>r.atom_ids.includes(a.atom_id)),'该事实被关系引用，请先修改或删除相关关系');current().atoms=current().atoms.filter(x=>x!==a);touch();renderAtoms();});td.append(button);tr.append(td);$('atoms').append(tr);
    }
  }
  function renderRelations() {
    const body=$('relations').querySelector('tbody');body.replaceChildren();
    for (const r of current().relations) {
      const tr=element('tr');tr.append(element('td',`${r.relation_id} · ${r.claim_group} · ${label(r.count_role)}`),element('td',[r.period,r.entity,r.counterparty,r.metric,r.rank_or_comparison,r.value,r.unit].filter(Boolean).join(' · ')),element('td',`${label(r.row_fidelity)} / ${label(r.verdict)}`),element('td',r.reason));
      const td=element('td'),edit=element('button','编辑'),remove=element('button','删除');edit.onclick=()=>editRelation(r);remove.onclick=()=>run(()=>{const next=clone(review),c=next.cases.find(x=>x.case_id===current().case_id);c.status='draft';c.relations=c.relations.filter(x=>x.relation_id!==r.relation_id);validateResponse(next,packet);review=next;touch();renderRelations();});td.append(edit,remove);tr.append(td);body.append(tr);
    }
  }
  function renderCase() {
    const c=packet.cases[active];$('case-select').value=c.case_id;$('question').textContent=c.question;$('answer').value=c.answer;
    $('scope').textContent=c.evidence_scope_note;$('messages').textContent=c.messages.map(m=>`${m.role}\n${m.content}`).join('\n\n');
    const table=$('evidence');table.replaceChildren();const columns=[...new Set(c.evidence_rows.flatMap(r=>Object.keys(r.values)))];const head=element('thead'),hr=element('tr');['证据行',...columns].forEach(k=>hr.append(element('th',k)));head.append(hr);table.append(head);const body=element('tbody');
    for(const r of c.evidence_rows){const tr=element('tr');[r.row_id,...columns.map(k=>r.values[k]??'')].forEach(v=>tr.append(element('td',String(v))));body.append(tr);}table.append(body);
    $('prior-exposure').value=current().prior_exposure;$('coverage').checked=current().coverage_checked;$('coverage-note').value=current().coverage_note;
    $('relation-editor').hidden=true;editing=null;renderAtoms();renderRelations();updateProgress();
  }
  const fieldSpecs=[['type','关系类别','relation_types'],['claim_group','计数组',null],['count_role','计数角色','count_roles'],['period','时期',null],['period_origin','时期来源','period_origins'],['entity','实体 / 产品',null],['counterparty','比较对象',null],['metric','业务指标',null],['rank_or_comparison','排名 / 比较方向',null],['value','数值原文（未陈述则留空）',null],['unit','单位',null],['row_fidelity','对应数据行忠实度','row_verdicts'],['numeric_check','数值与容差','numeric_checks'],['verdict','完整关系判断','verdicts'],['evidence_refs','证据行 ID（逗号分隔）',null],['search_scope_complete','已确认搜索范围完整','boolean']];
  function editRelation(existing) {
    if(!$('relation-editor').hidden&&!root.confirm('放弃尚未保存的关系编辑？'))return;
    editing=existing?existing.relation_id:null;
    const r=existing||{relation_id:fresh(current().relations,'r','relation_id'),type:'entity_value',claim_group:fresh(current().relations,'g','claim_group'),count_role:'primary',period:'',period_origin:'not_stated',entity:'',counterparty:'',metric:'',rank_or_comparison:'',value:'',unit:'',row_fidelity:'needs_review',numeric_check:'needs_review',verdict:'needs_review',evidence_refs:[],search_scope_complete:false,atom_ids:[],reason:''};
    $('editor-title').textContent=r.relation_id;$('relation-fields').replaceChildren();
    for(const [key,label,kind] of fieldSpecs){const wrapper=element('label');wrapper.append(element('span',label));const input=element(kind&&kind!=='boolean'?'select':'input');input.id='field-'+key;
      if(kind==='boolean'){input.type='checkbox';input.checked=r[key];}else if(kind){options(input,packet.enums[kind],r[key]);}else{input.value=Array.isArray(r[key])?r[key].join(', '):r[key];}wrapper.append(input);$('relation-fields').append(wrapper);}
    $('atom-links').replaceChildren();for(const a of current().atoms){const label=element('label'),box=element('input');box.type='checkbox';box.value=a.atom_id;box.checked=r.atom_ids.includes(a.atom_id);label.append(box,document.createTextNode(`${a.atom_id}: ${a.text}`));$('atom-links').append(label);}
    $('reason').value=r.reason;$('relation-editor').hidden=false;
  }
  $('save-relation').onclick=()=>run(()=>{
    const c=current(),ids=[...$('atom-links').querySelectorAll('input:checked')].map(n=>n.value);
    requireValue(ids.length,'至少关联一个事实片段');
    const r={relation_id:editing||$('editor-title').textContent,atom_ids:ids,reason:$('reason').value,available_after_char:Math.max(...c.atoms.filter(a=>ids.includes(a.atom_id)).map(a=>a.end))};
    for(const [key,,kind] of fieldSpecs){const input=$('field-'+key);r[key]=kind==='boolean'?input.checked:key==='evidence_refs'?input.value.split(',').map(x=>x.trim()).filter(Boolean):input.value;}
    const next=clone(review),target=next.cases.find(x=>x.case_id===c.case_id);target.status='draft';target.relations=target.relations.filter(x=>x.relation_id!==r.relation_id);target.relations.push(r);validateResponse(next,packet);review=next;touch();$('relation-editor').hidden=true;editing=null;renderRelations();notice('关系已加入草稿，尚未形成评价标签。');
  });
  $('cancel-relation').onclick=()=>{$('relation-editor').hidden=true;editing=null;};
  $('add-relation').onclick=()=>run(()=>{requireValue(current().atoms.length,'当前没有事实片段');editRelation(null);});
  $('add-atom').onclick=()=>run(()=>{const t=$('answer'),a=makeAtom(t.value,t.selectionStart,t.selectionEnd,fresh(current().atoms,'a','atom_id'));requireValue(!current().atoms.some(x=>x.start===a.start&&x.end===a.end&&x.type===a.type),'该片段已存在');current().atoms.push(a);touch();renderAtoms();notice(`${a.atom_id}: [${a.start}, ${a.end})`);});
  $('reviewer-id').oninput=e=>{review.reviewer_id=e.target.value;dirty=true;};$('reviewer-type').onchange=e=>{review.reviewer_type=e.target.value;dirty=true;};$('legacy-seen').onchange=e=>{review.legacy_labels_seen=e.target.value;dirty=true;};
  $('prior-exposure').onchange=e=>{current().prior_exposure=e.target.value;touch(false);};$('coverage').onchange=e=>{current().coverage_checked=e.target.checked;touch(false);};$('coverage-note').oninput=e=>{current().coverage_note=e.target.value;touch();};
  $('check-case').onclick=()=>run(()=>{requireValue($('relation-editor').hidden,'请先保存或取消正在编辑的关系');const c=checkResponse(review,packet,current().case_id).requested_case;notice(`${c.case_id} 结构校验通过：${c.atom_count} 个片段，${c.relation_count} 个关系；${label(c.status)}。事实判断未被自动验证。`);});
  $('complete-case').onclick=()=>run(()=>{requireValue($('relation-editor').hidden,'请先保存或取消正在编辑的关系');const next=clone(review);next.cases.find(x=>x.case_id===current().case_id).status='complete';checkResponse(next,packet,current().case_id,true);review=next;dirty=true;updateProgress();notice('本案例已标记供复核；其余案例不自动完成，判断正确性仍待复核。');});
  $('reopen-case').onclick=()=>{touch();notice('已恢复草稿状态。');};
  for(const c of packet.cases){const o=element('option',c.case_id);o.value=c.case_id;$('case-select').append(o);}
  $('case-select').onchange=e=>{if(!$('relation-editor').hidden&&!root.confirm('当前关系尚在编辑。放弃未保存的关系编辑？')){e.target.value=current().case_id;return;}active=packet.cases.findIndex(c=>c.case_id===e.target.value);renderCase();notice('');};
  for(const text of packet.rules)$('rules').append(element('li',text));
  $('export-button').onclick=()=>run(()=>{requireValue($('relation-editor').hidden,'请先保存或取消正在编辑的关系');validateResponse(review,packet);const blob=new Blob([JSON.stringify(review,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=element('a');a.href=url;a.download='bizhallu-relation-review-'+packet.packet_id.slice(0,8)+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);notice('已请求下载草稿；保存尚未核实，离页保护仍然有效。没有自动写入项目或指标。');});
  $('import-button').onclick=()=>$('import-file').click();$('import-file').onchange=async e=>{const file=e.target.files[0];if(!file)return;try{requireValue(file.size<2000000,'草稿文件过大');const imported=JSON.parse(await file.text());validateResponse(imported,packet);if((dirty||!$('relation-editor').hidden)&&!root.confirm('替换当前未导出的草稿或关系编辑？'))return;review=imported;$('reviewer-id').value=review.reviewer_id;$('reviewer-type').value=review.reviewer_type;$('legacy-seen').value=review.legacy_labels_seen;dirty=false;renderCase();notice('草稿结构校验通过；事实判断仍待复核。');}catch(error){notice(error.message);}finally{e.target.value='';}};
  root.addEventListener('beforeunload',e=>{if(dirty||!$('relation-editor').hidden){e.preventDefault();e.returnValue='';}});
  renderCase();
})(typeof window!=='undefined'?window:globalThis);
