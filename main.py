from __future__ import annotations

from crc32k import (
	bit_crc32k_msb,
	table_crc32k_msb,
	bit_crc32k_reflected,
	table_crc32k_reflected,
	generate_random_data,
)


def main() -> None:
	# As per the task: K = 1000 bits
	data = generate_random_data(1000, seed=12345)

	c1 = bit_crc32k_msb(data)
	c2 = table_crc32k_msb(data)
	c3 = bit_crc32k_reflected(data)
	c4 = table_crc32k_reflected(data)

	print(f"Message length: {len(data) * 8} bits ({len(data)} bytes)")
	print(f"bitwise_msb       : 0x{c1:08X}")
	print(f"table_msb         : 0x{c2:08X}")
	print(f"bitwise_reflected : 0x{c3:08X}")
	print(f"table_reflected   : 0x{c4:08X}")
	print(f"MSB pair equal       : {c1 == c2}")
	print(f"Reflected pair equal : {c3 == c4}")
	print(f"Families equal (MSB vs Reflected): {c1 == c3}")


if __name__ == "__main__":
	main()


