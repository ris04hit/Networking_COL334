import socket

website_ip = "vayu.iitd.ac.in"
port = 9801
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.connect((website_ip, port))

HEADER = 1000  # Define HEADER here

FORMAT = 'utf-8'
DISCONNECT_MESSAGE = "!DISCONNECT"
host_port = 5050
host_ip = "192.168.64.1"
data = ""

def message(msg, Port, IP):
    PORT = Port
    SERVER = IP
    ADDR = (SERVER, PORT)
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(ADDR)
    
    def send(msg):
        line_no = str(msg[0]).encode(FORMAT)
        line_no_length = len(line_no)
        line_no_length = str(line_no_length).encode(FORMAT)
        line_no_length += b' ' * (HEADER - len(line_no_length))
        client.send(line_no_length)
        client.send(line_no)
        
        line = msg[1].encode(FORMAT)
        msg_length = len(line)
        send_length = str(msg_length).encode(FORMAT)
        send_length += b' ' * (HEADER - len(send_length))
        client.send(send_length)
        client.send(line)
        
        feed = client.recv(HEADER).decode(FORMAT)
        
        if feed == DISCONNECT_MESSAGE:
            data_length = int(client.recv(1000).decode(FORMAT))
            data = client.recv(data_length).decode(FORMAT)
            print("Received data:", data)
    
    send(msg)
    print("Close")
    client.close()

sent = set()

print("Hello1")
while True:
    print("Hello2")
    request = "SENDLINE\n"
    server.send(request.encode())
    response = server.recv(64)
    line_data = response.decode().split("\n")
    print(line_data)
    line_no = int(line_data[0])
    if line_no == -1:
        continue
    if line_no in sent:
        if len(line_data) != 3:
            while True:
                response = server.recv(4096).decode().split('\n')
                if len(response) == 2:
                    break
        continue
    line = line_data[1]
    print("Hello3")
    
    print(line)
    if len(line_data) == 3:
        message((line_no, line), host_port, host_ip)
    else:
        while True:
            response = server.recv(500000)
            if not response:
                break
            line_data = response.decode().split("\n")
            if line_no == -1:
                continue
            if len(line_data) == 1:
                line += line_data[0]
            else:
                line += line_data[0]
                break
        message((line_no, line), host_port, host_ip)

server.close()
print(data)
