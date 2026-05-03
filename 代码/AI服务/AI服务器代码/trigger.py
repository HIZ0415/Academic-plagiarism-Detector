import base64
import os
import pickle
import time

from detection_service import DetectionService
from killer import clear_trigger


def monitor_batch(zip_path, interval=1):
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
            last_mtime = current_mtime
            yield
        time.sleep(interval)


if __name__ == "__main__":
    clear_trigger()
    service = DetectionService()
    target_file = "test/img.zip"
    time.sleep(5)
    print("fine from jzy", flush=True)

    try:
        for _ in monitor_batch(target_file):
            print("start detect")
            request_data = service.build_request_from_files("test/img.zip", "test/data.json", batch_id="trigger")
            results = service.handle_request(request_data)
            result_bytes = pickle.dumps(results)
            print("start results", flush=True)
            print(base64.b64encode(result_bytes).decode("utf-8"), flush=True)
    except KeyboardInterrupt:
        pass
