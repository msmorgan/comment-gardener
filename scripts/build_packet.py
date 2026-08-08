from __future__ import annotations
import argparse, dataclasses, re, subprocess, sys
from pathlib import Path
from typing import Sequence
HUNK_RE=re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?: .*)?$")
POLICY_NAMES=("AGENTS.md","CLAUDE.md","GEMINI.md")
class PacketError(Exception): pass
@dataclasses.dataclass(frozen=True)
class SeedScope:
 old_path:str|None; new_path:str|None; old_start:int|None; old_count:int|None; new_start:int|None; new_count:int|None
def _key(s): return (s.old_path is None,s.old_path or "",s.new_path is None,s.new_path or "",*[-1 if x is None else x for x in (s.old_start,s.old_count,s.new_start,s.new_count)])
def _dedup(x): return sorted(set(x),key=_key)
def _decode(s):
 if not s.startswith('"'): return s
 if not s.endswith('"'): raise PacketError("undecodable quoted Git path")
 out=[]; i=1
 while i<len(s)-1:
  if s[i]!='\\': out.append(s[i]);i+=1;continue
  i+=1
  if i>=len(s)-1: raise PacketError("undecodable quoted Git path")
  c=s[i]; m={'n':'\n','r':'\r','t':'\t','b':'\b','f':'\f','\\':'\\','"':'"'}
  if c in m: out.append(m[c]);i+=1
  elif c in '01234567' and i+2<len(s)-1 and all(x in '01234567' for x in s[i:i+3]): out.append(chr(int(s[i:i+3],8)));i+=3
  else: raise PacketError("undecodable quoted Git path")
 return ''.join(out)
def _parts(s):
 out=[];i=0
 while i<len(s):
  while i<len(s) and s[i]==' ':i+=1
  if i==len(s):break
  a=i
  if s[i]=='"':
   i+=1
   while i<len(s) and s[i]!='"': i+=2 if s[i]=='\\' else 1
   if i>=len(s):raise PacketError("undecodable quoted Git path")
   i+=1
  else:
   while i<len(s) and s[i]!=' ':i+=1
  out.append(_decode(s[a:i]))
 return out
def _git(s,p):
 if s=='/dev/null':return None
 if not s.startswith(p):raise PacketError("invalid Git path")
 s=s[len(p):]; q=Path(s)
 if not s or q.is_absolute() or '..' in q.parts or '.' in q.parts:raise PacketError("unsafe Git path")
 return q.as_posix()
def parse_git_diff(text):
 out=[]; old=new=None; header=marks=False
 for l in text.splitlines():
  if l.startswith('diff --git '):
   x=_parts(l[11:])
   if len(x)!=2:raise PacketError("invalid diff --git header")
   _git(x[0],'a/');_git(x[1],'b/');old=new=None;header=True;marks=False
  elif l.startswith('--- '):
   if not header:raise PacketError("file marker without diff header")
   old=_git(_decode(l[4:].split('\t')[0]),'a/')
  elif l.startswith('+++ '): new=_git(_decode(l[4:].split('\t')[0]),'b/');marks=True
  elif l.startswith('@@'):
   m=HUNK_RE.fullmatch(l)
   if not m:raise PacketError("malformed hunk header")
   if not(header and marks and (old or new)):raise PacketError("hunk without complete file header")
   a,b,c,d=m.groups();out.append(SeedScope(old,new,int(a),int(b or 1),int(c),int(d or 1)))
 return list(dict.fromkeys(out))
def _file(root,v):
 p=Path(v)
 if p.is_absolute() or '..' in p.parts:raise PacketError("unsafe path")
 q=root/p
 try:q.resolve(strict=True).relative_to(root.resolve())
 except (OSError,ValueError):raise PacketError("path escapes repository")
 if q.is_symlink() or not q.is_file():raise PacketError("not a materialized regular file")
 return q
