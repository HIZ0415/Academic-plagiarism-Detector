# -*- coding: utf-8 -*-
"""Automated coverage for the remaining Task-1 pending cases.

This script intentionally separates:
- API-backed checks that can be executed against the running local services.
- static frontend assertions for UI behavior that needs a browser for final
  visual confirmation, but whose implementation can still be checked by script.

Requires the local environment from scripts/start-local-windows.ps1.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests

BASE = os.environ.get("TEST_API_BASE", "http://127.0.0.1:8000")
ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "代码" / "后端" / "后端代码"
USER_FRONTEND = ROOT / "代码" / "前端" / "前端用户端"
ADMIN_FRONTEND = ROOT / "代码" / "前端" / "前端管理端"
OUT = Path(__file__).with_name("task1_pending_auto_results.json")


def result(ok: bool, method: str, note: str, **extra: Any) -> dict[str, Any]:
    return {
        "result": "通过" if ok else "失败",
        "method": method,
        "note": note,
        **extra,
    }


def healthcheck() -> None:
    for url in [
        "http://127.0.0.1:3000/",
        "http://127.0.0.1:3001/",
        f"{BASE}/admin/",
        "http://127.0.0.1:8010/health",
    ]:
        r = requests.get(url, timeout=15)
        if r.status_code >= 500:
            raise RuntimeError(f"service unhealthy: {url} -> {r.status_code}")


def setup_django() -> None:
    import sys

    sys.path.insert(0, str(BACKEND))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fake_image_detector.local_settings")
    os.environ.setdefault("SQLITE_NAME", str(BACKEND / ".local-dev" / "db.sqlite3"))
    import django

    django.setup()


def ensure_org_admin() -> None:
    setup_django()
    from django.contrib.auth import get_user_model
    from core.models import Organization

    User = get_user_model()
    org = Organization.objects.first()
    user, created = User.objects.get_or_create(
        email="org_admin@example.com",
        defaults={
            "username": "org_admin",
            "role": "admin",
            "is_staff": True,
            "organization": org,
        },
    )
    changed = False
    if created or not user.check_password("OrgAdmin123!"):
        user.set_password("OrgAdmin123!")
        changed = True
    if user.role != "admin":
        user.role = "admin"
        changed = True
    if not user.is_staff:
        user.is_staff = True
        changed = True
    if org and user.organization_id != org.id:
        user.organization = org
        changed = True
    if changed:
        user.save()


def login(email: str, password: str, role: str | None = None, admin: bool = False) -> str:
    body: dict[str, str] = {"email": email, "password": password}
    if role:
        body["role"] = role
    path = "/api/admin-login/" if admin else "/api/login/"
    r = requests.post(f"{BASE}{path}", json=body, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"login failed for {email}: {r.status_code} {r.text[:300]}")
    return r.json()["access"]


def hdr(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def task12_history_filter(pub: str) -> dict[str, Any]:
    now = datetime.now()
    params_list = [
        {"page": 1, "page_size": 10, "status": "completed"},
        {"page": 1, "page_size": 10, "task_type": "paper_aigc"},
        {
            "page": 1,
            "page_size": 10,
            "startTime": (now - timedelta(days=180)).strftime("%Y-%m-%d %H:%M:%S"),
            "endTime": now.strftime("%Y-%m-%d %H:%M:%S"),
        },
    ]
    details: list[dict[str, Any]] = []
    ok = True
    for params in params_list:
        r = requests.get(f"{BASE}/api/user-tasks/", params=params, headers=hdr(pub), timeout=30)
        payload = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        tasks = payload.get("tasks", [])
        this_ok = r.status_code == 200
        if "status" in params:
            this_ok = this_ok and all(t.get("status") == params["status"] for t in tasks)
        if "task_type" in params:
            this_ok = this_ok and all(t.get("task_type") == params["task_type"] for t in tasks)
        ok = ok and this_ok
        details.append(
            {
                "params": params,
                "status": r.status_code,
                "count": len(tasks),
                "ok": this_ok,
            }
        )

    source = read(USER_FRONTEND / "src" / "pages" / "history.vue")
    static_ok = all(
        s in source
        for s in [
            "v-model=\"filters.status\"",
            "v-model=\"filters.taskType\"",
            "v-model=\"filters.timeRange\"",
            "publisher.getAllDetectionTask(params)",
            "params.status = filters.value.status",
            "params.task_type = filters.value.taskType",
            "params.startTime = formatDateFilter",
            "params.endTime = formatDateFilter",
        ]
    )
    return result(
        ok and static_ok,
        "API + 源码断言",
        "检测历史支持按状态、任务类型、时间范围筛选；接口返回与筛选条件一致。",
        api_checks=details,
        static_ok=static_ok,
    )


def task21_docx_prompt() -> dict[str, Any]:
    source = read(USER_FRONTEND / "src" / "pages" / "upload.vue")
    checks = {
        "detects_docx": "name.endsWith('.docx')" in source,
        "docx_resource_type": "'docx'" in source and "type ResourceType" in source,
        "blocks_before_backend": "if (row.type === 'docx')" in source,
        "expected_prompt": "论文检测仅支持 PDF，请将 DOCX 转为 PDF 后上传。" in source,
        "no_docx_in_accept": 'accept="image/*,.pdf,.txt,.zip,.rar"' in source,
    }
    return result(
        all(checks.values()),
        "源码断言",
        "批量提交逻辑能识别 DOCX，并在前端直接置为失败提示，不创建后端检测任务。",
        checks=checks,
    )


def ensure_manual_review_request(pub: str, org_admin: str, task_type: str | None = None) -> tuple[int | None, int | None, str | None]:
    tasks_r = requests.get(
        f"{BASE}/api/user-tasks/",
        params={"page": 1, "page_size": 50},
        headers=hdr(pub),
        timeout=30,
    )
    tasks_r.raise_for_status()
    tasks = tasks_r.json().get("tasks", [])
    candidate = None
    for t in tasks:
        if t.get("status") == "completed" and (task_type is None or t.get("task_type") == task_type):
            candidate = t
            break
    if not candidate:
        return None, None, None

    cr = requests.post(
        f"{BASE}/api/manual-review-requests/",
        json={
            "detection_task_id": str(candidate["task_id"]),
            "task_type": candidate.get("task_type") or "image_detection",
            "reason": f"自动化补测申请理由 {int(time.time())}",
        },
        headers=hdr(pub),
        timeout=30,
    )
    if cr.status_code not in (200, 201):
        return None, candidate["task_id"], candidate.get("task_type")
    rr_id = cr.json().get("review_request_id") or cr.json().get("id")
    if rr_id:
        requests.post(
            f"{BASE}/api/handle_reviewRequest/{rr_id}/",
            json={"choice": 1, "reason": "自动化补测通过"},
            headers=hdr(org_admin),
            timeout=30,
        )
    return rr_id, candidate["task_id"], candidate.get("task_type")


def task27_application_filter(pub: str, org_admin: str) -> dict[str, Any]:
    rr_id, _, _ = ensure_manual_review_request(pub, org_admin)
    params_list = [
        {"page": 1, "page_size": 10},
        {"page": 1, "page_size": 10, "status": "in_progress"},
        {
            "page": 1,
            "page_size": 10,
            "startTime": (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S"),
            "endTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
    ]
    details = []
    ok = rr_id is not None
    for params in params_list:
        r = requests.get(
            f"{BASE}/api/get_publisher_review_tasks/",
            params=params,
            headers=hdr(pub),
            timeout=30,
        )
        payload = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        tasks = payload.get("tasks", [])
        this_ok = r.status_code == 200
        if params.get("status"):
            this_ok = this_ok and all(t.get("status") == params["status"] for t in tasks)
        ok = ok and this_ok
        details.append({"params": params, "status": r.status_code, "count": len(tasks), "ok": this_ok})

    source = read(USER_FRONTEND / "src" / "pages" / "annual.vue")
    static_ok = all(
        s in source
        for s in [
            "v-model=\"filters.status\"",
            "v-model=\"filters.timeRange\"",
            "listPublisherManualReviewApplications(params)",
            "status: filters.value.status || ''",
            "startTime: startTimeFilter",
            "endTime: endTimeFilter",
        ]
    )
    return result(
        ok and static_ok,
        "API + 源码断言",
        "人工审核申请列表支持按状态与时间筛选；脚本创建并审批了一条申请用于列表校验。",
        created_review_request_id=rr_id,
        api_checks=details,
        static_ok=static_ok,
    )


def task33_paper_or_review_manual_detail(pub: str, org_admin: str, reviewer: str) -> dict[str, Any]:
    rr_id, task_id, task_type = ensure_manual_review_request(pub, org_admin, task_type="paper_aigc")
    if not rr_id:
        return result(False, "API", "未找到可用于人工审核的已完成论文/Review 任务样本。", task_id=task_id, task_type=task_type)

    pool = requests.get(f"{BASE}/api/get_reviewer_tasks/", headers=hdr(reviewer), timeout=30)
    pool_payload = pool.json()
    if isinstance(pool_payload, list):
        items = pool_payload
    else:
        items = pool_payload.get("results") or pool_payload.get("tasks", [])
    target = next((it for it in items if str(it.get("review_request_id")) == str(rr_id)), None)
    mr_id = (target or {}).get("manual_review_id") or (target or {}).get("id")
    if not mr_id:
        return result(False, "API", "专家任务池未返回刚审批通过的论文人工审核任务。", review_request_id=rr_id)

    detail = requests.get(f"{BASE}/api/get_review_detail/{mr_id}/", headers=hdr(reviewer), timeout=30)
    payload = detail.json() if detail.headers.get("content-type", "").startswith("application/json") else {}
    text_segments = payload.get("text_segments") or payload.get("segments") or payload.get("text_units") or []
    ai_reference = (
        payload.get("ai_reference")
        or payload.get("ai_summary")
        or payload.get("ai_result")
        or payload.get("ai_detection_result")
        or payload.get("detection_task")
        or {}
    )
    ok = detail.status_code == 200 and (bool(text_segments) or bool(ai_reference))
    return result(
        ok,
        "API",
        "专家审核论文任务详情接口可返回文本片段或 AI 参考信息；页面仍建议浏览器目视确认排版。",
        review_request_id=rr_id,
        manual_review_id=mr_id,
        detail_status=detail.status_code,
        has_text_segments=bool(text_segments),
        has_ai_reference=bool(ai_reference),
        detail_keys=sorted(payload.keys()),
    )


def task41_sidebar_entry() -> dict[str, Any]:
    source = read(USER_FRONTEND / "src" / "App.vue")
    checks = {
        "publisher_academic_detection": 'effectiveRole === \'publisher\'' in source and 'title="学术检测"' in source,
        "publisher_history": 'title="检测历史"' in source,
        "publisher_manual_request": 'title="人工审核申请"' in source,
        "no_paper_detection_menu": 'title="论文检测"' not in source,
        "no_multimodal_menu": 'title="多模态融合"' not in source,
    }
    return result(
        all(checks.values()),
        "源码断言",
        "发布者侧栏只有统一的“学术检测”入口，没有独立“论文检测”或“多模态融合”菜单项。",
        checks=checks,
    )


def task42_user_legacy_redirect() -> dict[str, Any]:
    source = read(USER_FRONTEND / "src" / "router" / "index.ts")
    checks = {
        "detect_image_to_upload": "to.path === '/detect/image'" in source and "path: '/upload'" in source,
        "detect_paper_to_upload": "to.path === '/detect/paper'" in source and "section: 'paper'" in source,
        "paper_tab_mapping": "paper_tab: paperTab" in source,
        "requires_login_guard": "if (!isLoggedIn.value)" in source,
    }
    return result(
        all(checks.values()),
        "源码断言",
        "用户端路由守卫已实现 /detect/image 与 /detect/paper 到 /upload 的旧路径重定向。",
        checks=checks,
    )


def task43_admin_legacy_redirect() -> dict[str, Any]:
    source = read(ADMIN_FRONTEND / "src" / "router" / "index.ts")
    checks = {
        "paper_logs_to_logs": "to.path === '/paper-logs'" in source and "path: '/logs'" in source and "scope: 'paper'" in source,
        "review_logs_to_logs": "to.path === '/review-logs'" in source and "path: '/logs'" in source and "scope: 'review'" in source,
        "requires_login_guard": "if (!isLoggedIn.value)" in source,
    }
    return result(
        all(checks.values()),
        "源码断言",
        "管理端路由守卫已实现 /paper-logs 与 /review-logs 到 /logs 的旧路径重定向。",
        checks=checks,
    )


def main() -> int:
    healthcheck()
    ensure_org_admin()
    pub = login("publisher_test@example.com", "Publisher123!", "publisher")
    reviewer = login("reviewer_test@example.com", "Reviewer123!", "reviewer")
    org_admin = login("org_admin@example.com", "OrgAdmin123!", admin=True)

    results = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "services": {
            "user_frontend": "http://127.0.0.1:3000/",
            "admin_frontend": "http://127.0.0.1:3001/",
            "django": f"{BASE}/admin/",
            "ai": "http://127.0.0.1:8010/health",
        },
        "cases": {
            "12": task12_history_filter(pub),
            "21": task21_docx_prompt(),
            "27": task27_application_filter(pub, org_admin),
            "33": task33_paper_or_review_manual_detail(pub, org_admin, reviewer),
            "41": task41_sidebar_entry(),
            "42": task42_user_legacy_redirect(),
            "43": task43_admin_legacy_redirect(),
        },
    }
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if all(c["result"] == "通过" for c in results["cases"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
