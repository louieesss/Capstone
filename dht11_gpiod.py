"""
dht11_gpiod.py — DHT11 reader using the gpiod v2 Python API
=============================================================
Compatible with Raspberry Pi OS Bookworm + kernel 6.x.
Replaces the lgpio-based implementation that fails with
"GPIO busy" or "unexpected error" on newer kernels.

Usage:
    from dht11_gpiod import read_dht11
    temp_c, humidity = read_dht11(pin=27)   # raises RuntimeError on bad read
"""

import time
import gpiod
from gpiod.line import Direction, Value, Bias

_CHIP   = '/dev/gpiochip0'
_ACTIVE = Value.ACTIVE      # HIGH
_INACTIVE = Value.INACTIVE  # LOW


def _claim_output(pin: int, initial: Value = _ACTIVE):
    """Request pin as output with given initial level."""
    return gpiod.request_lines(
        _CHIP,
        consumer='dht11',
        config={pin: gpiod.LineSettings(
            direction=Direction.OUTPUT,
            output_value=initial,
        )}
    )


def _claim_input(pin: int):
    """Request pin as input (no internal pull — DHT11 has external pull-up)."""
    return gpiod.request_lines(
        _CHIP,
        consumer='dht11',
        config={pin: gpiod.LineSettings(
            direction=Direction.INPUT,
            bias=Bias.DISABLED,
        )}
    )


def read_dht11(pin: int = 27) -> tuple[float, float]:
    """
    Read temperature (°C) and humidity (%RH) from a DHT11 on BCM GPIO *pin*.
    Raises RuntimeError on timeout or CRC mismatch (common — retry 2-3 times).
    """

    # ── 1. Send start signal: pull LOW for 20 ms, then release HIGH ──────────
    req = _claim_output(pin, initial=_ACTIVE)
    time.sleep(0.001)                    # settle at HIGH
    req.set_value(pin, _INACTIVE)        # pull LOW
    time.sleep(0.020)                    # ≥18 ms LOW
    req.set_value(pin, _ACTIVE)          # release → HIGH
    req.release()

    # ── 2. Switch to input and let DHT11 respond ──────────────────────────────
    # The transition from output to input takes a few µs with gpiod;
    # DHT11 holds the line HIGH for 20-40 µs before responding, so timing is OK.
    req = _claim_input(pin)

    def wait_for(level: Value, timeout_us: int) -> int:
        """Spin-wait for pin to reach *level*. Returns elapsed µs or -1 on timeout."""
        deadline = time.monotonic_ns() + timeout_us * 1_000
        while req.get_value(pin) != level:
            if time.monotonic_ns() >= deadline:
                return -1
        return (deadline - time.monotonic_ns()) // 1_000   # remaining µs (unused but harmless)

    try:
        # DHT11 response: ~80 µs LOW → ~80 µs HIGH → data
        if wait_for(_INACTIVE, 250) < 0:
            raise RuntimeError('DHT11 no response: expected LOW after start')
        if wait_for(_ACTIVE, 250) < 0:
            raise RuntimeError('DHT11 no response: expected HIGH after LOW')
        if wait_for(_INACTIVE, 250) < 0:
            raise RuntimeError('DHT11 no response: expected data start LOW')

        # Read 40 bits
        bits = []
        for bit_n in range(40):
            # Each bit: ~50 µs LOW then HIGH whose length encodes 0 or 1
            if wait_for(_ACTIVE, 150) < 0:
                raise RuntimeError(f'DHT11 timeout on bit {bit_n} HIGH edge')
            t0 = time.monotonic_ns()
            if wait_for(_INACTIVE, 150) < 0:
                raise RuntimeError(f'DHT11 timeout on bit {bit_n} LOW edge')
            pulse_us = (time.monotonic_ns() - t0) // 1_000
            # 0-bit ≈ 26-28 µs HIGH,  1-bit ≈ 70 µs HIGH
            bits.append(1 if pulse_us > 40 else 0)

    finally:
        req.release()

    # ── 3. Decode bytes ───────────────────────────────────────────────────────
    data = []
    for i in range(0, 40, 8):
        byte = 0
        for b in bits[i:i + 8]:
            byte = (byte << 1) | b
        data.append(byte)
    # data = [RH_int, RH_dec, T_int, T_dec, checksum]

    checksum = (data[0] + data[1] + data[2] + data[3]) & 0xFF
    if checksum != data[4]:
        raise RuntimeError(
            f'DHT11 CRC fail (calc {checksum:#04x} vs recv {data[4]:#04x})')

    humidity = round(data[0] + data[1] / 10.0, 1)
    temp_c   = round(data[2] + data[3] / 10.0, 1)
    return temp_c, humidity
