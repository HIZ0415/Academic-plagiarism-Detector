import os
import sys
import json
import time
from PIL import Image
import numpy as np
from pipeline.pipeline_single_image import PipelineSingleImage
import pickle
import base64
import zipfile
from io import BytesIO
from killer import clear_trigger

def monitor_image(zip_path, interval=1, retries=100000, retry_interval=0.5):
    """
    监控指定 ZIP 文件的修改，并在修改完成后读取其中一级目录下的所有图片文件，
    将其转换为 NumPy 数组列表并返回。

    参数：
        zip_path (str): ZIP 文件路径
        interval (int): 轮询间隔时间（秒）
        retries (int): 读取失败时的最大重试次数
        retry_interval (float): 重试间隔时间（秒）

    返回：
        generator: 生成包含多个图片数据的 NumPy 数组列表
    """
    last_mtime = None

    while True:
        try:
            current_mtime = os.path.getmtime(zip_path)
        except FileNotFoundError:
            time.sleep(interval)
            continue

        if last_mtime is None:
            last_mtime = current_mtime
            time.sleep(interval)
            continue

        if current_mtime != last_mtime:
            success = False
            for attempt in range(retries):
                try:
                    with zipfile.ZipFile(zip_path) as zip_file:
                        images = []
                        for zip_info in zip_file.infolist():
                            # 排除子目录中的文件
                            if '/' in zip_info.filename:
                                continue
                            # 检查扩展名是否是图片
                            if not zip_info.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                                continue
                            # 读取文件并转换为 NumPy 数组
                            data = zip_file.read(zip_info)
                            img = Image.open(BytesIO(data))
                            img_array = np.array(img)
                            images.append(img_array)
                        # 更新时间戳
                        last_mtime = os.path.getmtime(zip_path)
                        # 生成结果
                        yield images
                        success = True
                        break
                except Exception as e:
                    print(f"Error reading ZIP file: {e}")
                    time.sleep(retry_interval)
            if not success:
                print("Failed to read ZIP file after multiple retries.")
        time.sleep(interval)
        
def read_param():
    with open("test/data.json", "r", encoding="utf-8") as f:
        loaded_data = json.load(f)
        return loaded_data
        
if __name__ == "__main__":
    clear_trigger()
    target_file = "test/img.zip"  # 修改为 ZIP 文件路径
    p = PipelineSingleImage()
    time.sleep(5)
    print("fine from jzy", flush=True)

    try:
        for images in monitor_image(target_file):
            print('start detect')
            p.clear_images()
            p.set_method_parameters(read_param())
            p.run_multi_images(images)  # 传递图像列表
            results = p.get_results()
            result_bytes = pickle.dumps(results)
            print('start results', flush=True)
            print(base64.b64encode(result_bytes).decode('utf-8'), flush=True)
    except KeyboardInterrupt:
        pass