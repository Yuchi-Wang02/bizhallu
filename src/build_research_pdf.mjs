// Optional local authoring step. Public CI validates committed files without a browser.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {parseArgs} from 'node:util';

const {values} = parseArgs({options:{'runtime-root':{type:'string'}}});
if (!values['runtime-root']) throw new Error('Provide the bundled dependency runtime root');
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const {chromium} = await import(pathToFileURL(path.join(values['runtime-root'],'node/node_modules/playwright/index.mjs')));
const html = (await fs.readFile(path.join(root,'reports/bizhallu_research_one_pager.html'),'utf8'))
  .replace('<head>', '<head><base href="https://yuchi-wang02.github.io/bizhallu/">');
const browser = await chromium.launch({channel:'msedge',headless:true});
try {
  const page = await browser.newPage({viewport:{width:1280,height:900},offline:true});
  await page.setContent(html,{waitUntil:'domcontentloaded'});
  await page.pdf({path:path.join(root,'reports/bizhallu_research_brief.pdf'),format:'A4',preferCSSPageSize:true,printBackground:true});
  console.log('Created reports/bizhallu_research_brief.pdf; inspect page count and render before publication.');
} finally {
  await browser.close();
}
