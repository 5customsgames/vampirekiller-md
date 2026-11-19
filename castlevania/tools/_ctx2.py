exec(open("_ctx.py").read().split("for name,cx,cy,kind in")[0])
for name,cx,cy,kind in (("brazier 1",88,176,"brazier"),("brazier 3",343,176,"brazier"),("brazier 4",471,176,"brazier"),("brazier 5",599,176,"brazier")):
    ctx,types,sp=run(cx,cy,kind,None)
    print(name,"| code",ctx["code"],"state",{k:v for k,v in ctx.items() if k!="code"},"| types",types,"| sprites",sp,flush=True)
