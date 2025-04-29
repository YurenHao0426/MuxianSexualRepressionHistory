#!/usr/bin/env python3
"""
按 UID 抓取 B 站评论并增量写入 Excel。
如有更新，自动 `git add && git commit -m "data: update"`。
"""
import os, sys, json, subprocess, pathlib, datetime
import requests, pandas as pd

BASE_URL   = "https://api.aicu.cc/api/v3/search/getreply"
UID        = int(os.getenv("BILIBILI_UID", "1"))          # 改成目标 UID，或在 Actions secrets 中设
EXCEL_FILE = pathlib.Path("replies.xlsx")
MAX_P_PAGE = 500
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0 Safari/537.36"
    ),
    # "Referer": "https://www.aicu.cc/",   # 如果仍 403 就把这行放开
}

def fetch_all(uid: int):
    replies, pn = [], 1
    while True:
        r = requests.get(BASE_URL, params=dict(uid=uid, pn=pn, ps=MAX_P_PAGE, mode=0), headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        if data.get("code") != 0:
            raise RuntimeError(f"API 返回 code={data['code']}")
        batch = data["data"]["replies"]
        replies.extend(batch)
        if data["data"]["cursor"]["is_end"]:
            break
        pn += 1
    return pd.DataFrame(replies)

def merge_and_save(df_new: pd.DataFrame, excel_path: pathlib.Path):
    if excel_path.exists():
        df_old = pd.read_excel(excel_path)
        # 以 reply 的唯一 id 去重（字段为 id_str 或 rpid，看 API 输出）
        key = "rpid"
        df_all = pd.concat([df_old, df_new]).drop_duplicates(key, keep="first")
    else:
        df_all = df_new

    # 若有新增才写盘，返回是否更新
    if excel_path.exists() and len(df_all) == len(pd.read_excel(excel_path)):
        return False
    df_all.to_excel(excel_path, index=False)
    return True

def git_commit_if_changed():
    subprocess.run(["git", "add", "replies.xlsx"], check=True)
    # --quiet 防止 log 过长；如果无变动会返回 1，用 non-zero exit 吞掉
    subprocess.run(["git", "-c", "user.name='github-actions'",
                    "-c", "user.email='actions@github.com'",
                    "commit", "-m", f'data: update {datetime.date.today()}'],
                   check=False)

if __name__ == "__main__":
    df = fetch_all(UID)
    if merge_and_save(df, EXCEL_FILE):
        git_commit_if_changed()
        print("✅ Excel 已更新并提交")
    else:
        print("ℹ️ 无新数据")
