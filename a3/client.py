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
        parsed_msg['Data'] = data
    return parsed_msg

def retransmit(message: str, received: list, index: int):       # Retransmits message
    while not received[index]:
        clientsocket.sendto(message.encode(), server)
        sleep(time_period)

def ask_size():         # Asking for size
    global data_size
    # message = 'SendSize\n\n'            # For tournament mode
    message = 'SendSize\nReset\n\n'     # For non tournament mode
    received = [False]
    retransmit_thread = threading.Thread(target=retransmit, args = (message, received, 0))
    retransmit_thread.start()
    data = {}
    while 'Size' not in data:
        reply, server_address = clientsocket.recvfrom(1024)
        data = reply_parser(reply.decode())
    lock = threading.Lock()
    with lock:
        received[0] = True
    retransmit_thread.join()
    data_size = int(data['Size'])

def data_receiver():     # Receiver for data
    global received_packet_num
    global duplicate_packet_num
    while received_packet_num != len(data_received):
        message = f'Offset: {data_size}\nNumBytes: {data_per_request}\n\n'
        parsed_reply = {}
        while ('Offset' not in parsed_reply) or ('Data' not in parsed_reply):
            reply, server_address = clientsocket.recvfrom(sys.getsizeof(message) + data_per_request)
            parsed_reply = reply_parser(reply.decode())
        lock = threading.Lock()
        received_offset = int(parsed_reply['Offset'])
        received_index = received_offset//data_per_request
        if not data_received[received_index]:
            with lock:
                data_received[received_index] = reply_parser(reply.decode())['Data']
                received_packet_num += 1
        else:
            duplicate_packet_num += 1

def send_request():        # Sends request to server
    # Sending first request
    first_not_ack = 0       # index of first element in window whose data is not received
    for ind in range(window_size):
        offset = ind*data_per_request
        message = f'Offset: {offset}\nNumBytes: {data_per_request}\n\n'
        clientsocket.sendto(message.encode(), server)
    while first_not_ack < len(data_received):
        start_timer = time()
        offset = first_not_ack*data_per_request
        while not data_received[first_not_ack]:
            if time() - start_timer > time_period:      # Timeout
                message = f'Offset: {offset}\nNumBytes: {data_per_request}\n\n'
                clientsocket.sendto(message.encode(), server)
                start_timer = time()
            sleep(time_period/num_check)
        first_not_ack += 1
        if (first_not_ack + offset) < len(data_received):       # Sending request for newly transmitted msg
            offset = (first_not_ack + offset)*data_per_request
            message = f'Offset: {offset}\nNumBytes: {data_per_request}\n\n'
            clientsocket.sendto(message.encode(), server)

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
    data = {}
    while 'Result' not in data:
        reply, server_address = clientsocket.recvfrom(1024)
        data = reply_parser(reply.decode())
    lock = threading.Lock()
    with lock:
        received[0] = True
    retransmit_thread.join()
    if data['Result'] == 'true':
        result = True
    print(data)

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
time_period = 0.005
num_check = 100     # Checks this many times whether data received before time_out

# Size of data to be received
data_size = 0
data_per_request = 1448
window_size = 1<<5

result = False

while not result:
    # Asking for size
    ask_thread = threading.Thread(target=ask_size)
    ask_thread.start()
    ask_thread.join()
    
    #  Initializing required variables
    data_received = [None for offset in range(0, data_size, data_per_request)]
    window_size = min(window_size, data_size//data_per_request)
    received_packet_num = 0
    duplicate_packet_num = 0

    # Turning on data receiver
    receiver_thread = threading.Thread(target=data_receiver)
    receiver_thread.start()

    # Asking for data
    send_thread = threading.Thread(target=send_request)
    send_thread.start()
    
    # Waiting for threads to finish
    receiver_thread.join()
    send_thread.join()
        
    # Submitting data
    submit_thread = threading.Thread(target=submit_data)
    submit_thread.start()
    submit_thread.join()
    
    print(received_packet_num, duplicate_packet_num)

# Closing Socket
clientsocket.close()