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

def modify_rtt(time_val: float):        # Changes time parameters of program
    def temp_modify_rtt(time_val: float):
        global timeout_time
        global avg_rtt
        if avg_rtt:
            avg_rtt = 0.875*avg_rtt + 0.125*time_val
        else:
            avg_rtt = time_val
        lock = threading.Lock()
        with lock:
            timeout_time = timeout_multiplier*avg_rtt
        rtt_log.write(f'{time()-first_req_time}\t{time_val}\t{avg_rtt}\n')       # Writing log file
    rtt_thread = threading.Thread(target=temp_modify_rtt, args=(time_val,))
    rtt_thread.start()
    rtt_thread.join()

def retransmit(message: str, received: list):       # Retransmits message
    while not received[0]:
        clientsocket.sendto(message.encode(), server)
        sleep(timeout_time)

def ask_size():         # Asking for size
    global data_size
    # message = 'SendSize\n\n'            # For tournament mode
    message = 'SendSize\nReset\n\n'     # For non tournament mode
    received = [False]
    retransmit_thread = threading.Thread(target=retransmit, args = (message, received))
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
    global squished
    global window_size
    while received_packet_num != len(data_received):
        message = f'Offset: {data_size}\nNumBytes: {data_per_request}\n\n'
        parsed_reply = {}
        while ('Offset' not in parsed_reply) or ('Data' not in parsed_reply):
            reply, server_address = clientsocket.recvfrom(sys.getsizeof(message) + data_per_request)
            end_time = time()
            parsed_reply = reply_parser(reply.decode())
        if 'Squished' in parsed_reply:
            lock_squish = threading.Lock()
            with lock_squish:
                squished += 1
        received_offset = int(parsed_reply['Offset'])
        received_index = received_offset//data_per_request
        receive_log.write(f'{end_time-first_req_time}\t{received_offset}\n')
        while not start_time[received_index]:
            pass
        if start_time[received_index] != -1:
            modify_rtt(end_time-start_time[received_index])
        lock = threading.Lock()
        if not data_received[received_index]:
            unique_receive_log.write(f'{end_time-first_req_time}\t{received_offset}\n')
            with lock:
                data_received[received_index] = parsed_reply['Data']
                received_packet_num += 1
                window_size += 1/int(window_size)       # Increasing window size due to low congestion
                window_log.write(f'{end_time-first_req_time}\t{window_size}\n')
        else:
            duplicate_receive_log.write(f'{end_time-first_req_time}\t{received_offset}\n')
            with lock:
                duplicate_packet_num += 1

def send_request():        # Sends request to server
    global requested_packet_num
    global window_size
    first_not_ack = 0       # index of first element in window whose data is not received
    max_sent = -1           # packet with index max_sent is the packet requested with max index till now
    while first_not_ack < len(data_received):
        ind = first_not_ack
        count = 0
        while (count < int(window_size)) and (ind < len(data_received)):        # Sending requests in burst of window_size
            if not data_received[ind]:
                offset = ind*data_per_request
                message = f'Offset: {offset}\nNumBytes: {data_per_request}\n\n'
                start_time_lock = threading.Lock()
                start_time_val = time()
                clientsocket.sendto(message.encode(), server)
                sent_log.write(f'{start_time_val-first_req_time}\t{offset}\n')      # Writing log file
                with start_time_lock:
                    if not start_time[ind]:
                        start_time[ind] = start_time_val
                    else:
                        start_time[ind] = -1
                    requested_packet_num += 1
                count += 1
                if ind <= max_sent:
                    window_lock = threading.Lock()
                    with window_lock:
                        window_size = max(1, window_size/2)
                        window_log.write(f'{start_time_val-first_req_time}\t{window_size}\n')
                max_sent = max(max_sent, ind)
            elif count == 0:
                first_not_ack += 1
            ind += 1
        sleep(timeout_time)

def submit_data():      # Submit data
    global result
    data = ''.join(data_received)[:data_size]
    md5_hash = hashlib.md5()
    md5_hash.update(data.encode())
    md5_hex = md5_hash.hexdigest()
    message = f'Submit: {user}\nMD5: {md5_hex}\n\n'
    received = [False]
    retransmit_thread = threading.Thread(target=retransmit, args = (message, received))
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

# Vayu Server*
server_ip = '10.17.7.134'
server_port = int(sys.argv[1])

# Local Server
# server_ip = '127.0.0.1'

server = (server_ip, server_port)

# Creating socket for client
clientsocket = socket(AF_INET, SOCK_DGRAM)

# Fixing Time Period
timeout_multiplier = 7      # use 4 for constant vayu server, use 8 for local server, 7 for variable vayu server
timeout_time = 0.1
avg_rtt = 0

# Size of data to be received
data_size = 0
data_per_request = 1448
window_size = 10

# Log files
rtt_log = open('log/rtt.txt', 'w')
sent_log = open('log/sent.txt', 'w')
receive_log = open('log/receive.txt', 'w')
unique_receive_log = open('log/unique.txt', 'w')
duplicate_receive_log = open('log/duplicate.txt', 'w')
window_log = open('log/window.txt', 'w')

result = False

while not result:
    # Asking for size
    ask_thread = threading.Thread(target=ask_size)
    ask_thread.start()
    ask_thread.join()
    
    #  Initializing required variables
    data_received = [None for offset in range(0, data_size, data_per_request)]
    start_time = [None for offset in range(0, data_size, data_per_request)]
    window_size = min(window_size, len(data_received))
    window_log.write(f'0\t{window_size}\n')
    requested_packet_num = 0
    received_packet_num = 0
    duplicate_packet_num = 0
    squished = 0
    first_req_time = time()

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
    
    print(f'Requested Packets:\t\t{requested_packet_num}\nReceived Packets:\t\t{received_packet_num}\nDuplicate Packets:\t\t{duplicate_packet_num}\nSquished Packets:\t\t{squished}\nTime Period:\t\t\t{timeout_time}')

# Closing Log files
rtt_log.close()
sent_log.close()
receive_log.close()
unique_receive_log.close()
duplicate_receive_log.close()
window_log.close()

# Closing Socket
clientsocket.close()