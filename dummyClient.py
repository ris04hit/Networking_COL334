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
    for i in range(num_dc):
        dummyclientsocket[i].close()
    serversocket.close()


try:
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
    host_ip = get_default_gateway()
    print(host_ip)

    # Sending IP to main client
    dummyclientsocket = [socket(AF_INET, SOCK_STREAM)]       # list of sockets of dummy clients (main client is also considered as dummy)
    dummyclientsocket[0].connect((mainclient_ip, dc_port))
    send_msg(dummyclientsocket[0], ['0 ', host_ip, ' \n'])

    # Recieving message from mainClient
    mainsocket, address = serversocket.accept()
    rec_msg = receive_msg(mainsocket).split()
    print(rec_msg)
    connectionsocket = [mainsocket]           # list of connection sockets for acting as server
    if rec_msg[0] == '1':
        dc_ip = [mainclient_ip]+rec_msg[1:]
        dc_ip.remove(host_ip)
        num_dc = len(dc_ip)         # Currrent number of dummyclients
        for i in range(1, num_dc):
            dummyclientsocket.append(socket(AF_INET, SOCK_STREAM))
            dummyclientsocket[i].connect((dc_ip[i], dc_port))        # Connection established to each dummy client
        send_msg(mainsocket, ['2 \n'])                         # Confirmation message to main client that connection is established
        for i in range(num_dc-1):
            consocket, addr = serversocket.accept()
            connectionsocket.append(consocket)

    # Receiving message to connect to webserver
    rec_msg = receive_msg(mainsocket)
    print(rec_msg)
    if rec_msg[0] == '3':
        clientsocket.connect((web_ip, web_port))                      # Connecting to web server

    # receiving maxlength from main client
    rec_msg = receive_msg(mainsocket).split()
    print(rec_msg)
    if rec_msg[0] == '4':
        max_length = int(rec_msg[1])
    else:                                                           # If max length not received from mainclient then asking from server
        msg = ['SUBMIT\n', host, '1\n', '1\n', '\n']
        send_msg(clientsocket, msg)
        response = receive_msg(clientsocket).split()
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