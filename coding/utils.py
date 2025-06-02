import streamlit as st
from typing import List, Dict, Any, Optional
import json
import os
from datetime import datetime
import pandas as pd

def paging():
    st.page_link("streamlit_app.py", label="Home", icon="🏠")
    st.page_link("pages/textmining.py", label="實習類型探索｜文字雲 × 技能圖", icon="📊")
    st.page_link("pages/teacher_agent.py", label="實習職缺導航", icon="🔍")
    st.page_link("pages/test.py", label="Ideal Persona", icon="🧑‍💼")
    

def display_session_msg(container_obj, user_image: Optional[str] = None):
    # Initialize messages list if not present
    messages = st.session_state.setdefault("messages", [])

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        avatar = None

        # Determine avatar to use
        if role == "assistant":
            avatar = user_image
        elif role not in ["user", "assistant"]:
            avatar = msg.get("image", None)

        # Display message
        if avatar:
            container_obj.chat_message(role, avatar=avatar).markdown(content)
        else:
            container_obj.chat_message("ai").markdown(content)

def show_chat_history(container_obj, chat_history: List[Dict[str, Any]], user_image=None) -> str:
    """
    Processes a list of chat history entries by:
      1. Skipping any entries whose role is 'tool'
      2. Skipping entries with null or empty content
      3. Stripping out the "ALL DONE" token
    Displays each valid message via Streamlit and returns the processed messages
    as a JSON-formatted string.
    """
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    processed = []

    for entry in chat_history:
        if entry.get('role') == 'tool':
            continue

        content = entry.get('content')

        if content is None:
            continue
        if isinstance(content, str):
            content = content.replace("##ALL DONE##", "")
            content = content.replace("ALL DONE", "")
            if not content.strip():
                continue
        else:
            continue

        role = entry.get('role', 'user')
        message = {"role": role, "content": content}
        processed.append(message)

        # Append to session history
        st.session_state.messages.append(message)

        # Display according to role
        if role == 'assistant':
            container_obj.chat_message("assistant", avatar=user_image).write(content)
        else:
            container_obj.chat_message("ai").write(content)

    # Return the processed messages as a JSON string
    return json.dumps(processed, ensure_ascii=False, indent=2)

def save_messages_to_json(
    messages: List[Dict[str, Any]],
    output_dir: str = "."
) -> str:
    """
    Save a list of chat messages (each a dict with 'role' and 'content')
    to a JSON file named with the current timestamp in "YYYY-MM-DD HH-MM.json" format.

    Args:
        messages: The processed messages to save.
        output_dir: Directory where the file will be saved. Defaults to current directory.

    Returns:
        The full path of the JSON file that was written.
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Generate filename based on current local time
    timestamp = datetime.now().strftime("%Y-%m-%d %H-%M")
    filename = f"{timestamp}.json"
    filepath = os.path.join(output_dir, filename)

    # Write messages to the file
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

    return filepath


def merge_csv():
    base_dir = "pages"
    os.makedirs(base_dir, exist_ok=True)

    # ===== 中文資料 =====
    df_cake_zh = pd.read_csv(os.path.join(base_dir, "jobsthousands.csv"))
    df_104_zh = pd.read_csv(os.path.join(base_dir, "104_jobs_all.csv"))
    df_104_zh = df_104_zh.rename(columns={
        "custName": "公司名稱",
        "jobName": "職缺名稱",
        "description": "完整描述",
        "tags": "技能關鍵字",
        "link": "職缺網址"
    })
    # 只保留 Cake 欄位並按照其順序
    df_104_zh = df_104_zh[[col for col in df_cake_zh.columns if col in df_104_zh.columns]]
    df_104_zh = df_104_zh.reindex(columns=df_cake_zh.columns)

    df_merged_zh = pd.concat([df_cake_zh, df_104_zh], ignore_index=True)
    df_merged_zh.drop_duplicates(subset=["公司名稱", "職缺名稱"], inplace=True)
    df_merged_zh.to_csv(os.path.join(base_dir, "merged_jobs.csv"), index=False, encoding="utf-8-sig")

    # ===== 英文資料 =====
    df_cake_en = pd.read_csv(os.path.join(base_dir, "jobsthousands_en.csv"))
    df_104_en = pd.read_csv(os.path.join(base_dir, "104_jobs_all_en.csv"))
    df_104_en = df_104_en.rename(columns={
        "custName": "Company",
        "jobName": "Job Title",
        "description": "Full Description",
        "tags": "Tags",
        "link": "Job URL"
    })

    # 確保欄位順序與 Cake 一樣
    df_104_en = df_104_en[df_cake_en.columns]

    # 合併 + 去重
    df_merged_en = pd.concat([df_cake_en, df_104_en], ignore_index=True)
    df_merged_en.drop_duplicates(subset=["Company", "Job Title"], inplace=True)

    # 輸出檔案
    df_merged_en.to_csv(os.path.join(base_dir, "merged_jobs_en.csv"), index=False, encoding="utf-8-sig")