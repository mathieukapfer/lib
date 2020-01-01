import re

## syntaxe
sSpace = '\s+'
sName = '\w+'
sGuard='\[.*\]'
sActions='\{.*\}'

## grammar
sStateDef=[ sName, '{']
sState=sName
#sActions=[ '{', sName, sParam, ';']
sTransition=[ sState, sGuard, sState, sActions]

## read file
txt=file.read(open('sample.sm'))
print('file %s' % txt)

## parser
def search(phrase, pos):
    """ Search a list of regepx """
    for item in phrase:
        # remove whitespace if any
        x = re.match(sSpace, txt[pos:])
        if x:
            pos+=x.end()

        # is item here ?
        x = re.match(item, txt[pos:])
        if x:
            print('[' + txt[pos + x.start(): pos + x.end()] + ']')
            #print(pos+x.start(),pos+x.end())
            pos+=x.end()

    return pos

#x = re.findall(sState, txt)
#print(x)
#x = re.search(sName, txt)
#print(x.start(),x.end(),x.string)

pos=0
pos=search(sStateDef,pos)
pos=search(sTransition,pos)
pos=search(sTransition,pos)
pos=search(sTransition,pos)
