import time
import subprocess
import statistics
import argparse
import math
import select
import re

def run_experiment(message, bits, timeout):
    rec_cmd = [
        "docker", "exec", "insec", "python3", "receiver.py",
        "--bits", str(bits), "--timeout", str(timeout)
    ]
    send_cmd = [
        "docker", "exec", "sec", "python3", "sender.py",
        "--bits", str(bits), "--msg", message
    ]

    rec_proc = subprocess.Popen(rec_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    time.sleep(2)

    start_time = time.time()
    subprocess.run(send_cmd, check=True)
    rec_stdout, rec_stderr = rec_proc.communicate(timeout=timeout)
    end_time = time.time()
    elapsed_time = end_time - start_time

    return elapsed_time, rec_stdout

def compute_capacity(elapsed, total_bits):
    if elapsed == 0:
        return 0.0
    return total_bits / elapsed

def confidence_interval(data, confidence=0.95):
    n = len(data)
    if n < 2:
        return (data[0], data[0]) if data else (0.0, 0.0)
    mean_val = statistics.mean(data)
    stdev = statistics.stdev(data)
    t = 2.131  # for n=3, 95% CI
    margin = t * stdev / math.sqrt(n)
    return (mean_val - margin, mean_val + margin)

def main():
    parser = argparse.ArgumentParser(description="Covert Channel Mitigation Experiment")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--output", type=str, default="experiment_mitigation_results.txt")
    args = parser.parse_args()

    bits_options = [3, 4, 6, 8, 11, 16]
    msg_options = [
        "Alive 2007, Daft Punk",
        "Submarine is the second studio album by American indie pop band the Marias.",
        "In Rainbows is the seventh studio album by the English rock band Radiohead. The album has 10 songs, making it 42 minutes and 39 seconds long.",
    ]
    mitigation_coefficients = [0.01, 0.1, 0.2, 0.3, 0.4] 
    results = []

    with open(args.output, "w") as f:
        f.write("Mitigation Experiment Results (Phase 4)\n")
        f.write("==========================================\n\n")

    for mitigation_coef in mitigation_coefficients:
        detector_cmd = [
            "docker", "exec", "tcp-options-processor", "python3", "-u", "main.py",
            "--mitigation_coef", str(mitigation_coef)
        ]
        detector_proc = subprocess.Popen(detector_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for bits in bits_options:
            for msg in msg_options:
                total_bits = len(msg) * 8
                capacities = []
                elapsed_times = []
                receiver_corrects = []

                print(f"\n[MITIGATION] bits={bits}, message='{msg[:50]}' (len={len(msg)}), mitigation_coef={mitigation_coef}")

                for trial in range(args.trials):
                    print(f"Trial {trial + 1}:")
                    try:
                        elapsed_time, rec_output = run_experiment(msg, bits, args.timeout)
                    except Exception as e:
                        print(f"  Error in trial: {e}")
                        continue

                    capacity = compute_capacity(elapsed_time, total_bits)
                    elapsed_times.append(elapsed_time)
                    capacities.append(capacity)

                    if "Decoded Covert Message:" in rec_output:
                        rec_decoded = rec_output.split("Decoded Covert Message:")[-1].strip()
                    else:
                        rec_decoded = rec_output.strip()

                    if rec_decoded.rstrip('\x00').strip() == msg.strip():
                        print(f"Correct Output: {rec_decoded}")
                        receiver_corrects.append(1)
                    else:
                        print(f"Incorrect Output: {rec_decoded}")
                        receiver_corrects.append(0)
                if capacities:
                    avg_elapsed = statistics.mean(elapsed_times)
                    avg_capacity = statistics.mean(capacities)
                    ci_low, ci_high = confidence_interval(capacities)
                    receiver_correct_rate = sum(receiver_corrects) / len(receiver_corrects) if receiver_corrects else 0

                    config_result = {
                        "bits": bits,
                        "msg_prefix": msg[:30] + "...",
                        "mitigation_coef": mitigation_coef,
                        "msg_length": len(msg),
                        "avg_elapsed": avg_elapsed,
                        "avg_capacity": avg_capacity,
                        "ci_low": ci_low,
                        "ci_high": ci_high,
                        "receiver_correct_rate": receiver_correct_rate
                    }
                    results.append(config_result)

                    line_to_write = (
                        f"Config: bits={config_result['bits']}, mitigation_coef={config_result['mitigation_coef']:.2f}, msg_length={config_result['msg_length']} bytes\n"
                        f"  Avg Elapsed: {config_result['avg_elapsed']:.4f} s, Avg Capacity: {config_result['avg_capacity']:.2f} bits/s, 95% CI: [{config_result['ci_low']:.2f}, {config_result['ci_high']:.2f}] bits/s\n"
                        f"  Receiver Message Correct Rate: {config_result['receiver_correct_rate']:.2f}\n"
                    )

                    with open(args.output, "a") as f:
                        f.write(line_to_write)
                    print(line_to_write.strip())
                else:
                    print(f"No successful trials for config: bits={bits}, msg_prefix='{msg[:50]}', mitigation_coef={mitigation_coef}")

        detector_proc.terminate()
    print("\nMitigation experimentation complete! Results saved to", args.output)

if __name__ == "__main__":
    main()