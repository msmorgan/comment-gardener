from __future__ import annotations
import argparse,dataclasses,re,subprocess,sys
from pathlib import Path
HUNK_RE=re.compile(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?: .*)?$'); N=('AGENTS.md','CLAUDE.md','GEMINI.md')
class PacketError(Exception):pass
@dataclasses.dataclass(frozen=True)
class SeedScope: old_path:str|None;new_path:str|None;old_start:int|None;old_count:int|None;new_start:int|None;new_count:int|None
def _dedup(x):return sorted(set(x),key=lambda s:(s.old_path is None,s.old_path or '',s.new_path is None,s.new_path or '',s.old_start or -1,s.old_count or -1,s.new_start or -1,s.new_count or -1))
def _path(s,p):
 if s=='/dev/null':return None
 if not s.startswith(p):raise PacketError('invalid Git path')
 s=s[2:]
 if not s or Path(s).is_absolute() or '..' in Path(s).parts:raise PacketError('unsafe Git path')
 return Path(s).as_posix()
def parse_git_diff(t):
 out=[];o=n=None;h=m=False
 for l in t.splitlines():
  if l.startswith('diff --git '):h=True;m=False;o=n=None
  elif l.startswith('--- '):o=_path(l[4:].split('\t')[0].strip('"'),'a/')
  elif l.startswith('+++ '):n=_path(l[4:].split('\t')[0].strip('"'),'b/');m=True
  elif l.startswith('@@'):
   z=HUNK_RE.fullmatch(l)
   if not z or not(h and m):raise PacketError('malformed hunk header')
   a,b,c,d=z.groups();out.append(SeedScope(o,n,int(a),int(b or 1),int(c),int(d or 1)))
 return list(dict.fromkeys(out))
def resolve_explicit_paths(root,values):
 out=[]
 for v in values:
  p=root/v
  if Path(v).is_absolute() or '..' in Path(v).parts or not p.exists() or p.is_symlink():raise PacketError('missing explicit target')
  for q in ([p] if p.is_file() else [x for x in p.rglob('*') if x.is_file() and not x.is_symlink()]):out.append(SeedScope(None,q.relative_to(root).as_posix(),None,None,None,None))
 return _dedup(out)
def discover_policy_sources(root,scopes,explicit):
 a=[]
 for s in scopes:
  for v in (s.old_path,s.new_path):
   d=(root/v).parent if v else root
   while True:
    a += [(d/x).relative_to(root).as_posix() for x in N if (d/x).is_file() and not(d/x).is_symlink()]
    if d==root:break
    d=d.parent
 e=[]
 for v in explicit:
  p=root/v
  if not p.is_file() or p.is_symlink():raise PacketError('not a materialized regular file')
  e.append(p.relative_to(root).as_posix())
 return list(dict.fromkeys(sorted(set(a),key=lambda x:(len(Path(x).parts),N.index(Path(x).name),x))+sorted(set(e))))
def _fence(s):return '`'*max(4,max([len(x)+1 for x in re.findall(r'`+',s)]or[0]))
def render_packet(mode,scopes,policy_sources,user_constraints,capabilities,verification_commands):
 l=['# Comment Gardener Job Packet','','## Mode',f'`{mode}`','','## Seed scopes']+(['- Resolution: successful no-op.','- None.'] if not scopes else [f'- `{s.new_path or s.old_path}`: whole file' for s in scopes])
 for title,x,lang in [('Policy sources',policy_sources,''),('Exact user constraints',user_constraints,'text'),('Environment capabilities',capabilities,''),('Verification commands',verification_commands,'console')]:
  l+=['',f'## {title}']
  for i,v in enumerate(x or ['None.'],1):
   if lang and x:f=_fence(v);l += [f'{i}. {f}{lang}',v,f]
   else:l += [f'- `{v}`' if x else '- None.']
 return '\n'.join(l+['','## Required report','- Effective mode','- Policy sources read','- Seed scopes','- Reference expansion','- Edits','- Preserved and protected comments','- Ambiguities','- Verification commands and results','- Packet fields or policy clauses that changed a verdict'])+'\n'
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--mode',default='garden');p.add_argument('--path',action='append');p.add_argument('--policy',action='append',default=[]);p.add_argument('--constraint',action='append',default=[]);p.add_argument('--capability',action='append',default=[]);p.add_argument('--verify',action='append',default=[]);a=p.parse_args(argv)
 try:
  if a.mode not in ('jungle','garden','zen'):raise PacketError('unknown mode')
  s=resolve_explicit_paths(Path.cwd(),a.path or []);print(render_packet(a.mode,s,discover_policy_sources(Path.cwd(),s,a.policy),a.constraint,a.capability,a.verify),end='');return 0
 except PacketError as e:print(f'comment-gardener: {e}',file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
