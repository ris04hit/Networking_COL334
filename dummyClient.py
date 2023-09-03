from socket import *
import threading, sys, subprocess

def send_msg(sock, msg):
    # function to send message
    for message in msg:
        sock.send(message.encode())

def receive_msg(sock):
    '''
        function to receive message from socket
    '''
    s = ''
    while s[-1] != '\n':
        s += sock.rcv(1024).decode()
    return s

def webserver(clientsocket):
    global line_ct
    # Processing lines from web server
    while line_ct != max_length:
        clientsocket.send('SENDLINE\n'.encode())                # Asking for line from webserver
        response = receive_msg(clientsocket).split('\n')       # Storing webserver response
        line_num = int(response[0])
        if line_num == -1:
            continue
        with line_lock[line_num]:
            if not line[line_num]:
                line[line_num] = response[1]
                with line_ct_lock:
                    line_ct += 1
                    print(line_ct)

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

# For Main Client
mainclient_ip = sys.argv[1]

# For dummy clients
dc_port = 12000
num_dc = 3                      # Max possible number of dummyclients
host = '2021CS10121@team\n'
serversocket.listen(num_dc)     # Setting the server to listen to other clients

# Getting our IP
command = ["curl", "https://ipinfo.io/ip"]
result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
host_ip = result.stdout.strip()
print(host_ip)

# Sending IP to main client
dummyclientsocket = [socket(AF_INET, SOCK_STREAM)]       # list of sockets of dummy clients (main client is also considered as dummy)
dummyclientsocket[0].connect((mainclient_ip, dc_port))
dummyclientsocket[0].send(('0 '+host_ip).encode())

# Recieving message from mainClient
mainsocket, address = serversocket.accept()
received_msg = mainsocket.recv(1024).decode().split()
connectionsocket = [mainsocket]           # list of connection sockets for acting as server
if received_msg[0] == '1':
    dc_ip = [mainclient_ip]+received_msg[1:]
    num_dc = len(dc_ip)         # Currrent number of dummyclients
    for i in range(1, num_dc):
        dummyclientsocket.append(socket(AF_INET, SOCK_STREAM))
        dummyclientsocket[i].connect((dc_ip[i], dc_port))        # Connection established to each dummy client
    mainsocket.send('2'.encode())                         # Confirmation message to main client that connection is established
    for i in range(num_dc-1):
        consocket, addr = serversocket.accept()
        connectionsocket.append(consocket)

# Receiving message from mainClient
received_msg = mainsocket.recv(1024).decode()
if received_msg == '3':
    clientsocket.connect((web_ip, web_port))                      # Connecting to web server

# receiving maxlength from main client
received_msg = mainsocket.recv(1024).decode().split()
if received_msg[0] == '4':
    max_length = int(received_msg[1])
else:                                                           # If max length not received from mainclient then asking from server
    msg = ['SUBMIT\n', host, '1\n', '1\n', '\n']
    send_msg(clientsocket, msg)
    response = clientsocket.recv(1024).decode().split()
    max_length = int(response[-5])

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
web_thread.join()

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