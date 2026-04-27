import json

from detection_service import DetectionService
from killer import clear_trigger


if __name__ == "__main__":
    clear_trigger()
    service = DetectionService()
    print("fine from jzy", flush=True)
    request_data = service.build_request_from_files("test/img.zip", "test/data.json", batch_id="main")
    print("start detect")
    results = service.handle_request(request_data)
    print("start results", flush=True)
    print(json.dumps(results, ensure_ascii=False, indent=2))
