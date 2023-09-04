from socket import *
import threading, sys

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
        s += sock.recv(1).decode()
        if s[-1] == '\n':
            break
    return s

def webserver(clientsocket):
    # Processing lines from web server
    global line_ct
    while line_ct != max_length:
        send_msg(clientsocket, ['SENDLINE\n'])                # Asking for line from webserver
        line_num = int(receive_msg(clientsocket))                    # Storing webserver response
        line_content = receive_msg(clientsocket)
        if line_num == -1:
            continue
        with line_lock[line_num]:
            if not line[line_num]:
                line[line_num] = line_content
                with line_ct_lock:
                    line_ct += 1
                    print(line_ct)
        # creating threads for line transfer to dummyclients 
        dummy_thread = []
        for i in range(num_dc):
            dummy_thread.append(threading.Thread(target = send_msg, args=(dummyclientsocket[i], [str(line_num), '\n', line_content])))
            dummy_thread[i].start()
            
def receive_line(sock):
    # Processing lines from dummyclients
    global line_ct
    try:
        while line_ct != max_length:
            print('rec')
            line_num = int(receive_msg(sock))                    # Storing dummyclient response
            line_content = receive_msg(sock)
            with line_lock[line_num]:
                if not line[line_num]:
                    line[line_num] = line_content
                    with line_ct_lock:
                        line_ct += 1
                        print(line_ct)
    except:
        pass

def get_default_gateway():
    # Get the default route using socket
    with socket(AF_INET, SOCK_DGRAM) as s:
        s.connect(("8.8.8.8", 80))
        default_gateway = s.getsockname()[0]
    return default_gateway

def close_socket():
    clientsocket.close()
    serversocket.close()
    for i in range(num_dc):
        dummyclientsocket[i].close()


num_dc = int(sys.argv[1])                  # Number of dummy clients to be connected
try:
    # For web server
    web_ip = '10.17.51.115'
    web_port = 9801
    clientsocket = socket(AF_INET, SOCK_STREAM)

    # Creating a server socket
    serversocket = socket(AF_INET, SOCK_STREAM)
    server_port = 12000
    serversocket.bind(('', server_port))

    # For dummy clients
    dc_ip = []
    dc_port = 12000
    host = '2021CS10547@team\n'
    serversocket.listen(num_dc)     # Setting the server to listen to other clients

    # Getting our IP
    host_ip = get_default_gateway()
    print(host_ip)

    # Receiving IP from dummyclients
    connectionsocket = []           # list of connection sockets for acting as server
    for i in range(num_dc):
        consocket, addr = serversocket.accept()                 # Accepting connection
        connectionsocket.append(consocket)
        msg = receive_msg(connectionsocket[i]).split()
        if msg[0] == '0':
            dc_ip.append(msg[1])
        print(msg)

    # Connecting with dummy clients
    dummyclientsocket = []       # list of sockets of dummy clients
    for i in range(num_dc):
        dummyclientsocket.append(socket(AF_INET, SOCK_STREAM))
        dummyclientsocket[i].connect((dc_ip[i], dc_port))        # Connection established to each dummy client

    for i in range(num_dc):
        send_msg(dummyclientsocket[i], ['1 ', ' '.join(dc_ip), ' \n'])                 # Message for dummy client to connect to other clients
        response = receive_msg(dummyclientsocket[i])      # Confirmation message that dummyclient connected to other clients
        print(response)
        
    for i in range(num_dc):
        send_msg(dummyclientsocket[i], ['3 \n'])                # Message for dummy client to connect to web server
    clientsocket.connect((web_ip, web_port))                      # Connecting to web server

    # Asking for max length from server
    msg = ['SUBMIT\n', host, '1\n', '1\n', '\n']
    send_msg(clientsocket, msg)
    response = receive_msg(clientsocket).split()
    max_length = int(response[-5])

    # Sending max length to dummyclient
    for i in range(num_dc):
        send_msg(dummyclientsocket[i], ['4 ', str(max_length), ' \n'])

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
            msg.append(line[i])
    send_msg(clientsocket, msg)

    # Getting submit response from server
    response = receive_msg(clientsocket)
    print(response)

    # Closing sockets
    close_socket()
except Exception as e:
    close_socket()
    print(e)