"""PaddleOCR MCP Server - 调用 AI Studio PaddleOCR-VL API 识别图像型 PDF"""

import json
import os
import time
import requests
from fastmcp import FastMCP

JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
TOKEN = "a8a633e4a5ada1136ff4103feb9a431d3f417092"
MODEL = "PaddleOCR-VL-1.5"

mcp = FastMCP("paddleocr")


def _submit_job(file_path: str) -> str:
    """提交 OCR 任务，返回 jobId"""
    headers = {"Authorization": f"bearer {TOKEN}"}
    optional_payload = {
        "useDocOrientationClassify": False,
        "useDocUnwarping": False,
        "useChartRecognition": False,
    }

    if file_path.startswith("http"):
        headers["Content-Type"] = "application/json"
        payload = {
            "fileUrl": file_path,
            "model": MODEL,
            "optionalPayload": optional_payload,
        }
        resp = requests.post(JOB_URL, json=payload, headers=headers, timeout=30)
    else:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        data = {"model": MODEL, "optionalPayload": json.dumps(optional_payload)}
        with open(file_path, "rb") as f:
            resp = requests.post(JOB_URL, headers=headers, data=data,
                                 files={"file": f}, timeout=120)

    resp.raise_for_status()
    return resp.json()["data"]["jobId"]


def _poll_job(job_id: str, timeout: int = 600) -> str:
    """轮询直到任务完成，返回结果 JSON URL"""
    headers = {"Authorization": f"bearer {TOKEN}"}
    deadline = time.time() + timeout

    while time.time() < deadline:
        resp = requests.get(f"{JOB_URL}/{job_id}", headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()["data"]
        state = data["state"]

        if state == "done":
            return data["resultUrl"]["jsonUrl"]
        elif state == "failed":
            raise RuntimeError(f"OCR 任务失败: {data.get('errorMsg', '未知错误')}")

        time.sleep(5)

    raise TimeoutError(f"OCR 任务超时（>{timeout}s）")


def _fetch_markdown(jsonl_url: str) -> str:
    """下载结果 JSONL，拼接所有页面的 Markdown 文本"""
    resp = requests.get(jsonl_url, timeout=60)
    resp.raise_for_status()

    pages = []
    for line in resp.text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        result = json.loads(line)["result"]
        for res in result["layoutParsingResults"]:
            pages.append(res["markdown"]["text"])

    return "\n\n---\n\n".join(pages)


@mcp.tool()
def ocr_pdf(file_path: str, save_to: str = "") -> str:
    """
    对图像型 PDF（或图片）进行 OCR，返回 Markdown 格式文本。

    Args:
        file_path: 本地文件绝对路径（PDF/PNG/JPG），或可公开访问的 HTTP URL
        save_to:   可选。若提供，将 Markdown 结果保存到该路径（绝对路径）

    Returns:
        OCR 识别后的 Markdown 文本
    """
    job_id = _submit_job(file_path)
    jsonl_url = _poll_job(job_id)
    markdown = _fetch_markdown(jsonl_url)

    if save_to:
        os.makedirs(os.path.dirname(os.path.abspath(save_to)), exist_ok=True)
        with open(save_to, "w", encoding="utf-8") as f:
            f.write(markdown)

    return markdown


if __name__ == "__main__":
    mcp.run()
