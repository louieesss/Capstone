"""
dht11_lgpio.py — DHT11 reader using lgpio directly (no RPi.GPIO / blinka)
==========================================================================
Bypasses the adafruit_dht + blinka + RPi.GPIO stack that causes
"GPIO busy" conflicts on Raspberry Pi OS Bookworm.

Usage:
    from dht11_lgpio import read_dht11
    temp_c, humidity = read_dht11(pin=4)   # raises RuntimeError on bad read
"""

import time
import lgpio

_CHIP = 0          # /dev/gpiochip0  (bcm2711 on Pi 4, adjust for Pi 5)
_TIMEOUT_US = 1_000_000   # 1 s safety timeout for pulse counting


def _send_start(h: int, pin: int):
    """Pull pin LOW for 18 ms then release so DHT11 can respond."""
    lgpio.gpio_claim_output(h, pin, 1)   # output, idle HIGH
    time.sleep(0.001)
    lgpio.gpio_write(h, pin, 0)
    time.sleep(0.018)                    # ≥18 ms LOW
    lgpio.gpio_write(h, pin, 1)
    time.sleep(0.00004)                  # 40 µs HIGH
    # Release output NOW — let the pull-up hold the line while we switch to input
    try:
        lgpio.gpio_free(h, pin)
    except lgpio.error:
        pass
    time.sleep(0.00005)                  # 50 µs settle before input claim


def _read_bits(h: int, pin: int) -> list[int]:
    """
    Wait for DHT11 response and sample 40 bits.
    Returns list of 40 ints (0 or 1) or raises RuntimeError on timeout.
    Timeouts are intentionally generous to handle Python scheduling jitter.
    """
    # Pin already freed in _send_start; claim it as input now
    lgpio.gpio_claim_input(h, 0, pin)  # 0 = no flags; DHT11 has external pull-up

    def wait_for(level: int, timeout_us: int = 200) -> bool:
        t0 = time.monotonic_ns()
        while lgpio.gpio_read(h, pin) != level:
            if (time.monotonic_ns() - t0) > timeout_us * 1000:
                return False
        return True

    # DHT11 pulls LOW ~80 µs then HIGH ~80 µs as ready signal
    if not wait_for(0, 250):
        raise RuntimeError('DHT11 no response (start LOW)')
    if not wait_for(1, 250):
        raise RuntimeError('DHT11 no response (start HIGH)')
    if not wait_for(0, 250):
        raise RuntimeError('DHT11 no response (data start)')

    bits = []
    for _ in range(40):
        # Each bit starts with ~50 µs LOW
        if not wait_for(1, 150):
            raise RuntimeError('DHT11 timeout waiting for bit HIGH')
        t0 = time.monotonic_ns()
        if not wait_for(0, 150):
            raise RuntimeError('DHT11 timeout waiting for bit LOW')
        pulse_us = (time.monotonic_ns() - t0) // 1000
        # 0-bit ≈ 26-28 µs HIGH, 1-bit ≈ 70 µs HIGH
        bits.append(1 if pulse_us > 40 else 0)

    return bits


def _bits_to_bytes(bits: list[int]) -> list[int]:
    result = []
    for i in range(0, 40, 8):
        byte = 0
        for b in bits[i:i + 8]:
            byte = (byte << 1) | b
        result.append(byte)
    return result   # [RH_int, RH_dec, T_int, T_dec, checksum]


def read_dht11(pin: int = 4) -> tuple[float, float]:
    """
    Read temperature (°C) and humidity (%RH) from a DHT11 on GPIO *pin*.
    Opens its own lgpio handle, reads once, then releases the pin.
    Raises RuntimeError on CRC mismatch or timeout.
    """
    h = lgpio.gpiochip_open(_CHIP)
    try:
        _send_start(h, pin)
        bits = _read_bits(h, pin)
    finally:
        # gpiochip_close releases all claims automatically.
        # We do NOT call gpio_free here — it can raise 'GPIO not allocated'
        # if the pin state changed during bit-reading and mask the real error.
        try:
            lgpio.gpio_free(h, pin)
        except lgpio.error:
            pass  # already freed or never claimed — safe to ignore
        lgpio.gpiochip_close(h)

    data = _bits_to_bytes(bits)
    checksum = (data[0] + data[1] + data[2] + data[3]) & 0xFF
    if checksum != data[4]:
        raise RuntimeError(
            f'DHT11 CRC fail (got {data[4]:#04x}, expected {checksum:#04x})')

    humidity = data[0] + data[1] / 10.0
    temp_c   = data[2] + data[3] / 10.0
    return round(temp_c, 1), round(humidity, 1)
