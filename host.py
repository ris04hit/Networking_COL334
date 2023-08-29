import socket
import threading
#Host server binding
host_port=5050
host_server=socket.gethostbyname(socket.gethostname())
ADDR=(host_server, host_port)
server=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(ADDR)

HEADER=64
FORMAT = 'utf-8'
DISCONNECT_MESSAGE='!DISCONNECT'

#Vayu server connecting
website_ip = socket.gethostbyname("vayu.iitd.ac.in")
port = 9801
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((website_ip, port))
lines = {}

def handle_client(conn, addr):
    print(f"[NEW_CONNECTION] {addr} connected")
    connected=True
    while connected:
        line_no_length=conn.recv(HEADER).decode(FORMAT)
        if (line_no_length):
            line_no_length=int(line_no_length)  
            line_no=int(conn.recv(line_no_length).decode(FORMAT))
            line_length=conn.recv(HEADER).decode(FORMAT)
            line_length=int(line_length)  
            line=conn.recv(line_length).decode(FORMAT)
            if (line_no not in lines):
                lines[line_no]=line
            if (len(lines)==1000):
                data="\n".join(lines)
                conn.send(DISCONNECT_MESSAGE.encode(FORMAT))
                conn.send(str(len(lines)).encode(FORMAT))
                conn.send(data.encode(FORMAT))
                connected=False
            else:
                conn.send("more".encode(FORMAT))
    conn.close()


def start():
    server.listen()
    print(f"[LISTENING] Server is listening on {host_server}") 
    while True:
        conn, addr= server.accept()
        thread=threading.Thread(target=handle_client, args=(list,conn, addr))
        thread.start()
        print(f"[ACTIVE CONNECTIONS] {threading.activeCount()-1}")


while len(lines) != 1000:
    request = "SENDLINE\n"
    client_socket.send(request.encode())
    response = client_socket.recv(1024)
    line_data = response.decode().split("\n")
    line_no = int(line_data[0])
    if line_no==-1:
        continue
    if line_no in lines:
        if len(line_data) != 3:
            while True:
                response = client_socket.recv(4096).decode().split('\n')
                if len(response) == 2:
                    break
        continue
    line=line_data[1]
    if (len(line_data)==3):
        lines[line_no]=line
        continue
    while True:
        response = client_socket.recv(500000)
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
    lines[line_no]=line
client_socket.close() 
print(lines)