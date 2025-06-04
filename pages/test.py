import os
from io import BytesIO

import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from pdf2image import convert_from_bytes

from coding.persona_tools import (
    persona_name,
    persona_title,
    get_clean_titles,
    extract_all_hard_skills_as_text,
    persona_hardskill,
    extract_all_soft_skills_as_text,
    persona_softskill,
    parse_ai_text_to_resources,
    get_ai_resources,
)

# ------------------------
# 中英文對照字典 (i18n)
# ------------------------
i18n = {
    "zh": {
        "menu_header": "🔧 選單",
        "title": "💼｜實習人物誌｜",
        "nav_explore": "｜實習類型探索｜文字雲 × 技能圖",
        "nav_navigator": "｜實習職缺導航｜",
        "nav_profile": "｜實習人物誌｜",
        "language_label": "語言切換 (Language)",
        "selected_lang": "已選語言：",
        "download_button": "📄 下載您的個人化配置檔",
        "nav_explore": "實習類型探索｜文字雲 × 技能圖",
        "nav_navigator": "實習職缺導航",
        "nav_profile": "實習人物誌",
    },
    "en": {
        "title": "💼｜Ideal Persona｜",
        "nav_explore": "Internship Explorer｜Word Cloud × Skill Chart",
        "nav_navigator": "Internship Navigator",
        "nav_profile": "Ideal Persona",
        "language_label": "Language",
        "selected_lang": "Selected language:",
        "download_button": "📄 Download Your Customized Persona",
        "nav_explore": "Internship Explorer｜Word Cloud × Skill Chart",
        "nav_navigator": "Internship Navigator",
        "nav_profile": "Ideal Persona",
        "menu_header": "🔧 Menu",
    },
}

def save_lang():
    st.session_state["lang_setting"] = st.session_state.get("language_select")

# ------------------------
# 側邊欄導航，不帶參數
# ------------------------
def paging():
    # 依照目前語言設定，決定要跑哪個 label
    lang_code = "zh" if st.session_state.lang_setting == "繁體中文" else "en"
    T = i18n[lang_code]

    st.page_link("streamlit_app.py", label=T["nav_explore"], icon="📊")
    st.page_link("pages/teacher_agent.py", label=T["nav_navigator"], icon="🔍")
    st.page_link("pages/test.py", label=T["nav_profile"], icon="💼")

@st.cache_data(show_spinner="🔍 Wait a minute...")
def get_cached_ai_resources(role: str, skills: str) -> str:
    return get_ai_resources(role, skills)

def pdf_to_png(pdf_path_or_bytes):
    """
    輸入PDF路徑或BytesIO，回傳PIL Image物件（PDF第1頁轉PNG）
    """
    if isinstance(pdf_path_or_bytes, BytesIO):
        pdf_bytes = pdf_path_or_bytes.getvalue()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    else:
        doc = fitz.open(pdf_path_or_bytes)
    
    page = doc.load_page(0)  # 第一頁
    mat = fitz.Matrix(2, 2)  # 放大 2 倍（可調整解析度）
    pix = page.get_pixmap(matrix=mat)
    
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    doc.close()
    return img

def paging(T: dict):
    st.page_link("streamlit_app.py", label=T["nav_explore"], icon="📊")
    st.page_link("pages/teacher_agent.py", label=T["nav_navigator"], icon="🔍")
    st.page_link("pages/test.py", label=T["nav_profile"], icon="💼")

def main():
    # 初始化 session_state
    if "lang_setting" not in st.session_state:
        st.session_state.lang_setting = "繁體中文"

    # 根據語言設定選擇文案
    lang_code = "zh" if st.session_state.lang_setting == "繁體中文" else "en"
    T = i18n[lang_code]

    # 頁面標題
    st.title(T["title"])        

    # 側邊欄：導航 & 語言切換
    user_image = "https://www.w3schools.com/howto/img_avatar.png"
    with st.sidebar:
        st.header(T["menu_header"])
        # 呼叫 paging()，不傳參數
        paging(T)

        selected_lang = st.selectbox(
            T["language_label"],
            ["English", "繁體中文"],
            index=0 if st.session_state.lang_setting == "English" else 1,
            on_change=save_lang,
            key="language_select",
        )
        st.session_state.lang_setting = selected_lang
        st.write(f"{T['selected_lang']} {selected_lang}")
        st.image(user_image, use_container_width=True)
    
    # 讀取職缺清單並清洗
    df = pd.read_csv("pages/saved_jobs.csv")
    job_titles = df["Job Title"].dropna().tolist()
    cleaned_raw = get_clean_titles(job_titles)

    # 取得輸入名字與生成底圖
    img, name = persona_name("pages/template.png")
    if img is None:
        return

    # 疊加職稱與技能
    img = persona_title(img, cleaned_raw)
    hard_skills = extract_all_hard_skills_as_text("pages/saved_jobs.csv")
    persona_hardskill(img, hard_skills)
    soft_skills = extract_all_soft_skills_as_text("pages/saved_jobs.csv")
    persona_softskill(img, soft_skills)

    ai_text = get_cached_ai_resources(cleaned_raw, hard_skills)
    resources = parse_ai_text_to_resources(ai_text)

    # 將 PIL 圖轉到 ReportLab Canvas
    bg_buffer = BytesIO()
    img.save(bg_buffer, format="PNG")
    bg_buffer.seek(0)
    bg_reader = ImageReader(bg_buffer)

    # 建立 PDF 物件
    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=(1080, 720))
    c.drawImage(bg_reader, 0, 0, width=1080, height=720)

    # 設定字體樣式與顏色
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor("#2c606d")

    # 資源清單位置設定
    y = 185
    for res in resources:
        text = f"[{res['type']}] {res['title']}"
        c.drawString(490, y, text)
        c.linkURL(res["url"], (490, y, 900, y + 15), relative=0)
        y -= 25

    c.save()
    pdf_bytes = pdf_buffer.getvalue()

    # === 轉 PNG 用於顯示 ===
    images = convert_from_bytes(pdf_bytes)
    png_buffer = BytesIO()
    images[0].save(png_buffer, format="PNG")
    png_bytes = png_buffer.getvalue()

    # === Streamlit 顯示與下載 ===
    st.image(png_bytes, use_container_width=True)
    st.download_button(
        T["download_button"],
        data=pdf_bytes,
        file_name=f"persona_{name}.pdf",
        mime="application/pdf",
    )

