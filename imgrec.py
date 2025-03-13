#!/usr/bin/env python3
from PIL import Image, ImageEnhance
import pytesseract
import os
import subprocess
import tempfile
import queue
import time
import concurrent.futures
from pyfiglet import Figlet
from colorama import Fore, Style, init

init(autoreset=True)

# 支持的文件格式
SUPPORTED_FORMATS = ('.jpg', '.png', '.bmp', '.bpg')
DEFAULT_LANG = 'eng'
cache = {}  # 缓存已识别的结果
result_queue = queue.Queue()  # 用于存储识别结果

def display_welcome():
    f = Figlet(font='slant')
    print(Fore.CYAN + f.renderText('OCR Tool'))
    print(Fore.YELLOW + "=" * 60)
    print(Fore.GREEN + "欢迎使用图像内容识别程序（运行于 Linux）")
    print(Fore.GREEN + "支持格式：jpg, png, bmp, bpg")
    print(Fore.GREEN + "功能：支持批量识别、缓存、多线程处理")
    print(Fore.YELLOW + "=" * 60)
    print(Fore.MAGENTA + "示例：/home/user/image.jpg 或文件夹路径，输入 'quit' 退出")
    print(Fore.YELLOW + "=" * 60)

def convert_bpg_to_png(image_path):
    try:
        # 检查 bpgdec 是否安装
        subprocess.run(['bpgdec', '-h'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except FileNotFoundError:
        print(Fore.RED + "错误：bpgdec 未安装。请安装 BPG 工具。")
        return None
    except subprocess.CalledProcessError:
        print(Fore.RED + "错误：bpgdec 运行失败。")
        return None

    # 创建临时 PNG 文件
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_png:
        temp_png_path = temp_png.name
        try:
            subprocess.run(['bpgdec', '-o', temp_png_path, image_path], check=True)
            return temp_png_path
        except subprocess.CalledProcessError:
            print(Fore.RED + f"错误：{image_path} BPG 文件转换失败。")
            return None

def recognize_image_content(image_path, lang=DEFAULT_LANG):
    """识别单个图像的内容"""
    try:
        # 检查文件格式
        if not image_path.lower().endswith(SUPPORTED_FORMATS):
            result_queue.put(f"{image_path} - 错误：仅支持 jpg, png, bmp, bpg 格式")
            return
        
        # 检查缓存
        if image_path in cache:
            result_queue.put(f"{image_path} - 从缓存中读取：\n{cache[image_path]}")
            return

        # 处理 BPG 文件
        temp_png_path = None
        if image_path.lower().endswith('.bpg'):
            temp_png_path = convert_bpg_to_png(image_path)
            if not temp_png_path:
                result_queue.put(f"{image_path} - 错误：BPG 处理失败")
                return
            img_path = temp_png_path
        else:
            img_path = image_path

        # 图像处理和内容识别
        try:
            img = Image.open(img_path).convert('L')  # 转换为灰度图
            img = ImageEnhance.Contrast(img).enhance(2.0)  # 增强对比度
            text = pytesseract.image_to_string(img, lang=lang)  # OCR 识别
            
            if text.strip():
                result_queue.put(f"{image_path} - 识别结果：\n{text}")
                cache[image_path] = text
            else:
                result_queue.put(f"{image_path} - 未识别到任何文本内容")
        finally:
            # 删除临时文件
            if temp_png_path:
                os.remove(temp_png_path)
                
    except FileNotFoundError:
        result_queue.put(f"{image_path} - 错误：找不到文件")
    except PermissionError:
        result_queue.put(f"{image_path} - 错误：无权限访问文件")
    except pytesseract.TesseractNotFoundError:
        result_queue.put(f"{image_path} - 错误：Tesseract OCR 未安装")
    except Exception as e:
        result_queue.put(f"{image_path} - 发生错误：{str(e)}")

def process_images(image_paths, lang=DEFAULT_LANG):
    """多线程处理图像"""
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(recognize_image_content, path, lang) for path in image_paths]
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(Fore.RED + f"处理图像时发生错误：{e}")

def display_results():
    """显示识别结果"""
    while not result_queue.empty():
        print(Fore.BLUE + result_queue.get())
        print(Fore.YELLOW + "-" * 50)

def main():
    display_welcome()
    
    while True:
        user_input = input(Fore.CYAN + "请输入图像路径或文件夹（输入 'quit' 退出）：").strip().strip("'\"")
        if user_input.lower() == 'quit':
            print(Fore.YELLOW + "程序已退出")
            break

        lang = input(Fore.CYAN + "请输入识别语言（默认 'eng'）：").strip() or DEFAULT_LANG
        image_paths = []

        # 处理输入是文件夹还是单个文件
        if os.path.isdir(user_input):
            for root, _, files in os.walk(user_input):
                for file in files:
                    if file.lower().endswith(SUPPORTED_FORMATS):
                        image_paths.append(os.path.join(root, file))
        elif os.path.isfile(user_input):
            image_paths.append(user_input)
        else:
            print(Fore.RED + "错误：输入路径无效")
            continue

        if not image_paths:
            print(Fore.RED + "没有找到支持的图像文件")
            continue

        print(Fore.GREEN + f"开始处理 {len(image_paths)} 个图像文件...")
        start_time = time.time()
        
        # 多线程处理图像
        process_images(image_paths, lang)
        
        # 显示结果
        display_results()
        
        print(Fore.GREEN + f"处理完成，耗时 {time.time() - start_time:.2f} 秒")

if __name__ == "__main__":
    main()