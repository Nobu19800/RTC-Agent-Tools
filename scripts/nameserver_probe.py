"""Probe/list the naming service without contacting unrelated registered RTCs."""
import sys
import CORBA
import CosNaming

orb=CORBA.ORB_init(['nameserver-probe','-ORBclientCallTimeOutPeriod','4000'],CORBA.ORB_ID)
try:
    root=orb.string_to_object('corbaloc:iiop:'+sys.argv[1]+'/NameService')._narrow(CosNaming.NamingContext)
    if root is None: raise RuntimeError('NameService is not a NamingContext')
    bindings,iterator=root.list(1000)
    pages=0
    while iterator is not None:
        more,items=iterator.next_n(1000); bindings.extend(items); pages+=1
        if not more: iterator.destroy(); break
        if pages>=16: raise RuntimeError('Naming listing exceeds bounded capacity')
    for binding in bindings:
        print('/'.join(n.id+('.'+n.kind if n.kind else '') for n in binding.binding_name))
finally:
    orb.destroy()
