from __future__ import annotations

import argparse
import time
from typing import Callable, Dict, List, Tuple

from crc32k import (
	generate_random_data,
	bit_crc32k_msb,
	table_crc32k_msb,
	bit_crc32k_reflected,
	table_crc32k_reflected,
)


def _format_table(rows: List[Tuple[str, float, float]]) -> str:
	# rows: (name, avg_us_per_op, mb_per_s)
	name_w = max(len(r[0]) for r in rows)
	lines = []
	header = f"{'Algorithm'.ljust(name_w)}  {'avg μs/op'.rjust(10)}  {'MB/s'.rjust(8)}"
	lines.append(header)
	for name, avg_us, mbps in rows:
		lines.append(f"{name.ljust(name_w)}  {avg_us:10.2f}  {mbps:8.1f}")
	return "\n".join(lines)


def run(trials: int, bits: int, seed: int | None) -> None:
	# Pre-generate all messages to ensure identical workload for each algorithm
	messages = [generate_random_data(bits, seed=(seed + i if seed is not None else None)) for i in range(trials)]
	total_bytes = len(messages[0]) * trials

	algorithms: Dict[str, Callable[[bytes], int]] = {
		"bitwise_msb": bit_crc32k_msb,
		"table_msb": table_crc32k_msb,
		"bitwise_reflected": bit_crc32k_reflected,
		"table_reflected": table_crc32k_reflected,
	}

	results: List[Tuple[str, float, float]] = []
	crc_results: List[Tuple[str, int]] = []

	print(f"Message: {bits} bits ({len(messages[0])} bytes), trials: {trials}")

	for name, func in algorithms.items():
		start = time.perf_counter()
		crc_last = 0
		for msg in messages:
			crc_last = func(msg)
		elapsed = time.perf_counter() - start
		avg_us = (elapsed / trials) * 1e6
		mbps = (total_bytes / (1024 * 1024)) / elapsed if elapsed > 0 else float("inf")
		results.append((name, avg_us, mbps))
		crc_results.append((name, crc_last))

	print(_format_table(results))
	# Print individual CRCs
	for name, value in crc_results:
		print(f"{name.ljust(24)} CRC: 0x{value:08X}")
	# Check agreement
	ref = crc_results[0][1]
	all_equal = all(v == ref for _, v in crc_results)
	if all_equal:
		print(f"All algorithms agree on CRC: 0x{ref:08X}")
	else:
		print("Mismatch detected among algorithms:")
		for name, value in crc_results:
			match = "OK " if value == ref else "ERR"
			print(f"  {match} {name}: 0x{value:08X} (ref 0x{ref:08X})")


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Benchmark CRC-32K algorithms")
	parser.add_argument("--trials", type=int, default=10000, help="number of experiments (default: 10000)")
	parser.add_argument("--bits", type=int, default=1000, help="message length in bits (default: 1000)")
	parser.add_argument("--seed", type=int, default=12345, help="base RNG seed (default: 12345)")
	return parser.parse_args()


if __name__ == "__main__":
	args = parse_args()
	run(trials=args.trials, bits=args.bits, seed=args.seed)


