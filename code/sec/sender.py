import os
import socket
import time
import argparse
from scapy.all import IP, TCP, send


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

def send_covert_message(dst_ip, dst_port, message, bits, delay):
    bit_stream = encode_message_to_bits(message, bits)
    padding = bits - (len(bit_stream) % bits) if len(bit_stream) % bits != 0 else 0
    bit_stream += [0] * padding
    timestamp_value = 0

    for i in range(0, len(bit_stream), bits):
        chunk = bit_stream[i:i + bits]

        for index, bit in enumerate(chunk):
            if bit == 1:
                timestamp_value += 2 ** (bits-(index+1))

        # print(f"Sending chunk: {chunk} (timestamp: {timestamp_value})")
        packet = IP(dst=dst_ip) / TCP(dport=dst_port, flags='PA', options=[("Timestamp", (timestamp_value, 0))])
        send(packet, verbose=0)
        time.sleep(delay)

    termination_signal = 0
    # print(f"Sending termination signal: {termination_signal}")
    packet = IP(dst=dst_ip) / TCP(dport=dst_port, flags='PA', options=[("Timestamp", (termination_signal, 0))])
    send(packet, verbose=0)


if __name__ == "__main__":
    # udp_sender()

    parser = argparse.ArgumentParser(description="Covert Sender")
    parser.add_argument("--msg", type=str, default="Hello InsecureNet!")
    parser.add_argument("--bits", type=int, default=8)
    parser.add_argument("--delay", type=float, default=0.0)
    args = parser.parse_args()

    dst_ip = os.getenv("INSECURENET_HOST_IP")
    dst_port = 1234    

    send_covert_message(dst_ip, dst_port, args.msg, args.bits, args.delay)

