import asyncio
from nats.aio.client import Client as NATS
import os, random
from scapy.all import Ether, TCP, IP
import struct
import time

MAX_UINT32 = 0xFFFFFFFF 

class CovertChannelDetector:
    def __init__(self, bits=8, expected_port=1234):
        self.bits = bits 
        self.expected_port = expected_port
        self.ip_states = {}
        self.lsb_mask = (1 << self.bits) - 1
        self.higher_bits_mask = ~self.lsb_mask & MAX_UINT32

    def analyze_packet(self, packet):
        detected = False
        if TCP in packet and packet[TCP].dport == self.expected_port and packet[TCP].options:
            src_ip = packet[IP].src
            current_packet_time = time.time()

            if src_ip not in self.ip_states:
                self.ip_states[src_ip] = {
                    'last_tsval': None,
                    'last_packet_time': current_packet_time,
                    'consecutive_small_natural_increments': 0
                }
            
            ip_state = self.ip_states[src_ip]

            for option in packet[TCP].options:
                if option[0] == "Timestamp":
                    current_tsval = option[1][0]

                    if current_tsval == 0:
                        print(f"\n[Termination Signal Detected!] from {src_ip}.")
                        if src_ip in self.ip_states:
                            del self.ip_states[src_ip]
                        return True 

                    if ip_state['last_tsval'] is not None:
                        # implement detection logic
                        last_tsval = ip_state['last_tsval']
                        last_packet_time = ip_state['last_packet_time']
                    
                    ip_state['last_tsval'] = current_tsval
                    ip_state['last_packet_time'] = current_packet_time
                    break 
        return detected


async def run():
    nc = NATS()
    detector = CovertChannelDetector()
    nats_url = os.getenv("NATS_SURVEYOR_SERVERS", "nats://nats:4222")
    await nc.connect(nats_url)

    async def message_handler(msg):
        subject = msg.subject
        data = msg.data #.decode()
        #print(f"Received a message on '{subject}': {data}")
        packet = Ether(data)
        # print(packet.show())
        detector.analyze_packet(packet)
        # Publish the received message to outpktsec and outpktinsec
        delay = random.expovariate(1/5e-6)
        await asyncio.sleep(delay)
        if subject == "inpktsec":
            await nc.publish("outpktinsec", msg.data)
        else:
            await nc.publish("outpktsec", msg.data)
   
    # Subscribe to inpktsec and inpktinsec topics
    await nc.subscribe("inpktsec", cb=message_handler)
    await nc.subscribe("inpktinsec", cb=message_handler)

    print("Subscribed to inpktsec and inpktinsec topics")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Disconnecting...")
        await nc.close()

if __name__ == '__main__':
    asyncio.run(run())