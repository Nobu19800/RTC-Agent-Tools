"""Read-only rtshell detail output limited to this deployment's RTCs.

Installed rtcat -ll intentionally clears its tree filter and can contact stale
unrelated registrations. Supply a scoped tree to the existing rtshell formatter.
"""
import sys
from rtctree.path import parse_path
from rtctree.tree import RTCTree
from rtshell import rtcat

if __name__=='__main__':
    if len(sys.argv)<4: raise SystemExit('usage: rtcat_scoped.py TARGET SCOPE_RTC SCOPE_RTC [SCOPE_RTC...]')
    target=sys.argv[1]; scopes=[parse_path(s)[0] for s in sys.argv[2:]]
    if parse_path(target)[0] not in scopes: raise SystemExit('Target outside permitted observation scope')
    tree=RTCTree(paths=scopes,filter=scopes)
    raise SystemExit(rtcat.main(['-ll',target],tree=tree))
