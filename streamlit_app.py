import time
import re
from dotenv import load_dotenv
import json, os
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from collections import Counter
import pandas as pd
from typing import Optional

# Import ConversableAgent class
import autogen
from autogen import ConversableAgent, LLMConfig
from autogen import AssistantAgent, UserProxyAgent, LLMConfig
from autogen.code_utils import content_str
from coding.constant import JOB_DEFINITION, RESPONSE_FORMAT
from coding.utils import paging
import streamlit as st
from openai import OpenAI


# Load environment variables from .env file
load_dotenv(override=True)

# https://ai.google.dev/gemini-api/docs/pricing
# URL configurations
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', None)
GEMINI_API_KEY_2 = os.getenv('OPEN_API_KEY', None)

seed = 42

llm_config_gemini = LLMConfig(
    api_type = "google", 
    model="gemini-2.0-flash-lite",                    # The specific model
    api_key=GEMINI_API_KEY,   # Authentication
)

llm_config_gemini_2 = LLMConfig(
    api_type = "google", 
    model="gemini-2.0-flash-lite",                    # The specific model
    api_key=GEMINI_API_KEY_2,   # Authentication
)

with llm_config_gemini:
    assistant = AssistantAgent(
        name="assistant",
        system_message=(
        "You are a helpful storyteller assistant. "
        "Please give me a story. After your result, say 'ALL DONE'. "
        "Do not say 'ALL DONE' in the same response."
        ),
        max_consecutive_auto_reply=2
    )

user_proxy = UserProxyAgent(
    "user_proxy",
    human_input_mode="NEVER",
    code_execution_config=False,
    is_termination_msg=lambda x: content_str(x.get("content")).find("ALL DONE") >= 0,
)

import os
import json
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from wordcloud import WordCloud
from collections import Counter
from matplotlib import font_manager as fm
from typing import Optional

# ------------------------
# 中英文對照字典 (i18n)
# ------------------------
i18n = {
    "zh": {
        "title": "📊｜實習類型探索｜文字雲 × 技能圖",
        "nav_explore": "｜實習類型探索｜文字雲 × 技能圖",
        "nav_navigator": "｜實習職缺導航｜",
        "nav_profile": "｜實習人物誌｜",
        "prompt": """是否在為該投哪類實習而猶豫？

本頁透過文字探勘技術，將實習資料分為七大類型，以「文字雲」與「技能圖」呈現各群的關鍵特徵，快速掌握職缺方向！

🔍 點選每一類即可查看關鍵技能、典型職稱與說明建議，再到實習導航篩選出專屬於你的職缺！""",
        "skills": "技能關鍵詞",
        "titles": "典型職稱",
        "desc": "說明",
        "wordcloud": "☁️ 四字 + 二字組合文字雲",
        "skill_chart": "🛠️ 技能長條圖",
        "menu_header": "🔧 選單",
        "language_label": "語言切換 (Language)",
    },
    "en": {
        "title": "📊 Internship Type Exploration｜Word Cloud × Skill Chart",
        "nav_explore": "Internship Explorer｜Word Cloud × Skill Chart",
        "nav_navigator": "Internship Navigator",
        "nav_profile": "Ideal Persona",
        "prompt": """Not sure which internship type to go for?

This page uses text mining to categorize internships into 7 types and visualizes their key terms using word clouds and skill charts.

🔍 Click each category to explore the skills, roles, and suggestions!""",
        "skills": "Skill Keywords",
        "titles": "Typical Titles",
        "desc": "Description",
        "wordcloud": "☁️ 4-Word + 2-Word Combo Word Cloud",
        "skill_chart": "🛠️ Skill Bar Chart",
        "menu_header": "🔧 Menu",
        "language_label": "Language",
    }
}

# ------------------------
# 側邊欄導航功能
# ------------------------
def paging(T: dict):
    st.page_link("streamlit_app.py", label=T["nav_explore"], icon="📊")
    st.page_link("pages/teacher_agent.py", label=T["nav_navigator"], icon="🔍")
    st.page_link("pages/test.py", label=T["nav_profile"], icon="💼")

