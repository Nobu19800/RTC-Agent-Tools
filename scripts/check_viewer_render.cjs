const fs=require('fs'),path=require('path'),{spawnSync}=require('child_process');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||process.argv[2]||'playwright');
const root=path.resolve(__dirname,'..');
function fingerprint(){
  const p=spawnSync(process.env.VERIFY_PYTHON||'python',[path.join(__dirname,'verification_evidence.py')],{encoding:'utf8'});
  if(p.status!==0)throw new Error(p.stderr||'Fingerprint command failed');
  return JSON.parse(p.stdout).sha256;
}
(async()=>{
  const run=fs.readFileSync(path.join(root,'build/system/teleop/current-run.txt'),'utf8').trim().replace(/^\/mnt\/([a-z])\//i,(_,d)=>d.toUpperCase()+':/');
  const stamp=new Date().toISOString().replace(/[:.]/g,'-');
  const report={startedAtUTC:new Date().toISOString(),implementationFingerprint:fingerprint(),pageErrors:[],requestFailures:[],badResponses:[],consoleErrors:[],
    scope:'Headless software rendering initialization and live state; screenshot content requires recorded image review',
    screenshot:path.join(run,'viewer-render-'+stamp+'.png')};
  if(!process.env.VIEWER_BROWSER_EXECUTABLE)throw new Error('Set VIEWER_BROWSER_EXECUTABLE to the verified browser executable');
  const browser=await chromium.launch({executablePath:process.env.VIEWER_BROWSER_EXECUTABLE,headless:true,args:['--enable-unsafe-swiftshader']});
  try {
    const page=await browser.newPage({viewport:{width:1280,height:800}});
    // The sample has no favicon. Fulfill only that optional request; never
    // suppress missing modules/models or anonymous console errors.
    await page.route('**/favicon.ico',r=>r.fulfill({status:204,body:''}));
    page.on('pageerror',e=>report.pageErrors.push(String(e)));
    page.on('requestfailed',r=>report.requestFailures.push({url:r.url(),failure:r.failure()}));
    page.on('response',r=>{if(r.status()>=400)report.badResponses.push({url:r.url(),status:r.status()});});
    page.on('console',m=>{if(m.type()==='error')report.consoleErrors.push(m.text());});
    await page.goto(process.env.VIEWER_URL||'http://127.0.0.1:8000/index.html?viewerConfigPath=/config/viewer-config-fleets.json&wsUri=ws://127.0.0.1:8765&wireVersion=v2',{waitUntil:'networkidle',timeout:45000});
    await page.getByRole('button',{name:'connected',exact:true}).waitFor({timeout:15000});
    await page.waitForFunction(()=>document.querySelector('#prop-x')?.textContent.trim().length>0,null,{timeout:10000});
    report.dom=await page.evaluate(()=>({text:document.body.innerText,canvases:Array.from(document.querySelectorAll('canvas')).map(c=>({width:c.width,height:c.height}))}));
    await page.screenshot({path:report.screenshot});
  } catch(e){report.failure=String(e);} finally {await browser.close();}
  report.finishedAtUTC=new Date().toISOString();
  report.passed=!report.failure&&['pageErrors','requestFailures','badResponses','consoleErrors'].every(k=>report[k].length===0)&&report.dom?.canvases.some(c=>c.width>0&&c.height>0)&&report.implementationFingerprint===fingerprint();
  report.sceneImageReview='pending';
  const raw=JSON.stringify(report,null,2);
  fs.writeFileSync(path.join(run,'viewer-render-'+stamp+'.json'),raw);
  fs.writeFileSync(path.join(run,'viewer-render-result.json'),raw);
  console.log(raw); if(!report.passed)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1;});
