import socket
website_ip = socket.gethostbyname("vayu.iitd.ac.in")
port = 9801
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.connect((website_ip, port))
host_port=5050
host_ip="192.168.64.1"
feed=""
data=""
DISCONNECT_MESSAGE="!DISCONNECT"
HEADER=100
def message(msg, data, Port, IP):

    PORT=Port
    FORMAT='utf-8'
    SERVER=IP
    ADDR=(SERVER, PORT)
    client=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(ADDR)
    def send(msg, data):
        line_no=msg[0].encode(FORMAT)
        line_no_length=len(message)
        line_no_length = str(line_no_length).encode(FORMAT)
        line_no_length +=b' '*(HEADER-len(line_no_length))
        client.send(line_no_length)
        client.send(line_no)
        line=msg[1].encode(FORMAT)
        msg_length=len(line)
        send_length = str(msg_length).encode(FORMAT)
        send_length +=b' '*(HEADER-len(send_length))
        client.send(send_length)
        client.send(line)
        feed=client.recv(HEADER).decode(FORMAT)
        if (feed==DISCONNECT_MESSAGE):
            data_length=int(client.recv(1000).decode(FORMAT))
            data=client.recv(data_length).decide(FORMAT)
            print("MIlgaya", data)
    send(msg, data)
sent=set()
while feed==DISCONNECT_MESSAGE:
    request = "SENDLINE\n"
    server.send(request.encode())
    response = server.recv(1024)
    line_data = response.decode().split("\n")
    line_no = int(line_data[0])
    if line_no==-1:
        continue
    if line_no in sent:
        if len(line_data) != 3:
            while True:
                response = server.recv(4096).decode().split('\n')
                if len(response) == 2:
                    break
        continue
    line=line_data[1]
    print(line)
    if (len(line_data)==3):
        message((line_no,line), data, host_port, host_ip)
        continue
    while True:
        response = server.recv(500000)
        if response==b'':
            break
        line_data = response.decode().split("\n")
        if line_no==-1:
            continue
        if len(line_data) == 1:
            line += line_data[0]
        else:
            line += line_data[0]
            break
    message((line_no,line), data, host_port, host_ip)


server.close() 
print(data)
