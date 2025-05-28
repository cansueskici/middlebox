import socket
import argparse
from functools import partial
from scapy.all import TCP, sniff

covert_message_bits = []
last_timestamp = 21081527

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

def decode_bits_to_message(bit_stream):
    
    if len(bit_stream) % 8 != 0:
        bit_stream += [0] * (8 - len(bit_stream) % 8) 
    
    chars = []
    for i in range(0, len(bit_stream), 8):
        byte = bit_stream[i:i + 8]
        char = chr(int(''.join(map(str, byte)), 2))
        chars.append(char)
    return ''.join(chars)


def process_packet(packet, covert_bits_count):
    global covert_message_bits
    
    if TCP in packet and packet[TCP].options:
        for option in packet[TCP].options:
            if option[0] == "Timestamp":
                timestamp_value = option[1][0]
                # print(f"Received packet with timestamp: {timestamp_value}")

                if timestamp_value == 0:
                    # print("\nTermination signal received.")
                    # message = decode_bits_to_message(covert_message_bits)
                    # print(f"Decoded Covert Message: {message}")
                    exit(0)
            
                extracted_value = timestamp_value & ((1 << covert_bits_count) - 1)
                chunk_bits_str = format(extracted_value, f'0{covert_bits_count}b')
                chunk = [int(bit) for bit in chunk_bits_str]
                covert_message_bits.extend(chunk)
                
                # print(f"Extracted chunk ({covert_bits_count} bits): {chunk}")
                break 


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Covert Receiver using TCP Timestamps")
    parser.add_argument("--timeout", type=int, default=900,
                        help="Timeout in seconds for sniffing before decoding.")
    parser.add_argument("--bits", type=int, default=4, 
                        help="Number of least significant bits used for covert data.")
    
    args = parser.parse_args()

    try:
        sniff(iface="eth0", filter="tcp and port 1234", prn=partial(process_packet, covert_bits_count=args.bits), timeout=args.timeout)
    except Exception as e:
        print(f"Error during sniffing: {e}")
    finally:
        if covert_message_bits:
            # print("\nSniffing stopped (timeout or manual stop). Attempting to decode received bits.")
            # print("Raw covert bits received:", ''.join(map(str, covert_message_bits)))
            message = decode_bits_to_message(covert_message_bits)
            print(message)
        else:
            print("No covert messages received.")
