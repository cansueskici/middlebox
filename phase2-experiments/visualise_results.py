import matplotlib.pyplot as plt
import pandas as pd

def load_data(file_path):
    columns = ["bits", "delay", "msg_length", "avg_elapsed", "avg_capacity", "ci_low", "ci_high"]
    return pd.read_csv(file_path, names=columns)

file_path = "clean_results.txt"
df = load_data(file_path)

fig, ax = plt.subplots(figsize=(10, 6))
for bits in df["bits"].unique():
    subset = df[df["bits"] == bits].sort_values("delay")
    x = subset["delay"]
    y = subset["avg_capacity"]
    yerr = [subset["avg_capacity"] - subset["ci_low"], subset["ci_high"] - subset["avg_capacity"]]
    ax.plot(x[1:-1], y[1:-1], "o-", label=f"Bits: {bits:.2f} s")
    ax.scatter([x.iloc[0], x.iloc[-1]], [y.iloc[0], y.iloc[-1]], color=ax.lines[-1].get_color(), zorder=3)
    ax.errorbar(x, y, yerr=yerr, fmt="o", capsize=5, color=ax.lines[-1].get_color())

ax.set_title("Average Capacity vs Delay for Different Bits", fontsize=14)
ax.set_xlabel("Delay (s)", fontsize=12)
ax.set_ylabel("Average Capacity (bits/s)", fontsize=12)
ax.legend(title="Bits")
ax.grid(True)

fig, ax = plt.subplots(figsize=(10, 6))
for delay in df["delay"].unique():
    subset = df[df["delay"] == delay].sort_values("msg_length")
    x = subset["msg_length"]
    y = subset["avg_capacity"]
    yerr = [subset["avg_capacity"] - subset["ci_low"], subset["ci_high"] - subset["avg_capacity"]]

    ax.plot(x[1:-1], y[1:-1], "o-", label=f"Delay: {delay:.2f} s")
    ax.scatter([x.iloc[0], x.iloc[-1]], [y.iloc[0], y.iloc[-1]], color=ax.lines[-1].get_color(), zorder=3)
    ax.errorbar(x, y, yerr=yerr, fmt="o", capsize=5, color=ax.lines[-1].get_color())


ax.set_title("Average Capacity vs Message Length for Different Delays", fontsize=14)
ax.set_xlabel("Message Length (bytes)", fontsize=12)
ax.set_ylabel("Average Capacity (bits/s)", fontsize=12)
ax.legend(title="Delay")
ax.grid(True)



# Show the plots
plt.tight_layout()
plt.show()