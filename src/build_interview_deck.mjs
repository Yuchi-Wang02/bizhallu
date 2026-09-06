// Local deck authoring; requires the bundled Artifact Tool runtime, never CI/GPU.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {parseArgs} from 'node:util';

const {values:args} = parseArgs({options:{'runtime-root':{type:'string'},'skill-dir':{type:'string'},revision:{type:'string',default:'r1'}}});
if(!args['runtime-root'] || !args['skill-dir'] || !/^r[0-9]+$/.test(args.revision)) throw new Error('Provide runtime root, skill directory and rN revision');
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const runtime = path.resolve(args['runtime-root']);
const skill = path.resolve(args['skill-dir']);
process.env.RUNTIME_NODE_MODULES = path.join(runtime,'node/node_modules');
const {Presentation,PresentationFile,FileBlob} = await import(pathToFileURL(path.join(runtime,'node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs')));
const {resolvePresentationFont,applyPresentationChartFont,finalizePresentation} = await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')));
const family = resolvePresentationFont();
const work = path.join(root,'outputs/presentation_v2',args.revision);
await fs.mkdir(work,{recursive:true});
await fs.mkdir(path.join(work,'final'),{recursive:true});
const summary = JSON.parse(await fs.readFile(path.join(root,'reports/bizhallu_career_package_summary.json'),'utf8'));
const story = summary.story;
if(story.revision !== 'english_research_B1_B2_2026_09_06' || story.slides.length!==10 || story.five_minute_seconds!==300) throw new Error('Unexpected story revision');
const data = JSON.parse(await fs.readFile(path.join(root,'reports/bizhallu_demo_v2_data.json'),'utf8'));
const presentation = Presentation.create({slideSize:{width:1280,height:720}});
const ink='#202124', muted='#52616B', teal='#18765E', red='#A13238';

