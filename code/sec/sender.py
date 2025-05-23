import os
import socket
import time
import argparse
import random
from scapy.all import IP, TCP, send

MAX_UINT32 = 0xFFFFFFFF

def udp_sender():
    host = os.getenv('INSECURENET_HOST_IP')
    port = 8888
    message = "Hello, InSecureNet!"

    if not host:
        print("SECURENET_HOST_IP environment variable is not set.")
        return

    try:
        # Create a UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        while True:
            # Send message to the server
            sock.sendto(message.encode(), (host, port))
            print(f"Message sent to {host}:{port}")

            # Receive response from the server
            response, server = sock.recvfrom(4096)
            print(f"Response from server: {response.decode()}")

            # Sleep for 1 second
            time.sleep(1)

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        sock.close()

def encode_message_to_bits(message, bits):
    bit_stream = ''.join(format(ord(char), f'0{bits}b') for char in message)
    return [int(bit) for bit in bit_stream]

def send_covert_message(message, bits, packet_delay):
    dst_ip = os.getenv("INSECURENET_HOST_IP")
    dst_port = 1234 
    bit_stream = encode_message_to_bits(message, 8) 

    padding= (bits - (len(bit_stream) % bits)) % bits
    padded_message_bits = bit_stream + [0] * padding

    print(f"Sending covert message: '{message}' with {bits} bits per packet.")
    # print(f"Total bits to send (including padding): {len(padded_message_bits)}")

    current_ts_counter = random.randint(0, MAX_UINT32)

    for i in range(0, len(padded_message_bits), bits):
        chunk = padded_message_bits[i : i + bits]
        covert_value = int(''.join(map(str, chunk)), 2)
        current_ts_counter = (current_ts_counter + random.randint(1, 100)) & MAX_UINT32 

        mask = ~((1 << bits) - 1) & MAX_UINT32 
        modified_tsval = (current_ts_counter & mask) | covert_value

        modified_tsval = modified_tsval & MAX_UINT32

        # print(f"Original TSval (counter): {current_ts_counter} ({bin(current_ts_counter)})")
        # print(f"Covert chunk: {chunk} ({covert_value})")
        # print(f"Modified TSval: {modified_tsval} ({bin(modified_tsval)})")

        packet = IP(dst=dst_ip) / TCP(dport=dst_port, flags='PA', options=[("Timestamp", (modified_tsval, 0))])
        send(packet, verbose=0)
        time.sleep(packet_delay)

    termination_tsval = 0 
    # print(f"Sending termination signal (TSval: {termination_tsval}).")
    packet = IP(dst=dst_ip) / TCP(dport=dst_port, flags='PA', options=[("Timestamp", (termination_tsval, 0))])
    send(packet, verbose=0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Covert Sender")
    parser.add_argument("--msg", type=str, default="Hello InsecureNet!")
    parser.add_argument("--bits", type=int, default=4,
                        help="Number of least significant bits (LSBs) to use for covert data.")
    parser.add_argument("--delay", type=float, default=0.01, 
                        help="Constant delay between sending covert packets (in seconds).")
    args = parser.parse_args()

    send_covert_message(args.msg, args.bits, args.delay)