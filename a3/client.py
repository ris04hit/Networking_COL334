from socket import *
from time import time, sleep
import threading
import sys
import hashlib

def reply_parser(message: str):     # Converts server reply into dictionary
    # Uses FSM
    state = 'key'
    key = ''
    value = ''
    data = ''
    parsed_msg = {}
    index = 0
    while index < len(message):
        if state == 'key':
            if message[index] == ':':
                state = 'value'
                value = ''
                index += 1
            elif message[index] == '\n':
                state = 'init'
                parsed_msg[key] = ''
            else:
                key += message[index]
        elif state == 'value':
            if message[index] == '\n':
                state = 'init'
                parsed_msg[key] = value
            else:
                value += message[index]
        elif state == 'init':
            if message[index] == '\n':
                state = 'data'
            else:
                state = 'key'
                key = message[index]
                value = ''
        else:
            data += message[index]
        index += 1
    if data:
        parsed_msg['data'] = data
    return parsed_msg

def ask_size():         # Asking for size
    global data_size
    # message = 'SendSize\n\n'            # For tournament mode
    message = 'SendSize\nReset\n\n'     # For non tournament mode
    received = [False]
    retransmit_thread = threading.Thread(target=retransmit, args = (message, received, 0))
    retransmit_thread.start()
    reply, server_address = clientsocket.recvfrom(1024)
    lock = threading.Lock()
    with lock:
        received[0] = True
    data = reply_parser(reply.decode())
    data_size = int(data['Size'])

def request_data(offset: int, num_bytes: int):          # Request data for given offset and num_bytes
    message = f'Offset: {offset}\nNumBytes: {num_bytes}\n\n'
    index = offset//data_per_request
    retransmit_thread = threading.Thread(target=retransmit, args = (message, data_received, index))
    retransmit_thread.start()
    reply, server_address = clientsocket.recvfrom(sys.getsizeof(message) + num_bytes)
    lock = threading.Lock()
    parsed_reply = reply_parser(reply.decode())
    try:
        received_offset = int(parsed_reply['Offset'])
    except:
        print(parsed_reply)
    received_index = received_offset//data_per_request
    with lock:
        data_received[received_index] = reply_parser(reply.decode())['data']

def submit_data():      # Submit data
    global result
    data = ''.join(data_received)[:data_size]
    md5_hash = hashlib.md5()
    md5_hash.update(data.encode())
    md5_hex = md5_hash.hexdigest()
    message = f'Submit: {user}\nMD5: {md5_hex}\n\n'
    received = [False]
    retransmit_thread = threading.Thread(target=retransmit, args = (message, received, 0))
    retransmit_thread.start()
    reply, server_address = clientsocket.recvfrom(1024)
    lock = threading.Lock()
    with lock:
        received[0] = True
    data = reply_parser(reply.decode())
    if data['Result'] == 'true':
        result = True
    print(data)

def retransmit(message: str, received: list, index: int):       # Retransmits message
    time_pause = time_period
    while not received[index]:
        clientsocket.sendto(message.encode(), server)
        sleep(time_pause)
        time_pause += time_period

# Submitting user
user = '2021CS10547@nothing'

# Vayu Server
server_ip = '10.237.26.109'
server_port = int(sys.argv[1])

# Local Server
server_ip = '127.0.0.1'

server = (server_ip, server_port)

# Creating socket for client
clientsocket = socket(AF_INET, SOCK_DGRAM)

# Fixing Time Period
time_period = 0.004

# Size of data to be received
data_size = 0
data_per_request = 1448

result = False

while not result:
    # Asking for size
    ask_thread = threading.Thread(target=ask_size)
    ask_thread.start()
    ask_thread.join()

    # Asking for data
    data_received = [None for offset in range(0, data_size, data_per_request)]
    window_size = (data_size//data_per_request)
    thread_list = [threading.Thread(target=request_data, args=(offset, data_per_request)) for offset in range(0, data_size, data_per_request)]
    for thread in thread_list:
        thread.start()
        sleep(time_period)
    for thread in thread_list:
        thread.join()
        
    # Submitting data
    submit_thread = threading.Thread(target=submit_data)
    submit_thread.start()
    submit_thread.join()

# Closing Socket
clientsocket.close()