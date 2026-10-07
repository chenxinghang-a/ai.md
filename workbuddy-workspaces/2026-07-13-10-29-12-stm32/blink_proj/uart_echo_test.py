#!/usr/bin/env python3
# 串口回环验证: 蓝Pill USART1 回显程序烧录后, USB-TTL 接 PA9/PA10
# 本脚本经 COM3 发 "hello stm32" 应原样收回
import serial, time, sys

PORT = "COM3"
BAUD = 115200

def main():
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
    except Exception as e:
        print(f"[FAIL] 无法打开 {PORT}: {e}")
        sys.exit(1)
    print(f"[OK] 已打开 {ser.name} @ {BAUD}")
    time.sleep(0.3)
    ser.reset_input_buffer()
    test = b"hello stm32\r\n"
    ser.write(test)
    time.sleep(0.4)
    got = ser.read(64)
    ser.close()
    print(f"发出: {test!r}")
    print(f"收回: {got!r}")
    if test in got:
        print("[PASS] 串口收发正常 -> USB-TTL + 蓝Pill USART1 链路打通")
    else:
        print("[WARN] 未收到预期回显, 检查: TX/RX 是否交叉接(对调), GND 共地, 波特率115200")

if __name__ == "__main__":
    main()
