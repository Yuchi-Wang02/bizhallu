"""Check committed PPTX text, notes, editable evidence and chart values without Office."""
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile
import xml.etree.ElementTree as ET

from presentation_story import build_story

ROOT = Path(__file__).resolve().parents[1]
PPTX = ROOT / 'reports/bizhallu_interview_v2.pptx'
NS = {'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
      'p':'http://schemas.openxmlformats.org/presentationml/2006/main',
      'c':'http://schemas.openxmlformats.org/drawingml/2006/chart'}


def texts(node):
    return [t.text or '' for t in node.findall('.//a:t', NS)]


def validate_package(payload, story):
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        slide_names = [f'ppt/slides/slide{i}.xml' for i in range(1,11)]
        actual = [n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)]
        if set(actual) != set(slide_names):
            raise ValueError('Expected ten slides')
        for index,(name,item) in enumerate(zip(slide_names,story['slides']),1):
            parts = texts(ET.fromstring(z.read(name)))
            if item['title'] not in parts:
                raise ValueError('Slide title differs from the speaking outline')
            notes = '\n'.join(texts(ET.fromstring(z.read(f'ppt/notesSlides/notesSlide{index}.xml'))))
            if item['script'] not in notes:
                raise ValueError('Speaker notes differ from the shared English script')
            for source in item['sources']:
                if source not in notes:
                    raise ValueError('Missing note source')
            if story['statistical_review']['source_sha256'] not in notes:
                raise ValueError('Notes do not identify the statistical source version')
            if story['b2_sensitivity']['source_sha256'] not in notes:
                raise ValueError('Notes do not identify the B2 source version')
            if index == 6:
                visible = '\n'.join(parts)
                expected_f1 = story['b2_sensitivity']['entropy']['test_metrics_after']['f1']
                for text in [f'B2 adds 9 provisional dev atoms: entropy F1 {expected_f1:.3f}',
                             'Same old test, not new confirmation.', 'B1 chart and interval:']:
                    if text not in visible:
                        raise ValueError('Visible B1/B2 distinction is missing or wrong')
        data = json.loads((ROOT/'reports/bizhallu_demo_v2_data.json').read_text(encoding='utf-8'))
        april = next(c for c in data['cases'] if c['question_id']=='q_0064')
        ordered = sorted(april['prompt_evidence_rows'],key=lambda r:r['net_revenue'],reverse=True)
        expected_april = [['Rank','Product','GBP net value']] + [[str(i+1),r['description'],f"{r['net_revenue']:,.2f}"] for i,r in enumerate(ordered)]
        expected_september = [['Product','GBP','Stated rank','Evidence rank']] + [[c['product_name'],c['amount_lexical'],str(c['stated_rank']),str(c['rank_in_shown_evidence'])] for c in story['september']]
        for slide, expected in [(2,expected_april),(3,expected_september)]:
            tables = ET.fromstring(z.read(f'ppt/slides/slide{slide}.xml')).findall('.//a:tbl',NS)
            if len(tables)!=1:
                raise ValueError('Missing editable evidence table')
            values = [[''.join(texts(cell)) for cell in row.findall('a:tc',NS)] for row in tables[0].findall('a:tr',NS)]
            if values != expected:
                raise ValueError('Evidence table differs from checked source rows')
        chart_names = [n for n in z.namelist() if re.search(r'/charts/chart\d+\.xml$',n)]
        if len(chart_names)!=1:
            raise ValueError('Expected one editable F1 chart')
        chart = ET.fromstring(z.read(chart_names[0]))
        values = [float(n.text) for n in chart.findall('.//c:ser/c:val//c:numCache/c:pt/c:v',NS)]
        rows = {r['signal']:r for r in story['statistical_review']['test_rows']}
        expected = [round(rows[k]['f1'],6) for k in ['mean_token_entropy','all_positive','one_minus_min_top2_margin']]
        if values!=expected:
            raise ValueError('Native chart values differ from six-decimal presentation source')
        axis = chart.find('.//c:valAx/c:scaling',NS)
        if axis is None or axis.find('c:min',NS).get('val')!='0' or axis.find('c:max',NS).get('val')!='1':
            raise ValueError('F1 chart must retain a full zero-to-one scale')
        if not any(n.endswith('.xlsx') and n.startswith('ppt/embeddings/') for n in z.namelist()):
            raise ValueError('Editable chart workbook is missing')
        for name in z.namelist():
            if name.endswith('.xml') and re.search(rb'[A-Za-z]:[\\/]Users[\\/]',z.read(name)):
                raise ValueError('Local user path in public PPTX')


def main():
    failures=[]
    payload=None
    try:
        payload=PPTX.read_bytes()
        validate_package(payload,build_story())
    except (OSError,ValueError,KeyError,TypeError,AttributeError,ET.ParseError,zipfile.BadZipFile) as exc:
        failures.append(str(exc))
    result={'deck_path':'reports/bizhallu_interview_v2.pptx','sha256':hashlib.sha256(payload).hexdigest() if payload else None,
            'status':'interview_deck_content_validated' if not failures else 'failed','slide_count':10,
            'native_table_slides':[2,3],'native_chart_slides':[6],
            'validation_scope':'OOXML_content_source_and_chart_structure; not native application or human review',
            'powerpoint_open_verified':False,'independent_human_annotation':False,
            'num_failures':len(failures),'failures':failures}
    (ROOT/'reports/bizhallu_interview_v2_validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    if failures:
        raise SystemExit(1)


if __name__=='__main__':
    main()
