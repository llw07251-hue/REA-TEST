// Headless three.js renderer: node shoot.js <wwwDir> <outDir> <jobs.json>
const { chromium } = require('playwright');
const http = require('http'), fs = require('fs'), path = require('path');
const [www, outDir, jobsFile] = process.argv.slice(2);
const jobs = JSON.parse(fs.readFileSync(jobsFile, 'utf8'));
const types = { '.html': 'text/html', '.js': 'text/javascript', '.glb': 'model/gltf-binary' };
const srv = http.createServer((q, r) => {
  const f = path.join(www, decodeURIComponent(q.url.split('?')[0].split('#')[0]));
  fs.readFile(f, (e, d) => { if (e) { r.writeHead(404); r.end(); return; }
    r.writeHead(200, { 'Content-Type': types[path.extname(f)] || 'application/octet-stream' }); r.end(d); });
}).listen(0, async () => {
  const port = srv.address().port;
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  for (const j of jobs) {
    const t0 = Date.now();
    const page = await browser.newPage({ viewport: { width: j.w || 1600, height: j.h || 1100 } });
    page.on('console', m => { if (m.type() === 'error') console.log('  console:', m.text()); });
    page.on('pageerror', e => console.log('  pageerror:', e.message));
    await page.goto(`http://127.0.0.1:${port}/render.html#` + encodeURIComponent(JSON.stringify(j)));
    await page.waitForFunction('window.__done === true', null, { timeout: 600000 });
    await page.locator('canvas').screenshot({ path: path.join(outDir, j.name + '.png') });
    console.log(j.name, ((Date.now() - t0) / 1000).toFixed(1) + 's');
    await page.close();
  }
  await browser.close(); srv.close();
});
