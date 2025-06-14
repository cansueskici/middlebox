import time
import subprocess
import statistics
import argparse
import math
import select
import re

def read_new_detector_output(detector_proc, timeout=1):
    lines = []
    while True:
        ready, _, _ = select.select([detector_proc.stdout], [], [], timeout)
        if ready:
            line = detector_proc.stdout.readline()
            if not line:
                break
            lines.append(line)
        else:
            break
    return ''.join(lines)

def parse_detector_output(output):
    detected = False
    optimal_bits = 0
    bits_pattern = r"\[DETECTOR\] Using (\d+) LSB bits"
    bits_match = re.search(bits_pattern, output)
    if bits_match:
        detected = True
        optimal_bits = int(bits_match.group(1))

    return detected, optimal_bits


def run_experiment(message, bits, delay, timeout, detector_proc):
    rec_cmd = [
        "docker", "exec", "insec", "python3", "receiver.py",
        "--bits", str(bits), "--timeout", str(timeout)
    ]
    send_cmd = [
        "docker", "exec", "sec", "python3", "sender.py",
        "--bits", str(bits), "--delay", str(delay), "--msg", message
    ]

    rec_proc = subprocess.Popen(rec_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    time.sleep(5) 

    start_time = time.time()
    subprocess.run(send_cmd, check=True)
    rec_stdout, rec_stderr = rec_proc.communicate(timeout=timeout)
    end_time = time.time()
    elapsed_time = end_time - start_time

    detector_output = read_new_detector_output(detector_proc)
    return detector_output, elapsed_time

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
    t = 2.131  
    margin = t * stdev / math.sqrt(n)
    return (mean_val - margin, mean_val + margin)

def main():
    parser = argparse.ArgumentParser(description="Covert Channel Experimentation Campaign (Phase 3)")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--output", type=str, default="experiment_results.txt")
    args = parser.parse_args()

    bits_options = [3, 4, 6, 8, 11, 16]
    msg_options = [
        "Alive 2007, Daft Punk",
        "Submarine is the second studio album by American indie pop band the Marias.",
        "In Rainbows is the seventh studio album by the English rock band Radiohead. The album has 10 songs, making it 42 minutes and 39 seconds long.",
    ]
    delay_options = [0.01, 0.10]

    results = []

    detector_cmd = ["docker", "exec", "tcp-options-processor", "python3", "-u", "main.py"]
    detector_proc = subprocess.Popen(detector_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    with open(args.output, "w") as f:
        f.write("Covert Channel Experiment Results (Phase 3)\n")
        f.write("==========================================\n\n")

    for bits in bits_options:
        for msg in msg_options:
            for delay in delay_options:
                total_bits = len(msg) * 8
                capacities = []
                elapsed_times = []
                correct_detections = []
                detections = []
    
                print(f"\nConfiguration: bits={bits}, message='{msg[:50]}' (length: {len(msg)} bytes), delay={delay:.3f} s")

                for trial in range(args.trials):
                    print(f"Trial {trial + 1}:")
                    try:
                         detector_output, elapsed_time= run_experiment(msg, bits, delay, args.timeout, detector_proc)
                         detected, det_opt_bits = parse_detector_output(detector_output)
                         print(f"Actual Bits: {bits}, Detected Optimal Bits: {det_opt_bits}")
                    except Exception as e:
                        print(f"  Error in trial: {e}")
                        continue

                    capacity = compute_capacity(elapsed_time, total_bits)
                    elapsed_times.append(elapsed_time)
                    capacities.append(capacity)
                    if detected:
                        detections.append(1)
                        if det_opt_bits == bits:
                            correct_detections.append(1)
                        else:
                            correct_detections.append(0)
                    else:
                        detections.append(0)
                        correct_detections.append(0)

                if capacities:
                    avg_elapsed = statistics.mean(elapsed_times)
                    avg_capacity = statistics.mean(capacities)
                    ci_low, ci_high = confidence_interval(capacities)
                    detection_rate = sum(detections) / len(detections) if detections else 0
                    correct_detection_rate = sum(correct_detections) / len(correct_detections) if correct_detections else 0

                    config_result = {
                        "bits": bits,
                        "msg_prefix": msg[:30] + "...",
                        "delay": delay,
                        "msg_length": len(msg),
                        "avg_elapsed": avg_elapsed,
                        "avg_capacity": avg_capacity,
                        "ci_low": ci_low,
                        "ci_high": ci_high,
                        "detection_rate": detection_rate,
                        "correct_detection_rate": correct_detection_rate,
                    }
                    results.append(config_result)

                    line_to_write = (
                        f"Config: bits={config_result['bits']}, delay={config_result['delay']:.2f} s, msg_length={config_result['msg_length']} bytes\n"
                        f"  Avg Elapsed: {config_result['avg_elapsed']:.4f} s, Avg Capacity: {config_result['avg_capacity']:.2f} bits/s, 95% CI: [{config_result['ci_low']:.2f}, {config_result['ci_high']:.2f}] bits/s\n"
                        f"  Detector Detection Rate: {config_result['detection_rate']:.2f}\n"
                        f"  Correct Detection Rate: {config_result['correct_detection_rate']:.2f}\n"
                    )

                    with open(args.output, "a") as f:
                        f.write(line_to_write)
                    print(line_to_write.strip())
                else:
                    print(f"No successful trials for config: bits={bits}, msg_prefix='{msg[:50]}', delay={delay:.2f} s")

    print("\nExperimentation complete! Results saved to", args.output)
    detector_proc.terminate()
    detector_proc.wait()

if __name__ == "__main__":
    main()