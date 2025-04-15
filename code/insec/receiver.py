import socket
import argparse
from functools import partial
from scapy.all import TCP, sniff

covert_message_bits = []
last_timestamp = None

def start_udp_listener():
    # Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Bind the socket to the port
    server_address = ( '', 8888)
    sock.bind(server_address)
    
    print("UDP listener started on port 8888")
    
    while True:
        data, address = sock.recvfrom(4096)
        print(f"Received {len(data)} bytes from {address}")
        print(data.decode())
        data = "Hi SecureNet!".encode()
        if data:
            sent = sock.sendto(data, address)
            print(f"Sent {sent} bytes back to {address}")


def decode_bits_to_message(bit_stream, bits):
    if len(bit_stream) % bits != 0:
        bit_stream += [0] * (bits - len(bit_stream) % bits) # pad with 0s 
    
    chars = []
    for i in range(0, len(bit_stream), bits):
        byte = bit_stream[i:i + bits]
        char = chr(int(''.join(map(str, byte)), 2))
        chars.append(char)
    return ''.join(chars)


def process_packet(packet, bits):
    global covert_message_bits
    global last_timestamp
    if TCP in packet and packet[TCP].options:
        for option in packet[TCP].options:
            if option[0] == "Timestamp":
                timestamp_value = option[1][0]
                # print(f"Received packet with timestamp: {timestamp_value}")

                if timestamp_value == 0:
                    # print("Termination signal received.")
                    message = decode_bits_to_message(covert_message_bits, bits)
                    print(message)
                    exit(0)
                
                if last_timestamp == None:
                    chunk = [(timestamp_value >> (bits - (i+1))) & 1 for i in range(bits)]
                    covert_message_bits.extend(chunk)
                    last_timestamp = timestamp_value
                else:
                    delta = timestamp_value - last_timestamp
                    chunk = [(delta >> (bits- (i+1))) & 1 for i in range(bits)]
                    covert_message_bits.extend(chunk)
                    last_timestamp = timestamp_value

                break


if __name__ == "__main__":
    # start_udp_listener()

    parser = argparse.ArgumentParser(description="Covert Receiver using TCP Timestamps")
    parser.add_argument("--timeout", type=int, default=900,
                        help="Timeout in seconds for sniffing before decoding.")
    parser.add_argument("--bits", type=int, default=8,
                        help="Number of bits encoded per TCP packet.")
    
    args = parser.parse_args()

    try:
        sniff(iface="eth0", filter="tcp and port 1234", prn=partial(process_packet, bits=args.bits), timeout=args.timeout)
    except Exception as e:
        print(f"Error: {e}")


