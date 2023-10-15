import subprocess, sys

target = sys.argv[1]    # getting the target destination

max_hop = 30
if (len(sys.argv) > 2):
    max_hop = int(sys.argv[2])

IP = []

try:

    print('Processing Route')
    
    for t in range(1, max_hop+1):
        command = f"ping -c 1 -t {t} -4 {target}"
        result = subprocess.run(command, stdout = subprocess.PIPE, stderr = subprocess.PIPE, text = True, shell = True)
        L = result.stdout.strip().split()
        ind = L.index('received,')
        if L[ind-1]=='1':
            for i in range(len(L)):
                if (L[i][-1]==')'):
                    s = L[i]
                    IP.append(s[s.find('(')+1:len(s)-1])
                    break
            break
        else:
            try:
                ind = L.index('From')
                for i in range(ind+1, len(L)):
                    if L[i][-1]==')':
                        IP.append(L[i][1:len(L[i])-1])
                        break
            except:
                IP.append('')
    
    print('Route Processed')
    print('Processing Time')
    
    #print(IP)
    
    ind = 0
    for address in IP:
        ind += 1
        if address:
            print(ind, address, sep = '.\t', end='\t')
            for i in range(3):
                command = f"ping -c 3 {address}"
                result = subprocess.run(command, stdout = subprocess.PIPE, stderr = subprocess.PIPE, text = True, shell = True)
                #print(result.stdout)
                try:
                    print(result.stdout.split('/')[-3]+' ms',end='\t')
                except:
                    print('*',end='\t\t')
        else:
            print(ind,"\t*\t\t*\t\t*\t\t*",sep='',end='')
        print()
except:
    print('Name or Service not known')