# ------------------------
# 主程式
# ------------------------
def main():
    # ------------------------
    # 初始化 session_state
    # ------------------------
    if "lang_setting" not in st.session_state:
        st.session_state.lang_setting = "繁體中文"

    # ------------------------
    # 根據語言選項決定用哪一套文案
    # ------------------------
    lang_code = "zh" if st.session_state.lang_setting == "繁體中文" else "en"
    T = i18n[lang_code]

    # ------------------------
    # 頁面基本設定
    # ------------------------
    st.set_page_config(page_title=T["title"], layout="wide")
    st.title(T["title"])
    st.markdown(T["prompt"])

    # ------------------------
    # 側邊欄：導航 & 語言切換
    # ------------------------
    user_image = "https://www.w3schools.com/howto/img_avatar.png"
    with st.sidebar:
        st.header(T["menu_header"])
        paging(T)

        selected_lang = st.selectbox(
            T["language_label"],
            ["English", "繁體中文"],
            index=0 if st.session_state.lang_setting == "English" else 1,
            on_change=lambda: st.session_state.update(
                {"lang_setting": st.session_state.language_select}
            ),
            key="language_select",
        )
        st.session_state.lang_setting = selected_lang

        st.image(user_image, use_container_width=True)

    # ------------------------
    # 載入分群資料
    # ------------------------
    JSON_PATH = "data/cluster_visual_data_final_v4_described.json"
    WC_DIR = "images/wc_combo"
    SKILL_DIR = "images/skills"
    FONT_PATH = "fonts/msyh.ttc"

    with open(JSON_PATH, encoding="utf-8") as f:
        clusters = json.load(f)
    cid2info = {c["cluster_id"]: c for c in clusters}

    # ------------------------
    # 中文字型設定
    # ------------------------
    try:
        my_font = fm.FontProperties(fname=FONT_PATH)
        plt.rcParams['font.family'] = my_font.get_name()
    except:
        plt.rcParams['font.family'] = "sans-serif"

    # ------------------------
    # 顯示每一群類別
    # ------------------------
    for cid, info in cid2info.items():
        group_title = f"{cid + 1}｜{info['category']}"
        with st.expander(group_title, expanded=False):
            safe_name = info["category"].replace("/", "_").replace(" ", "")

            st.markdown(f"**{T['skills']}：** {info['skills_keywords']}")
            st.markdown(f"**{T['titles']}：** {info['titles']}")
            st.markdown(info["summary"])

            # --- 文字雲 ---
            st.markdown(f"### {T['wordcloud']}")
            wc_path = os.path.join(WC_DIR, f"wordcloud_combo_{cid}_{safe_name}.png")
            if os.path.exists(wc_path):
                st.image(wc_path, use_container_width=True)
            else:
                words = info["word_text"].split()
                quads = [w for w in words if len(w) == 4]
                bigrams = [w1 + w2 for w1, w2 in zip(words[:-1], words[1:]) if len(w1) == len(w2) == 2]
                terms = quads + bigrams
                wc = WordCloud(font_path=FONT_PATH, width=800, height=400, background_color="white")
                fig, ax = plt.subplots(figsize=(8, 4))
                ax.imshow(wc.generate_from_frequencies(Counter(terms)))
                ax.axis("off")
                st.pyplot(fig)

            # --- 技能圖 ---
            st.markdown(f"### {T['skill_chart']}")
            skill_path = os.path.join(SKILL_DIR, f"skills_{cid}_{safe_name}.png")
            skills = info.get("skills_count", {})

            if os.path.exists(skill_path):
                st.image(skill_path, use_container_width=True)
            elif skills:
                labels, values = zip(*skills.items())
                # 以根號放大，讓橫軸更飽滿
                boosted_values = [int(np.sqrt(v) * 15) for v in values]
                fig, ax = plt.subplots(figsize=(6, 4))
                ax.barh(labels, boosted_values)
                ax.set_title(f"Top {T['skills']}：{info['category']}", fontproperties=my_font)
                ax.set_yticklabels(labels, fontproperties=my_font)
                ax.invert_yaxis()
                st.pyplot(fig)
            else:
                st.info("此群尚無技能統計圖。")

if __name__ == "__main__":
    main()