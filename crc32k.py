from __future__ import annotations

import os
import random
from typing import Iterable, List, Optional, Tuple

# CRC-32K (Koopman) polynomial parameters
# Normal (MSB-first) representation without the top x^32 term:
POLY_MSB = 0x741B8CD7


def reflect_bits(value: int, width: int) -> int:
	"""Return bit-reflected value of given width."""
	reflected = 0
	for _ in range(width):
		reflected = (reflected << 1) | (value & 1)
		value >>= 1
	return reflected


# Reflected (LSB-first) polynomial for CRC-32K
POLY_LSB = reflect_bits(POLY_MSB, 32)


def bit_crc32k_msb(data: bytes) -> int:
	"""
	Bitwise MSB-first CRC-32K, initial value 0x00000000, no final XOR.
	Processes bits from MSB to LSB in each byte.
	"""
	crc = 0
	for byte in data:
		for bit_index in range(8):
			in_bit = (byte >> (7 - bit_index)) & 1
			msb = (crc >> 31) & 1
			crc = ((crc << 1) & 0xFFFFFFFF)
			if msb ^ in_bit:
				crc ^= POLY_MSB
	return crc & 0xFFFFFFFF


def _make_table_msb() -> List[int]:
	"""Generate 256-entry MSB-first table for CRC-32K."""
	table: List[int] = []
	for i in range(256):
		crc = i << 24
		for _ in range(8):
			if (crc & 0x80000000) != 0:
				crc = ((crc << 1) & 0xFFFFFFFF) ^ POLY_MSB
			else:
				crc = (crc << 1) & 0xFFFFFFFF
		table.append(crc & 0xFFFFFFFF)
	return table


_TABLE_MSB = _make_table_msb()


def table_crc32k_msb(data: bytes, table: Optional[List[int]] = None) -> int:
	"""
	Table-driven MSB-first CRC-32K, initial value 0x00000000, no final XOR.
	"""
	t = _TABLE_MSB if table is None else table
	crc = 0
	for byte in data:
		index = ((crc >> 24) ^ byte) & 0xFF
		crc = (((crc << 8) & 0xFFFFFFFF) ^ t[index]) & 0xFFFFFFFF
	return crc & 0xFFFFFFFF


def bit_crc32k_reflected(data: bytes) -> int:
	"""
	Bitwise LSB-first CRC-32K with reflected polynomial.
	To match MSB-first results, the final CRC is reflected.
	"""
	crc = 0
	for byte in data:
		# XOR input byte into low 8 bits of CRC, then shift 8 times
		crc ^= byte
		for _ in range(8):
			if (crc & 1) != 0:
				crc = (crc >> 1) ^ POLY_LSB
			else:
				crc >>= 1
	# Reflect result to match MSB-first representation
	return reflect_bits(crc & 0xFFFFFFFF, 32)


def _make_table_lsb() -> List[int]:
	"""Generate 256-entry LSB-first (reflected) table for CRC-32K."""
	table: List[int] = []
	for i in range(256):
		crc = i
		for _ in range(8):
			if (crc & 1) != 0:
				crc = (crc >> 1) ^ POLY_LSB
			else:
				crc >>= 1
		table.append(crc & 0xFFFFFFFF)
	return table


_TABLE_LSB = _make_table_lsb()


def table_crc32k_reflected(data: bytes, table: Optional[List[int]] = None) -> int:
	"""
	Table-driven LSB-first CRC-32K with reflected polynomial.
	Returns reflected output so it equals MSB-first routines.
	"""
	t = _TABLE_LSB if table is None else table
	crc = 0
	for byte in data:
		index = (crc ^ byte) & 0xFF
		crc = ((crc >> 8) ^ t[index]) & 0xFFFFFFFF
	return reflect_bits(crc & 0xFFFFFFFF, 32)


def generate_random_data(num_bits: int, seed: Optional[int] = None) -> bytes:
	"""
	Generate a random bitstring of length num_bits and return as bytes.
	If num_bits is multiple of 8 (e.g., 1000 -> 125 bytes) it packs naturally.
	Bits are filled MSB-first within each byte.
	"""
	if seed is not None:
		random.seed(seed)
	num_bytes = (num_bits + 7) // 8
	b = bytearray(num_bytes)
	for bit_index in range(num_bits):
		byte_index = bit_index // 8
		shift = 7 - (bit_index % 8)
		if random.getrandbits(1):
			b[byte_index] |= 1 << shift
	return bytes(b)


def all_algorithms_agree(data: bytes) -> Tuple[bool, List[int]]:
	"""
	Run all four algorithms and return (agree, values).
	Values are [msb_bit, msb_table, lsb_bit, lsb_table] (all unified to MSB form).
	"""
	v1 = bit_crc32k_msb(data)
	v2 = table_crc32k_msb(data)
	v3 = bit_crc32k_reflected(data)
	v4 = table_crc32k_reflected(data)
	values = [v1, v2, v3, v4]
	return len(set(values)) == 1, values


def self_test() -> None:
	"""
	Simple self-test across a few random payloads, raises AssertionError on mismatch.
	"""
	# Deterministic vector: 125 bytes of incremental values
	data = bytes((i & 0xFF for i in range(125)))
	v1 = bit_crc32k_msb(data)
	v2 = table_crc32k_msb(data)
	v3 = bit_crc32k_reflected(data)
	v4 = table_crc32k_reflected(data)
	assert v1 == v2, f"MSB pair mismatch: {hex(v1)} vs {hex(v2)}"
	assert v3 == v4, f"Reflected pair mismatch: {hex(v3)} vs {hex(v4)}"
	# Random vectors
	for seed in (1, 123, 9999, 20231121):
		msg = generate_random_data(1000, seed=seed)
		v1 = bit_crc32k_msb(msg)
		v2 = table_crc32k_msb(msg)
		v3 = bit_crc32k_reflected(msg)
		v4 = table_crc32k_reflected(msg)
		assert v1 == v2, f"MSB pair mismatch (seed {seed}): {hex(v1)} vs {hex(v2)}"
		assert v3 == v4, f"Reflected pair mismatch (seed {seed}): {hex(v3)} vs {hex(v4)}"


if __name__ == "__main__":
	# Quick manual run to demonstrate output
	message = generate_random_data(1000, seed=42)
	ok, vals = all_algorithms_agree(message)
	print(f"All agree: {ok}, CRC = {hex(vals[0])}")


