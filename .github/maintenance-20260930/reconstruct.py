#!/usr/bin/env python3
"""Reconstruct reviewed text from immutable evidence; never execute source data."""
import argparse,base64,hashlib,json,lzma,subprocess
from pathlib import Path,PurePosixPath

MARK='__COMPUTE_MANAGED_DIGEST__'
BASE='85651f151d6cd77dc1f091f830f27296ebaff64a'
def sha(data):return hashlib.sha256(data).hexdigest()
def old(path):
    result=subprocess.run(['git','show',BASE+':'+path],capture_output=True)
    return result.stdout if result.returncode==0 else b''
def norm(text,kind):
    if not text or not kind:return text
    data=json.loads(text)
    if kind=='mapping':
        for entry in data.get('skills',[]):
            for item in entry.get('managed_files',[]):item['sha256']=MARK
    elif kind=='audit':
        for entry in data['skills']:
            if entry.get('baseline_sha256') is not None:entry['baseline_sha256']='__BASELINE_DIGEST__'
            entry['current_sha256']='__CURRENT_DIGEST__'
    else:raise ValueError('Unknown normalization')
    return json.dumps(data,ensure_ascii=False,indent=2)+'\n'
def safe(path):
    p=PurePosixPath(path)
    if p.is_absolute() or '..' in p.parts or '\\' in path or not p.parts:raise ValueError(path)
    if p.parts[0] not in {'skills','docs','tests','.github','bin','README.md','README.en.md','CHANGELOG.md','package.json'}:raise ValueError(path)
    q=Path(path)
    if any(x.is_symlink() for x in [q,*q.parents]):raise ValueError('Symlink destination '+path)
    return q

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--parts',nargs='+',required=True);ap.add_argument('--sha256',required=True);ap.add_argument('--evidence',type=Path,required=True);ap.add_argument('--verify-only',action='store_true');args=ap.parse_args()
    encoded=''.join(Path(p).read_text().strip() for p in args.parts)
    packed=base64.b64decode(encoded,validate=True)
    if sha(packed)!=args.sha256:raise ValueError('Payload checksum mismatch')
    decoder=lzma.LZMADecompressor(memlimit=256*1024*1024)
    raw=decoder.decompress(packed,max_length=8*1024*1024)
    if not decoder.eof or decoder.unused_data:raise ValueError('Invalid or oversized recipe')
    recipe=json.loads(raw)
    if recipe['base']!=BASE:raise ValueError('Unexpected baseline')
    subprocess.run(['git','cat-file','-e',BASE+'^{commit}'],check=True)
    snapshot=json.loads((args.evidence/'snapshots.json').read_text());up={}
    def unpack(payload):
        b=base64.b64decode(payload['base64'],validate=True)
        blob=payload.get('git_blob') or payload.get('blob_sha')
        if sha(b)!=payload['sha256'] or hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()!=blob:raise ValueError('Source evidence checksum mismatch')
        return b
    for entry in snapshot['entries']:
        for origin in entry['origins']:
            for item in origin['files']:
                if item.get('current'):up[item['target']]=unpack(item['current'])
    closure=args.evidence/'closure.json'
    if closure.is_file():
        for item in json.loads(closure.read_text())['files']:up[item['target']]=unpack(item)
    for src,dest in [('LICENSE','LICENSE.upstream.txt'),('skills/productivity/grill-me/SKILL.md','references/upstream-grill-me.md'),('skills/productivity/grilling/SKILL.md','references/upstream-grilling.md')]:
        up['skills/task-understanding-decomposition/grill-me/'+dest]=unpack(snapshot['extra_sources']['mattpocock/skills']['files'][src])
    outputs={};modes={};kinds={}
    for path,(kind,ops,mode,normalization) in recipe['files'].items():
        safe(path)
        if kind not in {'upstream','original'} or mode not in {'100644','100755'}:raise ValueError('Bad recipe format')
        source=up[path] if kind=='upstream' else old(path)
        lines=norm(source.decode('utf-8'),normalization).splitlines(keepends=True);parts=[]
        for op in ops:
            if isinstance(op,str):parts.append(op)
            else:
                if not isinstance(op,list) or len(op)!=2 or not all(type(i) is int for i in op) or not 0<=op[0]<=op[1]<=len(lines):raise ValueError('Bad source slice')
                parts.append(''.join(lines[op[0]:op[1]]))
        outputs[path]=''.join(parts).encode();modes[path]=mode;kinds[path]=normalization
    def actual(path):
        safe(path)
        return outputs[path] if path in outputs else Path(path).read_bytes()
    for path,kind in kinds.items():
        if not kind:continue
        data=json.loads(outputs[path])
        if kind=='mapping':
            for entry in data.get('skills',[]):
                for item in entry.get('managed_files',[]):
                    if item['sha256']!=MARK:raise ValueError('Unexpected digest marker')
                    item['sha256']=sha(actual(item['path']))
        elif kind=='audit':
            for entry in data['skills']:
                entry['current_sha256']=sha(actual(entry['path']))
                if entry['baseline_sha256'] is not None:entry['baseline_sha256']=sha(old(entry['path']))
        outputs[path]=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode()
    receipts={p:[modes[p],sha(b)] for p,b in outputs.items()}
    digest=sha(json.dumps(receipts,sort_keys=True,separators=(',',':')).encode())
    if digest!=recipe['expected_digest']:raise ValueError('Reconstruction differs from reviewed tree: '+digest)
    if not args.verify_only:
        for path,data in outputs.items():
            target=safe(path);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);target.chmod(0o755 if modes[path]=='100755' else 0o644)
    print(json.dumps({'files':len(outputs),'expected_content_digest':digest,'written':not args.verify_only}))
if __name__=='__main__':main()
