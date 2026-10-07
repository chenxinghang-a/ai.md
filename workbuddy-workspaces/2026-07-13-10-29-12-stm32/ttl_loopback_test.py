#!/usr/bin/env python3
# TTL 回环测试: 把 USB-TTL 的 TX 与 RX 用杜邦线短接后运行本脚本
# 能自发自收 => 芯片正常; 收不到 => 线没短好或芯片异常
import serial, time, sys

PORT = "COM3"        # 设备管理器里看到的口, 不对就改这里
BAUD = 115200

def main():
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
    except Exception as e:
        print(f"[FAIL] 无法打开 {PORT}: {e}")
        sys.exit(1)
    print(f"[OK] 已打开 {ser.name} @ {BAUD}")
    time.sleep(0.2)
    msg = b"HELLO_TTL_123\r\n"
    ser.reset_input_buffer()
    ser.write(msg)
    time.sleep(0.3)
    got = ser.read(len(msg))
    ser.close()
    if got == msg:
        print(f"[PASS] 回环成功! 收到: {got.decode(errors='replace')!r}")
        print("=> 这颗 USB-TTL 芯片 100% 正常, 可直接连单片机串口/烧录")
    else:
        print(f"[WARN] 发出 {msg!r} 但收到 {got!r}")
        print("=> 检查: 1) TX/RX 是否确实短接  2) 波特率是否匹配")

if __name__ == "__main__":
    main()
