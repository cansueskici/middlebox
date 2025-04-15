import time
import numpy as np
import subprocess
import statistics
import argparse
import math

def run_experiment(message, bits, delay, timeout):
    latencies = []
    throughputs = []

    rec_cmd = [
        "docker", "exec", "insec", "python3", "receiver.py",
        "--bits", str(bits), "--timeout", str(timeout)
    ]
    
    send_cmd = [
        "docker", "exec", "sec", "python3", "sender.py",
        "--bits", str(bits),"--delay", str(delay), "--msg", message]

    
    rec_proc = subprocess.Popen(rec_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    time.sleep(2)  

    start_time = time.time()
    subprocess.run(send_cmd, check=True)

    rec_stdout, rec_stderr = rec_proc.communicate(timeout=timeout)

    end_time = time.time()
    elapsed_time = end_time - start_time
    return elapsed_time, rec_stdout

def compute_capacity(elapsed, total_bits):
    return total_bits / elapsed

def confidence_interval(data, confidence=0.95):
    n = len(data)
    if n < 2:
        return (data[0], data[0])
    mean_val = statistics.mean(data)
    stdev = statistics.stdev(data)

    t = 2.131
    margin = t * stdev / math.sqrt(n)
    return (mean_val - margin, mean_val + margin)



def main():
    parser = argparse.ArgumentParser(description="Covert Channel Experimentation Campaign")
    parser.add_argument("--timeout", type=int, default=9000)
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--output", type=str, default="experiment_results.txt")
    args = parser.parse_args()

    bits_options = [7, 8, 16, 25]
    msg_options = [
        "Alive 2007, Daft Punk",                                                                                                                        #
        "Submarine is the second studio album by American indie pop band the Marias.",                                                                  # an ode to the albums i've listened to while working on this project 
        "In Rainbows is the seventh studio album by the English rock band Radiohead. The album has 10 songs, making it 42 minutes and 39 seconds long.",#
        "In Korea, heart surgeon. Number one. Steady hand. One day, Kim Jong Un need new heart. I do operation. But mistake! Kim Jong Un die! SSD very mad! I hide fishing boat, come to America. No English, no food, no money. Darryl give me job. Now I have house, American car and new woman. Darryl save life."
    ]
    delay_options = [0.01, 0.10, 0.15]
    results = []

    for bits in bits_options:
        for msg in msg_options:
            for delay in delay_options:
                total_bits = len(msg) * 8 
                capacities = []
                elapsed_times = []
                print(f"\nConfiguration: bits={bits}, message={msg} (length: {len(msg)} bytes), delay={delay:.2f} s")

                for trial in range(args.trials):
                    print(f"Trial {trial + 1}:")
                    try:
                        elapsed, rec_output = run_experiment(msg, bits, delay ,args.timeout)
                    except subprocess.CalledProcessError as e:
                        print("Error in trial:", e)
                        continue
                
                    capacity = compute_capacity(elapsed, total_bits)
                    elapsed_times.append(elapsed)
                    capacities.append(capacity)
                    
                    # print(f"Elapsed time: {elapsed:.4f} s, Capacity: {capacity:.2f} bits/s")
                    if rec_output.strip() == msg.strip():
                        print(f"Correct Output: {rec_output}")
                    else:
                        print(f"Incorrect Output: {rec_output}")
                if capacities:
                    avg_elapsed = statistics.mean(elapsed_times)
                    avg_capacity = statistics.mean(capacities)
                    print(f"Average Elapsed Time: {avg_elapsed:.4f} s, Average Capacity: {avg_capacity:.2f} bits/s, over {args.trials} trials.")
                    ci_low, ci_high = confidence_interval(capacities)
                    config_result = {
                        "bits": bits,
                        "msg": msg,
                        "delay": delay,
                        "msg_length": len(msg),
                        "avg_elapsed": avg_elapsed,
                        "avg_capacity": avg_capacity,
                        "ci_low": ci_low,
                        "ci_high": ci_high
                    }
                    results.append(config_result)
    
                
    with open(args.output, "w") as f:
        f.write("Covert Channel Experiment Results\n")
        f.write("=================================\n")
        for r in results:
            line = (f"bits: {r['bits']}, delay: {r['delay']:.1f} s, msg_length: {r['msg_length']} bytes, "
                    f"avg_elapsed: {r['avg_elapsed']:.4f} s, "
                    f"avg_capacity: {r['avg_capacity']:.2f} bits/s, "
                    f"95% CI: [{r['ci_low']:.2f}, {r['ci_high']:.2f}] bits/s\n")
            f.write(line)
            print(line.strip())
    
    print("\nExperimentation complete! Results saved to", args.output)

if __name__ == "__main__":
    main()