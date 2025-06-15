import asyncio 
from nats.aio.client import Client as NATS 
import os, random 
from scapy.all import Ether, TCP
from collections import deque 
import math 
import argparse

class CovertChannelDetector: 
    def __init__(self, entropy_threshold=0.3): 
        self.entropy_threshold = entropy_threshold 
        self.timestamp_buffer = deque(maxlen=1000)  
        self.packet_count = 0 
        self.detection_active = False 

    def calculate_entropy(self, values): 
        if not values or len(values) < 2: 
            return 0.0 

        freq_map = {} 
        for val in values: 
            freq_map[val] = freq_map.get(val, 0) + 1 

        total = len(values) 
        entropy = 0.0 

        for count in freq_map.values(): 
            if count > 0: 
                prob = count / total 
                entropy -= prob * math.log2(prob) 

        return entropy 

    def extract_lsb_bits(self, timestamps, num_bits): 
        mask = (1 << num_bits) - 1 
        return [ts & mask for ts in timestamps]    

    def detect_covert_channel(self, timestamps): 
        entropies = [] 

        for bits in range(1, 17): 
            lsb_values = self.extract_lsb_bits(timestamps, bits) 
            entropy = self.calculate_entropy(lsb_values) 
            entropies.append(entropy) 
    
        optimal_bits = 1 
        for i in range(1, len(entropies)): 
            entropy_increase = entropies[i] - entropies[i-1] 

            if entropy_increase < self.entropy_threshold: 
                optimal_bits = i 
                break 

            optimal_bits = i + 1 

        expected_entropy = optimal_bits  
        actual_entropy = entropies[optimal_bits - 1] 
        entropy_ratio = actual_entropy / expected_entropy if expected_entropy > 0 else 0 

        print(f"[DETECTOR] Optimal bits: {optimal_bits}, Entropy ratio: {entropy_ratio:.4f}") 

        is_covert = entropy_ratio < 0.9 and optimal_bits > 1

        if is_covert: 
            # print(f"[DETECTOR] COVERT CHANNEL DETECTED!") 
            print(f"[DETECTOR] Using {optimal_bits} LSB bits")  

        return is_covert, optimal_bits
 
    def process_packet(self, packet, mitigation_coef=0.01): 
        if not (TCP in packet and packet[TCP].options): 
            return 

        for i, option in enumerate(packet[TCP].options): 
            if option[0] == "Timestamp": 
                tsval = option[1][0]   

                # --mitigation--
                print(mitigation_coef)
                if random.random() < mitigation_coef:
                    n = random.randint(0, 4)
                    mitigated_tsval = tsval & ~((1 << n) - 1)
                    ops = list(packet[TCP].options)
                    ops[i] = ("Timestamp", (mitigated_tsval, option[1][1]))
                    packet[TCP].options = ops
               
                # --------------

                if tsval == 0: 
                    print(f"[DETECTOR] Termination signal detected (TSval=0)") 
                    timestamps = list(self.timestamp_buffer) 
                    is_covert, bits= self.detect_covert_channel(timestamps) 
                    if is_covert: 
                        print(f"[DETECTOR] *** COVERT CHANNEL ALERT ***") 

                    self.timestamp_buffer.clear() 
                    self.packet_count = 0 
                    self.detection_active = False 
                    return 

                self.timestamp_buffer.append(tsval) 
                self.packet_count += 1 
                self.detection_active = True 

                if self.packet_count % 50 == 0: 
                    print(f"[DETECTOR] Collected {self.packet_count} packets with timestamps") 
                break 

async def run(mitigation_coef=0.01): 
    nc = NATS() 
    nats_url = os.getenv("NATS_SURVEYOR_SERVERS", "nats://nats:4222") 
    await nc.connect(nats_url) 

    async def message_handler(msg): 
        subject = msg.subject 
        data = msg.data 

        try: 
            packet = Ether(data) 
            detector.process_packet(packet, mitigation_coef) 
            delay = random.expovariate(1/5e-6) 
            await asyncio.sleep(delay) 

            if subject == "inpktsec": 
                await nc.publish("outpktinsec", bytes(packet)) 
            else: 
                await nc.publish("outpktsec", msg.data) 

        except Exception as e: 
            print(f"[DETECTOR] Error processing packet: {e}") 
            if subject == "inpktsec": 
                await nc.publish("outpktinsec", msg.data) 
            else: 
                await nc.publish("outpktsec", msg.data) 

    await nc.subscribe("inpktsec", cb=message_handler) 
    await nc.subscribe("inpktinsec", cb=message_handler) 

    print("[DETECTOR] Subscribed to inpktsec and inpktinsec topics") 
    print("[DETECTOR] Monitoring for covert channels in TCP timestamps...") 

    try: 
        while True: 
            await asyncio.sleep(1) 

    except KeyboardInterrupt: 
        print("[DETECTOR] Disconnecting...") 
        await nc.close() 

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Detector")
    parser.add_argument("--entropy", type=float, default=0.2,
                        help="Entropy threshold for covert channel detection.")
    
    parser.add_argument("--mitigation_coef", type=float, default=0.01,
                        help="Mitigation coefficient.")

    args = parser.parse_args()
    detector = CovertChannelDetector(entropy_threshold=args.entropy)
    asyncio.run(run(mitigation_coef=args.mitigation_coef)) 