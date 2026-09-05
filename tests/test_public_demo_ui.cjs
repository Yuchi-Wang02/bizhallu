// Execute the generated page script. This is a logic test, not browser/visual QA.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const html = fs.readFileSync(path.join(__dirname, '../docs/portfolio_demo_v2.html'), 'utf8');
const scripts = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)]
  .map(match => match[1]).filter(script => script.includes('const DEMO_DATA ='));
assert.equal(scripts.length, 1);

function harness(query = '') {
  const elements = new Map();
  function getElementById(id) {
    if (!elements.has(id)) elements.set(id, {
      innerHTML: '', textContent: '', value: id === 'detectorFilter' ? 'simple' : 'all',
      handlers: {}, addEventListener(name, fn) { this.handlers[name] = fn; }
    });
    return elements.get(id);
  }
  const location = new URL('https://example.test/bizhallu/portfolio_demo_v2.html' + query);
  const history = { last: null, replaceState(_state, _title, url) { this.last = String(url); } };
  const ctx = vm.createContext({document: {getElementById}, window: {location, history}, URL, URLSearchParams});
  vm.runInContext(scripts[0], ctx, {timeout: 2000});
  return {ctx, el: getElementById, history,
    run(code) { return vm.runInContext(code, ctx); },
    change(id, value) { const el = getElementById(id); el.value = value; el.handlers.change({target: el}); }};
}

test('primary case renders complete relations and original evidence', () => {
  const h = harness('?case=q_0064');
  assert.match(h.el('casePanel').innerHTML, /April 2011/);
  assert.match(h.el('relationshipPanel').innerHTML, /4,173\.18/);
  assert.match(h.el('relationshipPanel').innerHTML, /<td>3<\/td><td>7<\/td>/);
  assert.match(h.el('relationshipPanel').innerHTML, /PAPER CHAIN KIT EMPIRE/);
  assert.match(h.el('evidencePanel').innerHTML, /Original evidence order/);
  assert.equal((h.el('casePanel').innerHTML.match(/<mark /g) || []).length, 3);
});

test('answer precedes interpretive context in the reading order for every case', () => {
  const h = harness();
  for (const id of h.run('DEMO_DATA.cases.map(c=>c.question_id)')) {
    h.change('caseSelect', id);
    const panel = h.el('casePanel').innerHTML;
    const answer = panel.indexOf('<div class="answer-output">');
    const context = panel.indexOf('<div class="answer-context">');
    assert.ok(answer >= 0 && context > answer);
    assert.equal((panel.match(/<pre>/g) || []).length, 1);
    assert.doesNotMatch(panel, /product-amount pair below/);
  }
});

test('case selection updates the question, comparison and URL', () => {
  const h = harness('?case=q_0064');
  h.change('caseSelect', 'q_0069');
  assert.match(h.el('casePanel').innerHTML, /September 2011/);
  assert.match(h.el('relationshipPanel').innerHTML, /<td>2<\/td><td>8<\/td>/);
  assert.match(h.history.last, /case=q_0069/);
});

test('unknown deep link falls back to an existing case', () => {
  const h = harness('?case=missing');
  assert.equal(h.run('currentCaseId'), h.run('DEMO_DATA.cases[0].question_id'));
  assert.notEqual(h.el('casePanel').innerHTML, '');
});

test('filter empty state does not hide or rewrite the relationship walkthrough', () => {
  const h = harness('?case=q_0064');
  const audit = h.el('relationshipPanel').innerHTML;
  h.change('factTypeFilter', 'percentage');
  assert.match(h.el('spanPanel').innerHTML, /No spans match these filters/);
  assert.equal(h.el('relationshipPanel').innerHTML, audit);
  h.change('factTypeFilter', 'all');
  assert.doesNotMatch(h.el('spanPanel').innerHTML, /No spans match these filters/);
});

test('all three detector filters use their own outcomes without modifying evidence', () => {
  const h = harness('?case=q_0064');
  const original = h.el('evidencePanel').innerHTML;
  for (const detector of ['simple', 'entropy', 'energy']) {
    h.change('detectorFilter', detector);
    h.change('outcomeFilter', 'missed');
    assert.equal(h.run(`filteredSpans(DEMO_DATA.cases.find(c=>c.question_id==='q_0064')).every(s=>s['${detector}_outcome']==='missed')`), true);
    assert.equal(h.el('evidencePanel').innerHTML, original);
  }
  assert.match(h.el('detectorHelp').textContent, /not an independent energy method/);
});

test('label filtering is scoped to preserved atomic judgments', () => {
  const h = harness('?case=q_0064');
  h.change('labelFilter', 'correct_key_fact');
  assert.equal(h.run("filteredSpans(DEMO_DATA.cases.find(c=>c.question_id==='q_0064')).every(s=>s.label==='correct_key_fact')"), true);
  assert.match(h.el('relationshipPanel').innerHTML, /Incorrect binding/);
});

test('remaining historical cases receive no invented relationship audit', () => {
  const h = harness();
  const ids = h.run('DEMO_DATA.cases.filter(c=>!c.presentation_walkthrough).map(c=>c.question_id)');
  assert.equal(ids.length, 7);
  for (const id of ids) {
    h.change('caseSelect', id);
    assert.match(h.el('relationshipPanel').innerHTML, /No new relationship audit/);
    assert.doesNotMatch(h.el('casePanel').innerHTML, /<mark /);
  }
});

test('Unicode codepoint highlighting and untrusted text remain safe', () => {
  const h = harness();
  const output = h.run("highlightAnswer('\\u{1f4c8}A<B', [{span_start_char:1,span_end_char:2,label:'correct_key_fact',fact_type:'<script>'}])");
  assert.match(output, /^\u{1f4c8}<mark/u);
  assert.match(output, />A<\/mark>&lt;B$/);
  assert.doesNotMatch(output, /<script>/);
  assert.equal(h.run("escapeHtml('<img onerror=\"x\">')"), '&lt;img onerror=&quot;x&quot;&gt;');
});
