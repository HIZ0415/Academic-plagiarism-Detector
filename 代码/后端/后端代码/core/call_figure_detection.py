import paramiko
import numpy as np
import pickle
import base64
from scp import SCPClient, SCPException
import os
import sys
import getpass

CONNECT = False

def remote_call(hostname, username, port, password):
    # 初始化SSH客户端
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=hostname, username=username, port=port, password=password)

    # 构建执行命令（确保在同一shell中执行）
    command = "cd /root/autodl-tmp/BUAA_SE_DetectFake && /root/miniconda3/envs/llm/bin/python trigger.py"
    stdin, stdout, stderr = ssh.exec_command(command)

    # 等待远程输出中出现'success'
    success_detected = False
    while True:
        line = stdout.readline()
        if not line:  # EOF，流关闭
            break
        line = line.strip()
        print("远程输出:", line)
        if 'fine from jzy' in line.lower():
            success_detected = True
            break

    if not success_detected:
        err = stderr.read().decode()
        ssh.close()
        if err:
            raise RuntimeError(f"远程执行错误: {err}")
        else:
            raise RuntimeError("远程脚本未返回'success'")
    return stdin, stdout, stderr, ssh  # 返回ssh以保持连接

def remote_monitor(stdout, stderr):
    result_detected = True
    while True:
        line = stdout.readline()
        if not line:  # EOF，流关闭
            err = stderr.read().decode()
            if err:
                raise RuntimeError(f"远程执行错误:{err}")
            break
        line = line.strip()
        print("远程输出:", line)
        if 'start results' in line.lower():
            result_detected = True
            break
    if not result_detected:
        err = stderr.read().decode()
        if err:
            raise RuntimeError(f"远程执行错误: {err}")
        else:
            raise RuntimeError("远程脚本未返回'results'")
    # 获取剩余的输出
    output = stdout.readline()
    # 反序列化结果
    result_bytes = base64.b64decode(output)
    return pickle.loads(result_bytes)

def transfer_image(ssh, local_path, remote_path='/root/autodl-tmp/BUAA_SE_DetectFake/test/'):
    try:
        # 使用现有的SSH连接进行传输
        with SCPClient(ssh.get_transport()) as scp:
            scp.put(local_path, remote_path)
            print(f"成功传输到: {remote_path}")
    except SCPException as e:
        print(f"传输失败: {str(e)}")
    except Exception as e:
        print(f"发生错误: {str(e)}")

ssh = None
if CONNECT:
    host = 'connect.nmb1.seetacloud.com'
    port = 24241
    username = 'root'
    password = "jiitZ48i6Zr+"

    # 建立远程连接并执行命令
    stdin, stdout, stderr, ssh = remote_call(host, username, port, password)

    print('finish remote_call')

import atexit

# 假设 ssh 是全局变量
def close_ssh_connection():
    global ssh
    try:
        if ssh:
            ssh.close()
            print("SSH 连接已关闭")
    except Exception as e:
        print(f"关闭 SSH 连接时发生错误: {e}")

# 注册清理函数
atexit.register(close_ssh_connection)

def reconnect():
    global stdin, stdout, stderr, ssh
    ssh.close()
    stdin, stdout, stderr, ssh = remote_call(host, username, port, password)

def get_result(local_path, json_path):
    # 传输图片
    # 参数是路径，因为能用ssh的现成方法
    global ssh
    transfer_image(ssh, json_path)
    transfer_image(ssh, local_path)

    # 获取处理结果
    try:
        result = remote_monitor(stdout, stderr)
        print("远程调用结果:", result)
    except Exception as e:
        print(f"发生错误: {str(e)}")
        return None
    return result


if __name__ == "__main__":
    # 每次启动服务器，以下参数都要重新设置
    host = 'connect.nmb1.seetacloud.com'
    port = 24241
    username = 'root'
    password = "jiitZ48i6Zr+"

    # 建立远程连接并执行命令
    stdin, stdout, stderr, ssh = remote_call(host, username, port, password)

    # 建立起来连接后，之后只要重复以下步骤就可以得到结果，无需重复建立连接

    # 传输图片
    # 参数是路径，因为能用ssh的现成方法
    local_path = 'img.zip'
    json_path = 'data.json'
    transfer_image(ssh, json_path)
    transfer_image(ssh, local_path)

    # 获取处理结果
    try:
        result = remote_monitor(stdout, stderr)
        print("远程调用结果:", result)
        ssh.close()
    except Exception as e:
        print(f"发生错误: {str(e)}")

    import pickle
    # 保存result
    with open('result_new_llm.pkl', 'wb') as file:
        pickle.dump(result, file)

    # with open('result_new_none_llm.pkl', 'rb') as file:
    #
    #     data_list = pickle.load(file)
    #     print(data_list)