if __name__ == "__main__":
    main()

# from PIL import Image, ImageDraw, ImageFont
# import streamlit as st
# from coding.utils import paging
# from io import BytesIO
# import os
# from coding.persona_tools import persona_name, persona_title, get_clean_titles, format_titles_centered
# from coding.persona_tools import extract_all_hard_skills_as_text, persona_hardskill, persona_softskill, extract_all_soft_skills_as_text
# from coding.persona_tools import parse_ai_text_to_resources, get_ai_resources
# import pandas as pd
# import fitz  # PyMuPDF
# from io import BytesIO
# from PIL import Image
# from reportlab.pdfgen import canvas
# from reportlab.lib.utils import ImageReader
# from pdf2image import convert_from_bytes
# from io import BytesIO
# from PIL import Image



# def save_lang():
#     st.session_state["lang_setting"] = st.session_state.get("language_select")

# user_image = "https://www.w3schools.com/howto/img_avatar.png"

# @st.cache_data(show_spinner="🔍 Wait a minute...")
# def get_cached_ai_resources(role: str, skills: str) -> str:
#     return get_ai_resources(role, skills)




# def pdf_to_png(pdf_path_or_bytes):
#     """
#     輸入PDF路徑或BytesIO，回傳PIL Image物件（PDF第1頁轉PNG）
#     """
#     if isinstance(pdf_path_or_bytes, BytesIO):
#         pdf_bytes = pdf_path_or_bytes.getvalue()
#         doc = fitz.open(stream=pdf_bytes, filetype="pdf")
#     else:
#         doc = fitz.open(pdf_path_or_bytes)
    
#     page = doc.load_page(0)  # 第一頁
#     mat = fitz.Matrix(2, 2)  # 放大 2 倍（可調整解析度）
#     pix = page.get_pixmap(matrix=mat)
    
#     img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
#     doc.close()
#     return img


# def main():
#     st.title("💼｜實習人物誌｜")        

#     with st.sidebar:
#         paging()
#         selected_lang = st.selectbox(
#             "Language",
#             ["English", "繁體中文"],
#             index=0,
#         )
#         st.write("Selected language:", selected_lang)
#         st.image(user_image)
#         st.write("sidebar loaded")

#     # 讀取職缺清單並清洗
#     df = pd.read_csv("pages/saved_jobs.csv")
#     job_titles = df["Job Title"].dropna().tolist()
#     cleaned_raw = get_clean_titles(job_titles)

#     # 取得輸入名字與生成底圖
#     img, name = persona_name("pages/template.png")
#     if img is None:
#         return

#     # 疊加職稱與技能
#     img = persona_title(img, cleaned_raw)
#     hard_skills = extract_all_hard_skills_as_text("pages/saved_jobs.csv")
#     persona_hardskill(img, hard_skills)
#     soft_skills = extract_all_soft_skills_as_text("pages/saved_jobs.csv")
#     persona_softskill(img, soft_skills)

#     ai_text = get_cached_ai_resources(cleaned_raw, hard_skills)
#     resources = parse_ai_text_to_resources(ai_text)


#     bg_buffer = BytesIO()
#     img.save(bg_buffer, format="PNG")
#     bg_buffer.seek(0)
#     bg_reader = ImageReader(bg_buffer)

#     # 建立 PDF 物件
#     pdf_buffer = BytesIO()
#     c = canvas.Canvas(pdf_buffer, pagesize=(1080, 720))
#     c.drawImage(bg_reader, 0, 0, width=1080, height=720)

#     # 設定字體樣式與顏色
#     c.setFont("Helvetica-Bold", 14)  # 可用 Helvetica, Courier, Times-Roman 等
#     c.setFillColor("#2c606d")  # 或 colors.red, colors.black, colors.green 等

#     # 資源清單位置設定
#     y = 185
#     for res in resources:
#         text = f"[{res['type']}] {res['title']}"
#         c.drawString(490, y, text)
#         c.linkURL(res['url'], (490, y, 900, y + 15), relative=0)
#         y -= 25  # 這邊也可調整行距（例如設為 30）

#     c.save()
#     pdf_bytes = pdf_buffer.getvalue()
    
#     # === 轉 PNG 用於顯示 ===
#     images = convert_from_bytes(pdf_bytes)
#     png_buffer = BytesIO()
#     images[0].save(png_buffer, format='PNG')
#     png_bytes = png_buffer.getvalue()

#     # === Streamlit 顯示與下載 ===
#     st.image(png_bytes, caption="生成完成的卡片", use_container_width=True)

#     st.download_button("📄 Download Your Customized Persona", 
#                        data=pdf_bytes, 
#                        file_name=f"persona_{name}.pdf", 
#                        mime="application/pdf")



# if __name__ == "__main__":
#     main()
