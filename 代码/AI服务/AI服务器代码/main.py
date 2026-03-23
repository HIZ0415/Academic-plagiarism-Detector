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
import multiprocessing as mp

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
        # 生成结果
        return images
        
def read_param():
    with open("test/data.json", "r", encoding="utf-8") as f:
        loaded_data = json.load(f)
        return loaded_data
        
if __name__ == "__main__":
    clear_trigger()
    target_file = "test/img.zip"  # 修改为 ZIP 文件路径
    p = PipelineSingleImage()
    print("fine from jzy", flush=True)
    images = monitor_image(target_file)
    print('start detect')
    p.clear_images()
    p.set_method_parameters(read_param())
    print(len(images))
    p.run_multi_images(images)  # 传递图像列表
    results = p.get_results()
    result_bytes = pickle.dumps(results)
    print('start results', flush=True)
    # print(base64.b64encode(result_bytes).decode('utf-8'), flush=True)