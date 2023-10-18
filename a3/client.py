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
        global dev_rtt
        dev_rtt = 0.75*dev_rtt + 0.25*abs(time_val - avg_rtt)
        if avg_rtt:
            avg_rtt = 0.875*avg_rtt + 0.125*time_val
        else:
            avg_rtt = time_val
        lock = threading.Lock()
        with lock:
            timeout_time = timeout_multiplier*(avg_rtt + 4*dev_rtt)
        print(time_val, avg_rtt, dev_rtt, timeout_time)
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
        lock = threading.Lock()
        while not start_time[received_index]:
            pass
        if start_time[received_index] != -1:
            modify_rtt(end_time-start_time[received_index])
        if not data_received[received_index]:
            with lock:
                data_received[received_index] = parsed_reply['Data']
                received_packet_num += 1
        else:
            with lock:
                duplicate_packet_num += 1

def send_request():        # Sends request to server
    global requested_packet_num
    # Sending first request
    first_not_ack = 0       # index of first element in window whose data is not received
    while first_not_ack < len(data_received):
        ind = first_not_ack
        count = 0
        while (count < window_size) and (ind < len(data_received)):
            if not data_received[ind]:
                offset = ind*data_per_request
                message = f'Offset: {offset}\nNumBytes: {data_per_request}\n\n'
                start_time_lock = threading.Lock()
                start_time_val = time()
                clientsocket.sendto(message.encode(), server)
                with start_time_lock:
                    if not start_time[ind]:
                        start_time[ind] = start_time_val
                    else:
                        start_time[ind] = -1
                    requested_packet_num += 1
                count += 1
            elif count == 0:
                first_not_ack += 1
            ind += 1
        sleep(timeout_time)

        
    # for ind in range(window_size):
    #     offset = ind*data_per_request
    #     message = f'Offset: {offset}\nNumBytes: {data_per_request}\n\n'
    #     start_time_lock = threading.Lock()
    #     start_time_val = time()
    #     clientsocket.sendto(message.encode(), server)
    #     with start_time_lock:
    #         start_time[ind] = start_time_val
    #         requested_packet_num += 1
    # while first_not_ack < len(data_received):
    #     start_timer = time()
    #     offset = first_not_ack*data_per_request
    #     timeout_time_local = timeout_time
    #     while not data_received[first_not_ack]:
    #         if time() - start_timer > timeout_time_local:      # Timeout
    #             message = f'Offset: {offset}\nNumBytes: {data_per_request}\n\n'
    #             start_time_lock = threading.Lock()
    #             start_time_val = -1
    #             clientsocket.sendto(message.encode(), server)
    #             with start_time_lock:
    #                 start_time[first_not_ack] = start_time_val
    #                 requested_packet_num += 1
    #             start_timer = time()
    #             timeout_time_local *= 2
    #         sleep(timeout_time_local/num_check)
    #     if (first_not_ack + window_size) < len(data_received):       # Sending request for newly transmitted msg
    #         offset = (first_not_ack + window_size)*data_per_request
    #         message = f'Offset: {offset}\nNumBytes: {data_per_request}\n\n'
    #         start_time_lock = threading.Lock()
    #         start_time_val = time()
    #         clientsocket.sendto(message.encode(), server)
    #         with start_time_lock:
    #             start_time[first_not_ack + window_size] = start_time_val
    #             requested_packet_num += 1
    #     first_not_ack += 1

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
server_ip = '127.0.0.1'

server = (server_ip, server_port)

# Creating socket for client
clientsocket = socket(AF_INET, SOCK_DGRAM)

# Fixing Time Period
timeout_multiplier = 5
timeout_time = 0.1
# num_check = 100     # Checks this many times whether data received before time_out
avg_rtt = 0
dev_rtt = 0

# Size of data to be received
data_size = 0
data_per_request = 1448
window_size = 1

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
    ssthresh = 0
    congestion_state = 0        # 0: slow start     1: congestion avoidance
    requested_packet_num = 0
    received_packet_num = 0
    duplicate_packet_num = 0
    squished = 0

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

# Closing Socket
clientsocket.close()