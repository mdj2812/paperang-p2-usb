#!/usr/bin/env python3
"""
Paperang P2 USB 打印机控制脚本
基于 https://github.com/hurui200320/java-paperang-p2-usb 协议实现
支持: 文字打印、图片打印、二维码打印、测试图案、热力密度调节
作者: OpenClaw
"""

import usb.core
import usb.util
import struct
import zlib
import sys
import os
import argparse
import random
from PIL import Image, ImageDraw, ImageFont

# Paperang P2 USB ID
VENDOR_ID = 0x4348
PRODUCT_ID = 0x5584
CRC_SEED = 0x35769521 & 0xffffffff

# 打印宽度 (参考 Java 项目: PAPERANG_P2_PRINT_BIT_PER_LINE = 576)
PRINT_WIDTH = 576  # 像素 (72 bytes/line * 8)
LINE_BYTES = 72    # 每行字节数
MAX_PACKET_DATA = 1023  # 最大单包数据长度


def crc32_paperang(data, seed=CRC_SEED):
    """
    Paperang 专用 CRC32 计算
    使用 seed = 0x35769521 (与标准 CRC32 的 0x00000000 不同)
    """
    crc = zlib.crc32(data, seed) & 0xffffffff
    # 转换为有符号 32 位整数
    if crc > 2147483647:
        crc = crc - 4294967296
    return crc


def pack_packet(cmd, data=b'', packet_remain=0):
    """
    打包 Paperang 协议数据包
    格式: [0x02] [CMD:1B] [packetRemain:1B] [dataLength:2B LE] [DATA:0-1023B] [CRC32:4B LE] [0x03]
    
    Args:
        cmd: 命令字节
        data: 数据内容
        packet_remain: 剩余包数量 (0 表示这是最后一包)
    """
    crc = crc32_paperang(data)
    packet = bytearray()
    packet.append(0x02)                           # 包头
    packet.append(cmd & 0xFF)                     # 命令 (1字节)
    packet.append(packet_remain & 0xFF)           # 剩余包数 (1字节)
    packet.extend(struct.pack('<H', len(data)))   # 数据长度 (2字节小端)
    packet.extend(data)                           # 数据 (0-1023字节)
    packet.extend(struct.pack('<i', crc))         # CRC32 (4字节小端有符号)
    packet.append(0x03)                           # 包尾
    return bytes(packet)


