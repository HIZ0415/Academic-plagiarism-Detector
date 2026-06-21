# -*- coding: utf-8 -*-
"""Execute remaining Task-2 cases: 6.3-2, 6.4-5/6, 6.5-3/5."""
from __future__ import annotations

import io
import json
import os
import sys
import time
from pathlib import Path

import requests

BASE = os.environ.get("TEST_API_BASE", "http://127.0.0.1:8000")
BACKEND = Path(__file__).resolve().parents[2] / "代码" / "后端" / "后端代码"
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fake_image_detector.local_settings")

import django

django.setup()

from django.contrib.auth import get_user_model
from core.models import DetectionTask, Organization

User = get_user_model()
RESULTS: dict[str, dict] = {}


def login(email: str, password: str, role: str | None = None) -> str:
    body = {"email": email, "password": password}
    if role:
        body["role"] = role
    r = requests.post(f"{BASE}/api/login/", json=body, timeout=30)
    r.raise_for_status()
    return r.json()["access"]


def hdr(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_6_3_2(pub_token: str) -> None:
    """Cross-user manual review: publisher A applies for publisher B's task."""
    org = Organization.objects.first()
    pub_a = User.objects.get(email="publisher_test@example.com")
    pub_b, created = User.objects.get_or_create(
        email="publisher_b_test@example.com",
        defaults={
            "username": "publisher_b_test",
            "role": "publisher",
            "organization": org,
        },
    )
    if created:
        pub_b.set_password("PublisherB123!")
        pub_b.save()
    task_b = (
        DetectionTask.objects.filter(user=pub_b, status="completed")
        .order_by("-id")
        .first()
    )
    if not task_b:
        ref = DetectionTask.objects.filter(user=pub_a, status="completed").order_by("-id").first()
        task_b = DetectionTask.objects.create(
            user=pub_b,
            organization=org,
            task_name="cross-user-test-task",
            task_type=(ref.task_type if ref else "image_detection"),
            status="completed",
        )
    r = requests.post(
        f"{BASE}/api/manual-review-requests/",
        json={
            "detection_task_id": str(task_b.id),
            "task_type": "image_detection",
            "reason": "跨用户越权测试申请理由足够长",
        },
        headers=hdr(pub_token),
        timeout=30,
    )
    ok = r.status_code == 403
    RESULTS["6.3-2"] = {
        "status": r.status_code,
        "msg": str(r.json())[:200],
        "result": "通过" if ok else "失败",
        "note": "非本人任务应返回 403 无权访问该检测任务",
    }


def test_6_4_5(pub_token: str) -> None:
    """Overlong review text — no explicit max in code; probe 200k chars."""
    long_text = "This is a boundary test sentence. " * 6000  # ~210k chars
    r = requests.post(
        f"{BASE}/api/review/submit/",
        json={"task_name": "long-review", "text": long_text},
        headers=hdr(pub_token),
        timeout=180,
    )
    if r.status_code == 400 and "超过最大长度" in r.text:
        RESULTS["6.4-5"] = {
            "status": r.status_code,
            "msg": str(r.json())[:200],
            "result": "通过",
            "note": "超过 MAX_REVIEW_TEXT_CHARS(100000) 被拒绝",
        }
    elif r.status_code in (200, 201):
        j = r.json()
        RESULTS["6.4-5"] = {
            "status": r.status_code,
            "msg": f"task_id={j.get('task_id')}, cleaned_len={j.get('cleaned_text_length')}",
            "result": "失败",
            "note": "超长文本不应被接受",
        }
    elif r.status_code == 400:
        RESULTS["6.4-5"] = {
            "status": r.status_code,
            "msg": str(r.json())[:200],
            "result": "通过",
            "note": "拒绝超长输入",
        }
    else:
        RESULTS["6.4-5"] = {
            "status": r.status_code,
            "msg": r.text[:200],
            "result": "失败" if r.status_code >= 500 else "阻塞",
        }


def test_6_4_6(pub_token: str) -> None:
    raw = "\ufeffReview\x00with\x1fBOM\t  and   spaces\n\n\n\nmixed 中文 English"
    r = requests.post(
        f"{BASE}/api/review/submit/",
        json={"task_name": "dirty-review", "text": raw},
        headers=hdr(pub_token),
        timeout=60,
    )
    if r.status_code not in (200, 201):
        RESULTS["6.4-6"] = {"status": r.status_code, "msg": str(r.json())[:200], "result": "失败"}
        return
    j = r.json()
    cleaned_len = j.get("cleaned_text_length")
    tid = j.get("task_id")
    res = requests.get(f"{BASE}/api/review/{tid}/result/", headers=hdr(pub_token), timeout=30)
    ok = r.status_code in (200, 201) and cleaned_len and cleaned_len > 0
    RESULTS["6.4-6"] = {
        "status": r.status_code,
        "msg": f"cleaned_text_length={cleaned_len}, result_status={res.status_code}",
        "result": "通过" if ok else "失败",
    }


def test_6_5_3(pub_token: str) -> None:
    """Invalid / non-parseable PDF."""
    garbage = b"%PDF-1.4\n%" + b"\x00" * 200 + b"\n%%EOF"
    r = requests.post(
        f"{BASE}/api/paper/upload/",
        files={"file": ("encrypted_fake.pdf", garbage, "application/pdf")},
        headers=hdr(pub_token),
        timeout=30,
    )
    ok = r.status_code == 400
    RESULTS["6.5-3"] = {
        "status": r.status_code,
        "msg": str(r.json())[:200],
        "result": "通过" if ok else "失败",
        "note": "使用损坏 PDF 字节；真·密码加密 PDF 需专用样本文件",
    }

    try:
        import fitz

        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Encrypted sample")
        buf = io.BytesIO()
        doc.save(
            buf,
            encryption=fitz.PDF_ENCRYPT_AES_256,
            owner_pw="owner",
            user_pw="secret",
        )
        doc.close()
        buf.seek(0)
        r2 = requests.post(
            f"{BASE}/api/paper/upload/",
            files={"file": ("encrypted_real.pdf", buf.read(), "application/pdf")},
            headers=hdr(pub_token),
            timeout=30,
        )
        RESULTS["6.5-3_encrypted"] = {
            "status": r2.status_code,
            "msg": str(r2.json())[:200] if r2.headers.get("content-type", "").startswith("application/json") else r2.text[:120],
            "result": "通过" if r2.status_code == 400 else ("失败" if r2.status_code >= 500 else "部分通过"),
            "note": "PyMuPDF 生成的 AES 加密 PDF",
        }
    except Exception as exc:
        RESULTS["6.5-3_encrypted"] = {"result": "跳过", "note": str(exc)}


def test_6_5_5(pub_token: str) -> None:
    """Download report for non-completed task."""
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color=(200, 100, 50)).save(buf, format="PNG")
    png = buf.getvalue()
    up = requests.post(
        f"{BASE}/api/upload/",
        files={"file": ("pending_report.png", png, "image/png")},
        headers=hdr(pub_token),
        timeout=60,
    )
    if up.status_code != 200:
        pending = DetectionTask.objects.filter(
            user__email="publisher_test@example.com", status="pending"
        ).first() or DetectionTask.objects.filter(
            user__email="publisher_test@example.com", status="in_progress"
        ).first()
        if pending:
            tid = pending.id
        else:
            RESULTS["6.5-5"] = {"result": "阻塞", "msg": "无法构造进行中任务"}
            return
    else:
        fid = up.json()["file_id"]
        ex = requests.get(
            f"{BASE}/api/upload/{fid}/extract_images/", headers=hdr(pub_token), timeout=30
        )
        images = [i["image_id"] for i in ex.json().get("images", [])]
        sub = requests.post(
            f"{BASE}/api/detection/submit/",
            json={
                "image_ids": images,
                "task_name": f"pending-rpt-{int(time.time())}",
                "detection_mode": "fast",
                "mode": 1,
            },
            headers=hdr(pub_token),
            timeout=60,
        )
        if sub.status_code not in (200, 201):
            RESULTS["6.5-5"] = {"result": "阻塞", "msg": sub.text[:200]}
            return
        tid = sub.json()["task_id"]
        time.sleep(1)

    r = requests.get(f"{BASE}/api/tasks/{tid}/report/", headers=hdr(pub_token), timeout=30)
    st = requests.get(f"{BASE}/api/detection-task/{tid}/status/", headers=hdr(pub_token), timeout=10)
    task_status = st.json().get("status") if st.ok else "?"
    ok = r.status_code == 400 and "not completed" in r.text.lower()
    RESULTS["6.5-5"] = {
        "status": r.status_code,
        "msg": str(r.json())[:200] if r.headers.get("content-type", "").startswith("application/json") else r.text[:120],
        "task_status_at_test": task_status,
        "result": "通过" if ok else ("部分通过" if r.status_code == 400 else "失败"),
    }


def main() -> int:
    try:
        requests.get(f"{BASE}/admin/", timeout=5)
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1

    pub = login("publisher_test@example.com", "Publisher123!", "publisher")
    test_6_3_2(pub)
    test_6_4_5(pub)
    test_6_4_6(pub)
    test_6_5_3(pub)
    test_6_5_5(pub)

    out = Path(__file__).with_name("remaining_task2_results.json")
    out.write_text(json.dumps(RESULTS, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out)
    for k, v in RESULTS.items():
        print(k, v.get("result"), v.get("status"), v.get("msg", "")[:80])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
