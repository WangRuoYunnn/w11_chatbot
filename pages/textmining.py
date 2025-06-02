import streamlit as st
import json, os
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from collections import Counter
from coding.utils import paging
import pandas as pd

# ---------- 設定路徑 ----------
JSON_PATH = "data/cluster_visual_data_final_v4_described.json"
WC_DIR = "images/wc_combo"
SKILL_DIR = "images/skills"
FONT_PATH = "fonts/msyh.ttc"

# ---------- 載入資料 ----------
with open(JSON_PATH, encoding="utf-8") as f:
    clusters = json.load(f)
cid2info = {c["cluster_id"]: c for c in clusters}

# ---------- 字體設定 ----------
my_font = fm.FontProperties(fname=FONT_PATH)
plt.rcParams['font.family'] = my_font.get_name()

# ---------- UI ----------
st.set_page_config(page_title="實習類型探索", layout="wide")
st.title("📊 實習類型探索｜文字雲 × 技能圖")

# ---------- 說明文字 ----------
st.markdown("""
是否在為該投哪類實習而猶豫？
            
本頁透過文字探勘技術，將實習資料分為七大類型，以「文字雲」與「技能圖」呈現各群的關鍵特徵，快速掌握職缺方向！

🔍 點選每一類即可查看關鍵技能、典型職稱與說明建議，再到實習導航篩選出專屬於你的職缺！
""")

# 展示每一群類別的簡介卡 + 展開按鈕
for cid, info in cid2info.items():
    with st.expander(f"{cid+1}｜{info['category']}", expanded=False):
        safe_name = info["category"].replace("/", "_").replace(" ", "")

        st.markdown(f"**技能關鍵詞：** {info['skills_keywords']}")
        st.markdown(f"**典型職稱：** {info['titles']}")
        st.markdown(f"{info['summary']}")
        #st.markdown(f"**📊 職缺筆數：** {info['count']}")

        # ---------- 文字雲 ----------
        st.markdown("### ☁️ 四字 + 二字組合文字雲")
        wc_path = os.path.join(WC_DIR, f"wordcloud_combo_{cid}_{safe_name}.png")
        if os.path.exists(wc_path):
            st.image(wc_path, use_column_width=True)
        else:
            # 即時繪圖
            words = info["word_text"].split()
            quads = [w for w in words if len(w) == 4]
            bigrams = [w1 + w2 for w1, w2 in zip(words[:-1], words[1:]) if len(w1) == len(w2) == 2]
            terms = quads + bigrams
            wc = WordCloud(font_path=FONT_PATH, width=800, height=400, background_color="white")
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.imshow(wc.generate_from_frequencies(Counter(terms)))
            ax.axis("off")
            st.pyplot(fig)

        # ---------- 技能圖 ----------
        st.markdown("### 🛠️ 技能長條圖")
        skill_path = os.path.join(SKILL_DIR, f"skills_{cid}_{safe_name}.png")
        skills = info["skills_count"]

        if os.path.exists(skill_path):
            st.image(skill_path, use_column_width=True)
        elif skills:
            labels, values = zip(*skills.items())
            fig, ax = plt.subplots(figsize=(6, 4))
            ax.barh(labels, values)
            ax.set_title(f"Top 技能：{info['category']}", fontproperties=my_font)
            ax.set_yticklabels(labels, fontproperties=my_font)
            ax.invert_yaxis()
            st.pyplot(fig)
        else:
            st.info("此群尚無技能統計圖。")


# -----------page setting---------------
def save_lang():
    st.session_state["lang_setting"] = st.session_state.get("language_select")

user_image = "https://www.w3schools.com/howto/img_avatar.png"

def main():
    # merge_csv()

    if "lang_setting" not in st.session_state:
        st.session_state.lang_setting = "English"

    if "search_keywords" not in st.session_state:
        st.session_state.search_keywords = []
    if "result_df" not in st.session_state:
        st.session_state.result_df = pd.DataFrame()
    if "selected_jobs" not in st.session_state:
        st.session_state.selected_jobs = []
    if "saved_jobs" not in st.session_state:
        st.session_state.saved_jobs = []
    if "hidden_saved_jobs" not in st.session_state:
        st.session_state.hidden_saved_jobs = set()
    if "aggrid_key" not in st.session_state:
        st.session_state.aggrid_key = "job_grid"

    with st.sidebar:
        paging()
        selected_lang = st.selectbox(
            "Language",
            ["English", "繁體中文"],
            index=0 if st.session_state.lang_setting == "English" else 1,
            on_change=save_lang,
            key="language_select",
        )
        lang_setting = st.session_state.get("lang_setting", selected_lang)
        st.session_state["lang_setting"] = lang_setting

        st.image(user_image)

if __name__ == "__main__":
    main()