class PaperangP2:
    def __init__(self):
        self.dev = None
        self.ep_out = None
        self.ep_in = None
        
    def connect(self):
        """连接打印机"""
        self.dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
        if self.dev is None:
            raise RuntimeError("未找到 Paperang P2 打印机")
        
        # 分离内核驱动
        if self.dev.is_kernel_driver_active(0):
            self.dev.detach_kernel_driver(0)
        
        # 设置配置
        self.dev.set_configuration()
        cfg = self.dev.get_active_configuration()
        intf = cfg[(0, 0)]
        
        # 查找端点
        self.ep_out = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
        )
        self.ep_in = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
        )
        
        return True
    
    def send(self, cmd, data=b''):
        """发送命令"""
        packet = pack_packet(cmd, data)
        self.dev.write(self.ep_out.bEndpointAddress, packet)
        return True
    
    def send_multi_packet(self, cmd, data):
        """
        发送多包数据 (用于打印大数据)
        按照 Paperang 协议分包，每包最多 1023 字节数据
        """
        total_len = len(data)
        offset = 0
        packet_idx = 0
        
        while offset < total_len:
            # 计算剩余包数
            remaining = total_len - offset
            current_packet_data_len = min(MAX_PACKET_DATA, remaining)
            next_offset = offset + current_packet_data_len
            packets_remain = (total_len - next_offset + MAX_PACKET_DATA - 1) // MAX_PACKET_DATA
            
            chunk = data[offset:next_offset]
            packet = pack_packet(cmd, chunk, packets_remain)
            self.dev.write(self.ep_out.bEndpointAddress, packet)
            
            offset = next_offset
            packet_idx += 1
        
        return True
    
    def feed(self, lines=100):
        """走纸 (命令 0x1A)"""
        return self.send(0x1A, struct.pack('<H', lines))
    
    def set_heat_density(self, density=75):
        """
        设置热力密度/打印浓度 (命令 0x19)
        范围: 0-100 (0=最浅, 100=最深)
        默认 75 是较好的平衡点
        """
        if density < 0:
            density = 0
        if density > 100:
            density = 100
        return self.send(0x19, struct.pack('<H', density))
    
    def set_paper_type(self, paper_type=0):
        """设置纸张类型 (0=普通, 1=连续)"""
        return self.send(0x2C, bytes([paper_type]))
    
    def print_test_page(self):
        """打印测试页"""
        return self.send(0x1B)
    
    def get_status(self):
        """获取状态"""
        self.send(0x0C)
        try:
            resp = self.dev.read(self.ep_in.bEndpointAddress, 64, timeout=1000)
            return resp
        except:
            return None
    
    def get_battery(self):
        """获取电量"""
        self.send(0x10)
        try:
            resp = self.dev.read(self.ep_in.bEndpointAddress, 64, timeout=1000)
            return resp
        except:
            return None
    
    def print_bitmap(self, bitmap_data, width_bytes=72):
        """打印位图数据 (按行分包，参考 Java 项目)"""
        # 每包包含的行数: 1023 / 72 = 14 行
        lines_per_packet = MAX_PACKET_DATA // width_bytes  # 14
        
        total_bytes = len(bitmap_data)
        total_lines = total_bytes // width_bytes
        
        # 计算总包数
        total_packets = (total_lines + lines_per_packet - 1) // lines_per_packet
        
        offset = 0
        line_offset = 0
        packet_idx = 0
        
        while offset < total_bytes:
            # 计算当前包包含的行数
            remaining_lines = total_lines - line_offset
            current_lines = min(lines_per_packet, remaining_lines)
            current_bytes = current_lines * width_bytes
            
            # 计算剩余包数 (当前包发送后还剩多少包)
            packet_idx += 1
            remaining_packets = total_packets - packet_idx
            
            chunk = bitmap_data[offset:offset + current_bytes]
            packet = pack_packet(0x00, chunk, remaining_packets)
            self.dev.write(self.ep_out.bEndpointAddress, packet)
            
            offset += current_bytes
            line_offset += current_lines
        
        return True
    
    def print_image(self, image_path, heat_density=75, feed_before=50, feed_after=300):
        """
        打印图片文件
        
        Args:
            image_path: 图片路径
            heat_density: 热力密度 0-100 (默认75)
            feed_before: 打印前走纸量 (默认50)
            feed_after: 打印后走纸量 (默认300)
        """
        # 打开图片
        img = Image.open(image_path)
        
        # 调整宽度为 576 像素
        if img.width != PRINT_WIDTH:
            ratio = PRINT_WIDTH / img.width
            new_height = int(img.height * ratio)
            img = img.resize((PRINT_WIDTH, new_height), Image.LANCZOS)
        
        # 转为灰度然后二值化 (如果还不是1-bit)
        if img.mode != '1':
            img = img.convert('L')
            img = img.point(lambda x: 0 if x < 128 else 255, '1')
        
        # 转为位图数据 (参考 Java 项目的 toByteArrays())
        # 按行打包: 每行 72 字节，每个字节的 8 位代表 8 个水平像素
        # bitPos = 7 - (x % 8), 即 MSB 在左
        width_bytes = PRINT_WIDTH // 8  # 72
        height = img.height
        
        # 按行打包数据
        data = bytearray()
        for y in range(height):
            row = bytearray(width_bytes)
            for x in range(PRINT_WIDTH):
                if img.getpixel((x, y)) == 0:  # 黑点
                    byte_pos = x // 8
                    bit_pos = 7 - (x % 8)  # MSB 在左
                    row[byte_pos] |= (1 << bit_pos)
            data.extend(row)
        
        # 打印流程 (参考 Java 项目)
        self.set_paper_type(0)           # 设置普通纸张
        self.set_heat_density(heat_density)  # 设置热力密度
        self.feed(feed_before)           # 打印前走纸
        self.print_bitmap(bytes(data), width_bytes)  # 发送打印数据
        self.feed(feed_after)            # 打印后走纸
        return True
    
    def print_text(self, text, font_size=24, heat_density=75):
        """打印文字"""
        # 尝试加载字体 (优先使用支持中英文的字体)
        font_paths = [
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
            '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',
            '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
            '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        ]
        font = None
        for fp in font_paths:
            if os.path.exists(fp):
                font = ImageFont.truetype(fp, font_size)
                break
        if font is None:
            font = ImageFont.load_default()
        
        # 计算尺寸
        lines = text.split('\n')
        max_width = 0
        total_height = 0
        line_heights = []
        
        for line in lines:
            bbox = font.getbbox(line)
            w = bbox[2] - bbox[0] if bbox else len(line) * font_size // 2
            # 使用 bbox[3] 作为高度（包含基线下方的空间）
            h = bbox[3] if bbox else font_size
            max_width = max(max_width, w)
            line_heights.append(h + 4)
            total_height += h + 4
        
        # 创建图像 (宽度必须是 576，高度必须是 8 的倍数)
        img_width = PRINT_WIDTH  # 576
        img_height = ((total_height + 20 + 7) // 8) * 8  # 向上取整到 8 的倍数
        img = Image.new('1', (img_width, img_height), 1)
        draw = ImageDraw.Draw(img)
        
        # 绘制文字
        y = 10
        for i, line in enumerate(lines):
            draw.text((10, y), line, font=font, fill=0)
            y += line_heights[i]
        
        # 保存临时文件并打印
        tmp_path = '/tmp/paperang_text.png'
        img.save(tmp_path)
        return self.print_image(tmp_path, heat_density=heat_density)
    
    def print_qr(self, content, box_size=10, heat_density=75):
        """打印二维码"""
        try:
            import qrcode
        except ImportError:
            print("请先安装 qrcode: pip3 install qrcode[pil]")
            return False
        
        qr = qrcode.QRCode(version=1, box_size=box_size, border=2)
        qr.add_data(content)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # 居中放置
        qr_size = min(img.width, PRINT_WIDTH - 40)
        img = img.resize((qr_size, qr_size), Image.NEAREST)
        
        canvas = Image.new('1', (PRINT_WIDTH, qr_size + 20), 1)
        offset_x = (PRINT_WIDTH - qr_size) // 2
        canvas.paste(img, (offset_x, 10))
        
        tmp_path = '/tmp/paperang_qr.png'
        canvas.save(tmp_path)
        return self.print_image(tmp_path, heat_density=heat_density)
    
    def print_pattern_test(self):
        """
        打印测试图案 (参考 UsbPatternTest.kt)
        用于测试: 行长度、每行点数、每列点数、多包传输
        """
        width_bytes = LINE_BYTES  # 48 bytes = 384 dots
        
        # 创建测试图案数据
        data = bytearray()
        
        # 1. 测试行长度 - 每 8 字节打印一列
        # 打印 8 列，每列 8 字节宽
        for _ in range(50):  # 50 行
            row = bytearray(width_bytes)
            for col in range(8):  # 8 列
                start_byte = col * 6  # 每列 6 字节 (48/8=6)
                for b in range(6):
                    row[start_byte + b] = 0xFF
            data.extend(row)
        
        # 2. 测试每行点数 - 交替图案 10101010
        for _ in range(50):
            row = bytearray(width_bytes)
            for b in range(width_bytes):
                row[b] = 0xAA  # 10101010
            data.extend(row)
        
        # 3. 测试每列点数 - 竖线
        for _ in range(50):
            row = bytearray(width_bytes)
            for b in range(width_bytes):
                row[b] = 0x81  # 10000001 - 两边有竖线
            data.extend(row)
        
        # 4. 随机数据测试多包传输
        for _ in range(100):
            row = bytearray(width_bytes)
            for b in range(width_bytes):
                row[b] = random.randint(0, 255)
            data.extend(row)
        
        # 打印流程
        self.set_paper_type(0)
        self.set_heat_density(75)
        self.feed(50)
        self.print_bitmap(bytes(data), width_bytes)
        self.feed(300)
        return True
    
    def print_heat_density_test(self):
        """
        打印热力密度测试 (参考 UsbHeatDensityTest.kt)
        展示不同热力密度下的打印效果
        """
        width_bytes = LINE_BYTES
        
        densities = [0, 25, 50, 75, 100]
        
        for density in densities:
            # 设置热力密度
            self.set_heat_density(density)
            
            # 打印密度标记条
            data = bytearray()
            
            # 顶部空白
            for _ in range(20):
                data.extend(bytearray(width_bytes))
            
            # 实心块
            for _ in range(30):
                row = bytearray(width_bytes)
                for b in range(width_bytes):
                    row[b] = 0xFF
                data.extend(row)
            
            # 底部空白
            for _ in range(20):
                data.extend(bytearray(width_bytes))
            
            self.print_bitmap(bytes(data), width_bytes)
            self.feed(50)
        
        # 恢复默认密度
        self.set_heat_density(75)
        self.feed(300)
        return True


def main():
    parser = argparse.ArgumentParser(description='Paperang P2 打印机控制')
    parser.add_argument('-t', '--text', help='打印文字')
    parser.add_argument('-i', '--image', help='打印图片')
    parser.add_argument('-q', '--qr', help='打印二维码')
    parser.add_argument('-f', '--font-size', type=int, default=24, help='字体大小')
    parser.add_argument('-d', '--density', type=int, default=75, help='热力密度 0-100 (默认75)')
    parser.add_argument('--test', action='store_true', help='打印测试页')
    parser.add_argument('--pattern-test', action='store_true', help='打印图案测试 (测试行/列/多包)')
    parser.add_argument('--density-test', action='store_true', help='打印热力密度测试')
    parser.add_argument('--status', action='store_true', help='获取打印机状态')
    parser.add_argument('--battery', action='store_true', help='获取电量')
    
    args = parser.parse_args()
    
    printer = PaperangP2()
    
    try:
        printer.connect()
        
        if args.test:
            printer.print_test_page()
        elif args.pattern_test:
            printer.print_pattern_test()
        elif args.density_test:
            printer.print_heat_density_test()
        elif args.status:
            status = printer.get_status()
            print(f"状态: {status}")
        elif args.battery:
            battery = printer.get_battery()
            print(f"电量: {battery}")
        elif args.text:
            printer.print_text(args.text, font_size=args.font_size, heat_density=args.density)
        elif args.image:
            printer.print_image(args.image, heat_density=args.density)
        elif args.qr:
            printer.print_qr(args.qr, heat_density=args.density)
        else:
            # 默认打印测试文字
            test_text = """Paperang P2 测试打印
==================
打印机工作正常！

时间: """ + os.popen('date "+%Y-%m-%d %H:%M:%S"').read().strip()
            printer.print_text(test_text, heat_density=args.density)
        
        print("打印完成!")
        return 0
        
    except Exception as e:
        print(f"错误: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