function text(slide,value,x,y,w,h,size=30,color=ink,bold=false){
  const shape=slide.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  shape.text=value;
  shape.text.style={typeface:family,fontSize:size,color,bold,autoFit:'none'};
  return shape;
}
function table(slide,values,top,widths,rowHeight=58){
  const t=slide.tables.add({rows:values.length,columns:widths.length,left:64,top,width:1152,height:rowHeight*values.length,columnWidths:widths,values});
  t.borders.assign({fill:'#D5DEE2',width:1,style:'solid'});
  for(let r=0;r<values.length;r++){
    t.rows[r].height=rowHeight;
    for(let c=0;c<widths.length;c++){
      const cell=t.getCell(r,c);
      cell.fill=r===0?'#E8EFF0':'#FFFFFF';
      cell.text.style={typeface:family,fontSize:23,color:ink,bold:r===0,autoFit:'none'};
    }
  }
  return t;
}
for(const [index,item] of story.slides.entries()){
  const slide=presentation.slides.add();
  slide.background.fill='#FFFFFF';
  if(item.kind==='title'){
    text(slide,'BizHallu',64,165,1130,110,72,ink,true);
    text(slide,item.lines[0],66,293,1080,100,38,teal);
    text(slide,item.lines[1],66,440,1100,74,24,muted);
    text(slide,item.lines[2],66,562,1050,42,23,muted);
  }else{
    text(slide,item.title,64,44,1152,98,44,ink,true);
    if(item.kind==='case'){
      text(slide,`Qwen assigns rank 3 to ${story.april.product_name} at GBP ${story.april.amount_lexical}`,64,150,1152,54,25,red,true);
      const rows=data.cases.find(c=>c.question_id==='q_0064').prompt_evidence_rows;
      const ordered=[...rows].sort((a,b)=>b.net_revenue-a.net_revenue);
      const values=[['Rank','Product','GBP net value'],...ordered.map((r,i)=>[String(i+1),r.description,Number(r.net_revenue).toLocaleString('en-GB',{minimumFractionDigits:2,maximumFractionDigits:2})])];
      const evidenceTable=table(slide,values,206,[85,785,282],44);
      for(const [rank,fill,color] of [[3,'#EAF5F1',teal],[story.april.rank_in_shown_evidence,'#FCEDEF',red]]){
        for(let c=0;c<3;c++){
          const cell=evidenceTable.getCell(rank,c);
          cell.fill=fill;
          cell.text.style={typeface:family,fontSize:23,color,bold:true,autoFit:'none'};
        }
      }
      text(slide,'Eight evidence rows, sorted here for comparison. The demo preserves original prompt order.\nThe copied amount matches its product. Six products have larger values.',64,612,1152,65,22,muted);
    }else if(item.kind==='relations'){
      text(slide,item.lines[0],64,158,1152,54,29,teal,true);
      const relationTable=table(slide,[['Product','GBP','Stated rank','Evidence rank'],...story.september.map(c=>[c.product_name,c.amount_lexical,String(c.stated_rank),String(c.rank_in_shown_evidence)])],242,[572,220,180,180],76);
      for(let r=1;r<4;r++){
        relationTable.getCell(r,3).text.style={typeface:family,fontSize:26,color:red,bold:true,autoFit:'none'};
      }
      text(slide,item.lines[2],64,589,1152,65,23,muted);
    }else if(item.kind==='metrics'){
      const signals=['mean_token_entropy','all_positive','one_minus_min_top2_margin'];
      const rows=new Map(story.statistical_review.test_rows.map(r=>[r.signal,r]));
      const chart=slide.charts.add('bar',{position:{left:60,top:170,width:650,height:376},
        categories:['Token entropy','Flag every span','Top-2 margin'],
        series:[{name:'Test F1',values:signals.map(k=>Number(rows.get(k).f1.toFixed(6))),valuesFormatCode:'0.000',fill:teal,
          dataLabelOverrides:signals.map((k,idx)=>({idx,text:rows.get(k).f1.toFixed(3),showValue:false,position:'outEnd',textStyle:{typeface:family,fontSize:24,bold:true}}))}],
        hasLegend:false,barOptions:{direction:'column',grouping:'clustered'},
        xAxis:{textStyle:{typeface:family,fontSize:21}},
        yAxis:{min:0,max:1,majorUnit:0.2,numberFormatCode:'0.0',textStyle:{typeface:family,fontSize:20}},
        dataLabels:{showValue:false,position:'outEnd',textStyle:{typeface:family,fontSize:24,bold:true}},
        chartFill:'#FFFFFF',plotAreaFill:'#FFFFFF'});
      applyPresentationChartFont(chart,{fontFamily:family});
      text(slide,'Entropy - flag every span',760,185,435,67,28,ink,true);
      const d=story.statistical_review.entropy_minus_all_positive;
      text(slide,`${d.point_difference.toFixed(4)} F1 difference`,760,268,435,64,33,teal,true);
      text(slide,`Paired 95% interval\n[${d.lower_95.toFixed(4)}, ${d.upper_95.toFixed(4)}]\nCrosses zero`,760,350,435,132,27,red);
      text(slide,'B1 chart and interval: 103 provisional test spans; original dev thresholds. Exploratory.',64,558,1152,36,22,muted);
      text(slide,`B2 adds 9 provisional dev atoms: entropy F1 ${story.b2_sensitivity.entropy.test_metrics_after.f1.toFixed(3)}; margin unchanged.`,64,606,1152,38,24,red,true);
      text(slide,'Same old test, not new confirmation. B1 chart values and paired interval are not updated B2 estimates.',64,648,1152,28,19,muted);
    }else{
      const gap=item.lines.length===3?140:115;
      item.lines.forEach((line,i)=>text(slide,line,64,172+i*gap,1136,gap-18,29,i===0?teal:ink,i===0));
    }
  }
  text(slide,`BizHallu   ${String(index+1).padStart(2,'0')} / 10`,64,687,1140,22,16,muted);
  slide.speakerNotes.textFrame.setText(item.script+'\n\nSources:\n'+item.sources.map(s=>s.startsWith('https://')?s:'https://github.com/Yuchi-Wang02/bizhallu/blob/main/'+s).join('\n')+'\nStatistical source SHA-256: '+story.statistical_review.source_sha256+'\nB2 sensitivity source SHA-256: '+story.b2_sensitivity.source_sha256+(item.kind==='metrics'?'\nChart workbook stores six-decimal presentation values; source analysis retains full saved-trace precision. Labels show three decimals.':''));
}
const candidate=path.join(work,'candidate.pptx');
await (await PresentationFile.exportPptx(presentation)).save(candidate);
for(let i=0;i<10;i++){
  const slide=presentation.slides.items[i];
  const png=await presentation.export({slide,format:'png',scale:1});
  await fs.writeFile(path.join(work,`slide-${i+1}.png`),new Uint8Array(await png.arrayBuffer()));
  const layout=await slide.export({format:'layout'});
  await fs.writeFile(path.join(work,`slide-${i+1}.layout.json`),await layout.text());
}
const result=await finalizePresentation({workspaceDir:work,candidatePath:candidate,
  finalPath:path.join(work,'final',`bizhallu_interview_v2_${args.revision}.pptx`),
  pythonExecutable:path.join(runtime,'python/python.exe'),
  integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit',
    '--require-native-table-slide','2','--require-native-table-slide','3'],
  explicitTotalSlideCount:10,requiredNativeTableOwnerSlides:[2,3],requiredNativeChartOwnerSlides:[6],
  materializeLiteralChartWorkbooks:true,fontPolicy:{basis:'design',families:[family]},
  verifyArtifactToolImport:true,receiptPath:path.join(work,'validation.json')});
const finalPresentation=await PresentationFile.importPptx(await FileBlob.load(result.finalPath));
for(let i=0;i<10;i++){
  const png=await finalPresentation.export({slide:finalPresentation.slides.items[i],format:'png',scale:1});
  await fs.writeFile(path.join(work,`final-slide-${i+1}.png`),new Uint8Array(await png.arrayBuffer()));
}
// Compose rendered evidence only; all underlying slide objects remain editable.
const {default:sharp}=await import(pathToFileURL(path.join(runtime,'node/node_modules/sharp/dist/index.mjs')));
const thumbnails=[];
for(let i=0;i<10;i++){
  thumbnails.push({input:await sharp(path.join(work,`final-slide-${i+1}.png`)).resize(640,360).png().toBuffer(),
    left:16+(i%2)*656,top:16+Math.floor(i/2)*376});
}
await sharp({create:{width:1328,height:1896,channels:3,background:'#D5DEE2'}})
  .composite(thumbnails).png().toFile(path.join(work,'overview.png'));
await fs.copyFile(path.join(work,'final-slide-6.png'),path.join(work,'preview.png'));
console.log(JSON.stringify({font:family,finalPath:result.finalPath,sha256:result.finalSha256,
  warnings:result.presentationLayout.warnings,slidesRendered:10},null,2));
