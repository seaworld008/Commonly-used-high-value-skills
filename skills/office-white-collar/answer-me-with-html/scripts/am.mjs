#!/usr/bin/env node
// Offline, security-hardened technical report renderer.
// Original third-party author attribution and MIT license are retained in LICENSE.txt.
// This implementation intentionally excludes unsafe shell, network, active HTML and arbitrary file access.
import * as fs from 'node:fs';
import * as path from 'node:path';
import { randomBytes } from 'node:crypto';

const MAX_INPUT = 256 * 1024;
const MAX_PAGE = 2 * 1024 * 1024;
const SAFE_NAME = /^am-[a-f0-9]{24}\.html$/;
const FENCE = String.fromCharCode(96).repeat(3);
function fail(message, code = 2) {
  process.stderr.write('am: ' + message + '\n');
  process.exit(code);
}
function esc(value) {
  return String(value).replaceAll('&','&amp;').replaceAll('<','&lt;')
    .replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
}
function workspace() {
  const base = fs.realpathSync(process.cwd());
  const root = path.join(base, '.am-pages');
  if (!fs.existsSync(root)) fs.mkdirSync(root, { mode: 0o700 });
  const stat = fs.lstatSync(root);
  if (!stat.isDirectory() || stat.isSymbolicLink() || fs.realpathSync(root) !== root)
    fail('unsafe report output directory');
  if ((stat.mode & 0o022) !== 0)
    fail('report output directory must not be group or world writable');
  return root;
}
function boundedRead(fd, limit) {
  const parts = [];
  const buffer = Buffer.allocUnsafe(16384);
  let used = 0;
  for (;;) {
    const n = fs.readSync(fd, buffer, 0, buffer.length, null);
    if (!n) break;
    used += n;
    if (used > limit) fail('input exceeds configured size limit');
    parts.push(Buffer.from(buffer.subarray(0,n)));
  }
  return Buffer.concat(parts).toString('utf8');
}
function parseMetadata(draft) {
  const input = draft.replaceAll('\r\n','\n').replaceAll('\r','\n');
  const meta = {};
  if (!input.startsWith('---\n')) return {meta, body:input};
  const end = input.indexOf('\n---\n',4);
  if (end < 0 || end > 8192) fail('invalid or oversized frontmatter');
  for (const line of input.slice(4,end).split('\n')) {
    const n = line.indexOf(':');
    if (n < 1) continue;
    const key = line.slice(0,n).trim();
    if (['title','subtitle','lang'].includes(key))
      meta[key] = line.slice(n+1).trim().replace(/^['"]|['"]$/g,'');
  }
  return {meta,body:input.slice(end+5)};
}
function panels(text) {
  const out = [];
  let current = {title:'Overview', lines:[]};
  for (const line of text.split('\n')) {
    if (line.startsWith('## ')) {
      if (current.lines.length || out.length) out.push(current);
      current = {title:line.slice(3).trim().replace(/\s*\{[^}]*\}\s*$/,''),lines:[]};
    } else current.lines.push(line);
  }
  out.push(current);
  if (out.length > 24) fail('report has more than 24 panels');
  return out.filter(p=>p.lines.some(line=>line.trim()) || p.title!=='Overview');
}
function flowDiagram(lines) {
  return lines.map(line=>{
    const nodes = line.split(/\s+--?>\s+/).map(s=>s.trim()).filter(Boolean);
    return nodes.length > 1 ?
      '<div class="flow">'+nodes.map(v=>'<span class="node">'+esc(v)+'</span>').join('<span class="arrow" aria-hidden="true">→</span>')+'</div>'
      :'<pre>'+esc(line)+'</pre>';
  }).join('\n');
}
function tableHTML(lines) {
  const rows=lines.map(line=>line.trim().replace(/^\||\|$/g,'').split('|'));
  return '<table>'+rows.flatMap((row,i)=>{
    if(i===1 && row.every(c=>/^\s*:?-{3,}:?\s*$/.test(c)))return [];
    const tag=i===0?'th':'td';
    return ['<tr>'+row.map(v=>'<'+tag+'>'+esc(v.trim())+'</'+tag+'>').join('')+'</tr>'];
  }).join('')+'</table>';
}
function renderLines(lines) {
  const html=[], paragraph=[], bullets=[], rows=[];
  let inFence=false,lang='',code=[];
  const flush=()=>{
    if(paragraph.length){html.push('<p>'+esc(paragraph.join(' ').trim())+'</p>');paragraph.length=0;}
    if(bullets.length){html.push('<ul>'+bullets.map(v=>'<li>'+esc(v)+'</li>').join('')+'</ul>');bullets.length=0;}
    if(rows.length){html.push(tableHTML(rows));rows.length=0;}
  };
  for(const line of [...lines,'']){
    if(inFence){
      if(line.startsWith(FENCE)){
        html.push(lang==='flow'?flowDiagram(code):'<pre class="code"><code>'+esc(code.join('\n'))+'</code></pre>');
        code=[];lang='';inFence=false;
      }else code.push(line);
      continue;
    }
    if(line.startsWith(FENCE)){flush();inFence=true;lang=line.slice(3).trim().split(' ')[0];continue;}
    if(!line.trim()){flush();continue;}
    if(line.startsWith('|')){if(paragraph.length||bullets.length)flush();rows.push(line);continue;}
    if(/^\s*[-*+]\s+/.test(line)){if(paragraph.length||rows.length)flush();bullets.push(line.replace(/^\s*[-*+]\s+/,''));continue;}
    if(line.startsWith('### ')){flush();html.push('<h3>'+esc(line.slice(4))+'</h3>');continue;}
    if(line.startsWith('# ')){flush();html.push('<h3>'+esc(line.slice(2))+'</h3>');continue;}
    if(line.startsWith('> ')){flush();html.push('<blockquote>'+esc(line.slice(2))+'</blockquote>');continue;}
    if(rows.length||bullets.length)flush();
    paragraph.push(line);
  }
  if(inFence)html.push('<pre class="code"><code>'+esc(code.join('\n'))+'</code></pre>');
  return html.join('\n');
}
function buildPage(draft) {
  if(Buffer.byteLength(draft)>MAX_INPUT)fail('draft too large');
  const {meta,body}=parseMetadata(draft);
  const title=(meta.title||'Technical Report').slice(0,180);
  const subtitle=(meta.subtitle||'').slice(0,300);
  const lang=/^[a-zA-Z]{2,3}(?:-[a-zA-Z]{2,8})?$/.test(meta.lang||'')?meta.lang:'en';
  const sections=panels(body).map(p=>'<section><h2>'+esc(p.title)+'</h2>'+renderLines(p.lines)+'</section>').join('\n');
  const source=Buffer.from(draft,'utf8').toString('base64');
  return '<!doctype html>\n<html lang="'+esc(lang)+'"><head><meta charset="utf-8">'
    +'<meta name="viewport" content="width=device-width,initial-scale=1">'
    +'<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; style-src &#39;unsafe-inline&#39;; img-src data:; base-uri &#39;none&#39;; form-action &#39;none&#39;;">'
    +'<title>'+esc(title)+'</title>'
    +'<style>:root{font-family:system-ui,sans-serif;color-scheme:light dark}body{margin:0;padding:24px;background:#101827;color:#edf2fa}main{max-width:1160px;margin:auto}h1{font-size:2rem}h2{font-size:1.15rem}section{background:#1c273b;border:1px solid #38455d;border-radius:12px;padding:24px;margin:16px 0}p,li{line-height:1.6}table{border-collapse:collapse;width:100%}td,th{border:1px solid #475b75;padding:9px;text-align:left;vertical-align:top}th{background:#27364e}pre{background:#0b1424;overflow:auto;white-space:pre-wrap;border-radius:8px;padding:15px}.flow{display:flex;flex-wrap:wrap;gap:12px;align-items:center}.node{border:1px solid #83a9df;border-radius:7px;background:#293f61;padding:12px}.arrow{color:#a6caff}blockquote{border-left:3px solid #a1bfea;margin:0;padding:10px}footer{font-size:.8rem;opacity:.7;padding:20px 0}@media(prefers-color-scheme:light){body{background:#f5f8ff;color:#152338}section{background:white;border-color:#dce5f0}pre{background:#eaf1fb}.node{background:#e3eeff;color:#142a4a}td,th{border-color:#d2dbe8}th{background:#e8eef8}}</style></head>'
    +'<body><main><header><h1>'+esc(title)+'</h1><p>'+esc(subtitle)+'</p></header>'
    +sections+'<footer>Offline report. Untrusted HTML and SVG are shown as escaped text; no scripts or network requests run.</footer>'
    +'<!-- AM_SOURCE:'+source+' --></main></body></html>\n';
}
function writeNew(draft){
  const root=workspace(),filename=path.join(root,'am-'+randomBytes(12).toString('hex')+'.html');
  const fd=fs.openSync(filename,fs.constants.O_CREAT|fs.constants.O_EXCL|fs.constants.O_WRONLY|fs.constants.O_NOFOLLOW,0o600);
  try{fs.writeFileSync(fd,buildPage(draft),'utf8');}finally{fs.closeSync(fd);}
  console.log('✓ '+filename);
}
function openOwned(filename){
  const root=workspace(),full=path.resolve(filename);
  if(path.dirname(full)!==root || !SAFE_NAME.test(path.basename(full)))fail('page is not a managed report path');
  const fd=fs.openSync(full,fs.constants.O_RDWR|fs.constants.O_NOFOLLOW);
  const stat=fs.fstatSync(fd);
  if(!stat.isFile() || stat.size>MAX_PAGE){fs.closeSync(fd);fail('unsafe or oversized page');}
  return {fd,full};
}
function patchPage(file,title,replacement){
  if(!title || title.length>180)fail('patch requires a bounded --panel value');
  const {fd,full}=openOwned(file);
  try{
    const html=boundedRead(fd,MAX_PAGE);
    const match=/<!-- AM_SOURCE:([A-Za-z0-9+/=]+) -->/.exec(html);
    if(!match)fail('not an editable report');
    const source=Buffer.from(match[1],'base64').toString('utf8');
    const result=[];
    let found=0,skip=false;
    const replacementLines=replacement.trim().split('\n');
    for(const line of source.split('\n')){
      if(line.startsWith('## ')){
        skip=false;
        if(line.slice(3).trim()===title){found++;skip=true;result.push(line,...replacementLines.filter((s,i)=>i!==0||!s.startsWith('## ')));continue;}
      }
      if(!skip)result.push(line);
    }
    if(found!==1)fail('panel is missing or ambiguous');
    const updated=buildPage(result.join('\n'));
    fs.ftruncateSync(fd,0);
    fs.writeSync(fd,updated,0,'utf8');
    console.log('✓ '+full);
  }finally{fs.closeSync(fd);}
}
function help(){
  console.log('Secure offline HTML report generator\nUsage:\n  am render - [--no-open]\n  am patch .am-pages/am-<24hex>.html --panel "Section title"\n  am help\n  am list\n\nPanels support Markdown text, lists, tables, fenced code and simple flow diagrams.\nNo shell, network access, scripts, external HTML, automatic browser open, serve or update. Unsafe legacy operations are disabled.');
}
function main(argv){
  const command=argv.shift()||'help';
  if(['help','--help','-h','list'].includes(command))return help();
  if(command==='render'){
    const input=argv.shift();
    if(input!=='-'||argv.some(a=>a!=='--no-open'))fail('usage: render - [--no-open]');
    return writeNew(boundedRead(0,MAX_INPUT));
  }
  if(command==='patch'){
    const file=argv.shift(),idx=argv.indexOf('--panel');
    if(!file||idx<0||idx+1>=argv.length||argv.length!==2)fail('usage: patch <managed-page> --panel <section-title>');
    return patchPage(file,argv[idx+1],boundedRead(0,MAX_INPUT));
  }
  fail('unsupported or disabled command: '+command);
}
try{main(process.argv.slice(2));}
catch(e){fail(e instanceof Error?e.message:'unknown failure');}
