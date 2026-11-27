"""Organiza objetos nuevos sin renumerar referencias existentes del prefab."""
import re

def organize(blocks, added):
    by={int(re.search(r'&(\d+)',z)[1]):z for z in blocks}
    names={re.search(r'  m_Name: (.*)',z)[1].strip().strip('"'):int(re.search(r'&(\d+)',z)[1]) for z in blocks if z.startswith('--- !u!1 ')}
    transforms={int(re.search(r'm_GameObject: \{fileID: (\d+)\}',z)[1]):int(re.search(r'&(\d+)',z)[1]) for z in blocks if z.startswith('--- !u!4 ')}
    source=names[next(n for n in names if n.startswith('H_1_Cierre_Icrea_R14_0001_'))];gtemplate=by[source];ttemplate=by[transforms[source]]
    levels={};moving=[]
    for q in added:
        gid=names[q['id']+'_'+q['name']];tid=transforms[gid];moving.append(tid);levels.setdefault(q['group'].split('/')[0],[]).append(tid)
    for i,z in enumerate(blocks):
        if z.startswith('--- !u!4 '):
            for tid in moving:z=z.replace('  - {fileID: '+str(tid)+'}\n','')
            blocks[i]=z
    for j,(level,tids) in enumerate(levels.items()):
        go=700000000000090000+j*2;tr=go+1;parent=transforms[names[level]]
        g=re.sub(r'&\d+','&'+str(go),gtemplate,count=1);g=re.sub(r'  m_Component:\n.*?  m_Layer:',f'  m_Component:\n  - component: {{fileID: {tr}}}\n  m_Layer:',g,flags=re.S);g=re.sub(r'  m_Name: .*','  m_Name: Campus_R16',g)
        t=re.sub(r'&\d+','&'+str(tr),ttemplate,count=1);t=re.sub(r'm_GameObject: \{fileID: \d+\}',f'm_GameObject: {{fileID: {go}}}',t);t=t.replace('  m_Children: []','  m_Children:\n'+''.join('  - {fileID: '+str(tid)+'}\n' for tid in tids).rstrip());t=re.sub(r'm_Father: \{fileID: \d+\}',f'm_Father: {{fileID: {parent}}}',t)
        for i,z in enumerate(blocks):
            if z.startswith('--- !u!4 &'+str(parent)+'\n'):blocks[i]=z.replace('  m_Father:','  - {fileID: '+str(tr)+'}\n  m_Father:',1)
            elif any(z.startswith('--- !u!4 &'+str(tid)+'\n') for tid in tids):blocks[i]=re.sub(r'm_Father: \{fileID: \d+\}',f'm_Father: {{fileID: {tr}}}',z)
        blocks.extend([g,t])
    return blocks
