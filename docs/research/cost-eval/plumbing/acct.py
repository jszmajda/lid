import json,sys,glob,os
f=sys.argv[1]
recs=[json.loads(l) for l in open(f) if l.startswith('{')]
res=[r for r in recs if r.get('type')=='result'][-1]
sid=res['session_id']
print('result.total_cost_usd', res['total_cost_usd'])
print('result.modelUsage', {m:{k:v for k,v in u.items() if k in('inputTokens','outputTokens','cacheReadInputTokens','cacheCreationInputTokens','costUSD')} for m,u in res['modelUsage'].items()})
u=res['usage']; print('result.usage', {k:u[k] for k in ('input_tokens','output_tokens','cache_read_input_tokens','cache_creation_input_tokens')})
sub=[r for r in recs if r.get('parent_tool_use_id')]
print('stream records with parent_tool_use_id:', len(sub), set(r.get('type') for r in sub))
for r in recs:
    if r.get('type')=='user':
        for c in r['message'].get('content',[]) if isinstance(r['message'].get('content'),list) else []:
            if c.get('type')=='tool_result' and r.get('tool_use_result'):
                tur=r['tool_use_result']; 
                if isinstance(tur,dict) and ('totalTokens' in tur or 'usage' in tur): print('Agent tool_use_result keys', {k:tur[k] for k in tur if k in ('totalTokens','totalToolUseCount','totalDurationMs','usage','agentId')})
# transcripts on disk
cwd=[r for r in recs if r.get('subtype')=='init'][0]['cwd']
enc=cwd.replace('/','-').replace('_','-').replace('.','-')
base=os.path.expanduser('~/.claude/projects/'+enc)
files=glob.glob(base+'/'+sid+'.jsonl')+glob.glob(base+'/'+sid+'/**/*.jsonl',recursive=True)
def tally(path):
    seen={}; models=set()
    for l in open(path):
        try: d=json.loads(l)
        except: continue
        m=d.get('message') or {}
        if d.get('type')=='assistant' and m.get('usage'):
            seen[m.get('id')]=m['usage']; models.add(m.get('model'))
    t={k:sum(u.get(k,0) or 0 for u in seen.values()) for k in ('input_tokens','output_tokens','cache_read_input_tokens','cache_creation_input_tokens')}
    return t,models,len(seen)
for p in files: print(os.path.relpath(p,base), tally(p))