def resolve_explicit_paths(root,values):
 fs=[]
 for v in values:
  p=root/Path(v)
  if Path(v).is_absolute() or '..' in Path(v).parts:raise PacketError("unsafe path")
  if not p.exists() or p.is_symlink():raise PacketError("missing explicit target")
  if p.is_dir(): fs += [_file(root,x.relative_to(root).as_posix()) for x in p.rglob('*') if x.is_file() and not x.is_symlink()]
  else:fs.append(_file(root,v))
 return _dedup([SeedScope(None,x.relative_to(root).as_posix(),None,None,None,None) for x in fs])
def discover_policy_sources(root,scopes,explicit):
 found=[]
 for s in scopes:
  for v in (s.old_path,s.new_path):
   if not v:continue
   d=(root/v).parent
   while True:
    for n in POLICY_NAMES:
     p=d/n
     if p.is_file() and not p.is_symlink():found.append(p.relative_to(root).as_posix())
    if d==root:break
    d=d.parent
 auto=sorted(set(found),key=lambda x:(len(Path(x).parts),POLICY_NAMES.index(Path(x).name),x))
 extra=sorted({_file(root,x).relative_to(root).as_posix() for x in explicit})
 return list(dict.fromkeys(auto+extra))
def _fence(s):return '`'*(max([len(x) for x in re.findall(r'`+',s)]or[0])+1)
def render_packet(mode,scopes,policy_sources,user_constraints,capabilities,verification_commands):
 lines=['# Comment Gardener Job Packet','','## Mode',f'`{mode}`','','## Seed scopes']
 lines += ['- Resolution: successful no-op.'] if not scopes else []
 lines += ['- None.'] if not scopes else [f"- `{s.new_path or s.old_path}`: whole file" if s.old_start is None else f"- `{s.new_path or s.old_path}`: old {s.old_start},{s.old_count}; new {s.new_start},{s.new_count}" for s in scopes]
 for title,vals,lang in [('Policy sources',policy_sources,None),('Exact user constraints',user_constraints,'text'),('Environment capabilities',capabilities,None),('Verification commands',verification_commands,'console')]:
  lines += ['',f'## {title}']
  if not vals:lines+=['- None.']
  else:
   for i,v in enumerate(vals,1):
    if lang:
     f=_fence(v);lines += [f'{i}. {f}{lang}',v,f]
    else: lines += [f'- `{v}`']
 lines += ['','## Required report','- Effective mode','- Policy sources read','- Seed scopes','- Reference expansion','- Edits','- Preserved and protected comments','- Ambiguities','- Verification commands and results','- Packet fields or policy clauses that changed a verdict']
 return '\n'.join(lines)+'\n'
def main(argv=None):
 p=argparse.ArgumentParser(); g=p.add_mutually_exclusive_group();g.add_argument('--path',action='append');g.add_argument('--changeset',action='store_true');g.add_argument('--stack',action='store_true');g.add_argument('--revset');p.add_argument('--policy',action='append',default=[]);p.add_argument('--constraint',action='append',default=[]);p.add_argument('--capability',action='append',default=[]);p.add_argument('--verify',action='append',default=[]);p.add_argument('--mode',default='garden');a=p.parse_args(argv)
 try:
  if a.mode not in ('jungle','garden','zen'):raise PacketError('unknown mode')
  root=Path.cwd(); scopes=resolve_explicit_paths(root,a.path or []) if a.path else []
  if a.changeset or a.stack or a.revset:
   rr=subprocess.run(['jj','--no-pager','root'],cwd=root,text=True,capture_output=True)
   if rr.returncode:return 2
   rev='@' if a.changeset else ('immutable_heads()..@' if a.stack else a.revset)
   d=subprocess.run(['jj','--no-pager','diff','-r',rev,'--git'],cwd=root,text=True,capture_output=True,check=True).stdout;scopes=parse_git_diff(d)
  print(render_packet(a.mode,scopes,discover_policy_sources(root,scopes,a.policy),a.constraint,a.capability,a.verify),end='');return 0
 except (PacketError,OSError,subprocess.SubprocessError) as e:print(f'comment-gardener: {e}',file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
