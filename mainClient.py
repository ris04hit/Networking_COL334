from socket import *
import threading
import sys

def send_msg(sock, msg):
    # function to send message
    for message in msg:
        sock.send(message.encode())

def receive_msg(sock):
    '''
        function to receive message from socket
    '''
    s = ''
    while True:
        s += sock.recv(1024).decode()
        if s[-1] == '\n':
            break
    return s

def webserver(clientsocket):
    # Processing lines from web server
    global line_ct
    while line_ct != max_length:
        clientsocket.send('SENDLINE\n'.encode())                # Asking for line from webserver
        resp = receive_msg(clientsocket)                    # Storing webserver response
        response = resp.split('\n')
        line_num = int(response[0])
        if line_num == -1:
            continue
        with line_lock[line_num]:
            if not line[line_num]:
                line[line_num] = response[1]
                with line_ct_lock:
                    line_ct += 1
                    print(line_ct)
        # creating threads for line transfer to dummyclients 
        dummy_thread = []
        for i in range(num_dc):
            dummy_thread.append(threading.Thread(target = send_msg, args=(dummyclientsocket[i], [response])))
            dummy_thread[i].start()
            
def receive_line(sock):
    # Processing lines from dummyclients
    global line_ct
    while True:
        response = receive_msg(sock).split('\n')
        line_num = int(response[0])
        with line_lock[line_num]:
            if not line[line_num]:
                line[line_num] = response[1]
                with line_ct_lock:
                    line_ct += 1
                    print(line_ct)

# For web server
web_ip = '10.17.51.115'
web_port = 9801
clientsocket = socket(AF_INET, SOCK_STREAM)

# Creating a server socket
serversocket = socket(AF_INET, SOCK_STREAM)
server_port = 12000
serversocket.bind(('', server_port))

# For dummy clients
num_dc = int(sys.argv[1])                  # Number of dummy clients to be connected
dc_ip = []
dc_port = 12000
host = '2021CS10547@team\n'
host_ip = gethostbyname(gethostname())
print(host_ip)
serversocket.listen(num_dc)     # Setting the server to listen to other clients

# Receiving IP from dummyclients
connectionsocket = []           # list of connection sockets for acting as server
for i in range(num_dc):
    consocket, addr = serversocket.accept()                 # Accepting connection
    connectionsocket.append(consocket)
    msg = connectionsocket[i].recv(1024).decode().split()
    if msg[0] == '0':
        dc_ip.append(msg[1])

# Connecting with dummy clients
dummyclientsocket = []       # list of sockets of dummy clients
for i in range(num_dc):
    dummyclientsocket.append(socket(AF_INET, SOCK_STREAM))
    dummyclientsocket[i].connect((dc_ip[i], dc_port))        # Connection established to each dummy client

for i in range(num_dc):
    dummyclientsocket[i].send(('1 '+dc_ip.join(' ')).encrypt())                 # Message for dummy client to connect to other clients
    response = dummyclientsocket[i].recv(1024).decode()      # Confirmation message that dummyclient connected to other clients
    
for i in range(num_dc):
    dummyclientsocket[i].send('3'.encrypt())                # Message for dummy client to connect to web server
clientsocket.connect((web_ip, web_port))                      # Connecting to web server

# Asking for max length from server
msg = ['SUBMIT\n', host, '1\n', '1\n', '\n']
send_msg(clientsocket, msg)
response = clientsocket.recv(1024).decode().split()
max_length = int(response[-5])

# Sending max length to dummyclient
for i in range(num_dc):
    dummyclientsocket[i].send(('4 '+str(max_length)).encode())

# variable to store lines and its count
line = [None]*max_length
line_lock = [threading.Lock() for i in range(max_length)]       # Lock for each line
line_ct = 0
line_ct_lock = threading.Lock()         # Lock for line_ct

# Creating different threads
web_thread = threading.Thread(target=webserver, args=(clientsocket, ))        # Creating a thread for web server
receive_thread = []             # list of threads for receiving lines from dummyclient
for i in range(num_dc):
    receive_thread.append(threading.Thread(target=receive_line, args=(connectionsocket[i],)))
    receive_thread[i].start()

web_thread.start()                  # Starting web server thread
web_thread.join()                   # Waiting for web server thread to finsih

# Submitting collected lines
msg = ['SUBMIT\n', host, str(line_ct)+"\n"]
for i in range (max_length):
    if line[i]:
        msg.append(str(i)+'\n')
        msg.append(line[i]+'\n')
send_msg(clientsocket, msg)

# Getting submit response from server
response = receive_msg(clientsocket)
print(response)

# Closing sockets
clientsocket.close()
for i in range(num_dc):
    dummyclientsocket[i].close()
serversocket.close()