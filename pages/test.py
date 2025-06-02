from PIL import Image, ImageDraw, ImageFont
import streamlit as st
from coding.utils import paging
from io import BytesIO
import os
from coding.persona_tools import persona_name, persona_title, get_clean_titles, format_titles_centered
from coding.persona_tools import extract_all_hard_skills_as_text, persona_hardskill, persona_softskill, extract_all_soft_skills_as_text
from coding.persona_tools import parse_ai_text_to_resources, get_ai_resources
import pandas as pd
import fitz  # PyMuPDF
from io import BytesIO
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from pdf2image import convert_from_bytes
from io import BytesIO
from PIL import Image



def save_lang():
    st.session_state["lang_setting"] = st.session_state.get("language_select")

user_image = "https://www.w3schools.com/howto/img_avatar.png"

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


def main():
    st.title("🧑\u200d💼 Ideal Persona")        

    with st.sidebar:
        paging()
        selected_lang = st.selectbox(
            "Language",
            ["English", "繁體中文"],
            index=0,
        )
        st.write("Selected language:", selected_lang)
        st.image(user_image)
        st.write("sidebar loaded")

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


    bg_buffer = BytesIO()
    img.save(bg_buffer, format="PNG")
    bg_buffer.seek(0)
    bg_reader = ImageReader(bg_buffer)

    # 建立 PDF 物件
    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=(1080, 720))
    c.drawImage(bg_reader, 0, 0, width=1080, height=720)

    # 設定字體樣式與顏色
    c.setFont("Helvetica-Bold", 14)  # 可用 Helvetica, Courier, Times-Roman 等
    c.setFillColor("#2c606d")  # 或 colors.red, colors.black, colors.green 等

    # 資源清單位置設定
    y = 185
    for res in resources:
        text = f"[{res['type']}] {res['title']}"
        c.drawString(490, y, text)
        c.linkURL(res['url'], (490, y, 900, y + 15), relative=0)
        y -= 25  # 這邊也可調整行距（例如設為 30）

    c.save()
    pdf_bytes = pdf_buffer.getvalue()
    
    # === 轉 PNG 用於顯示 ===
    images = convert_from_bytes(pdf_bytes)
    png_buffer = BytesIO()
    images[0].save(png_buffer, format='PNG')
    png_bytes = png_buffer.getvalue()

    # === Streamlit 顯示與下載 ===
    st.image(png_bytes, caption="生成完成的卡片", use_container_width=True)

    st.download_button("📄 Download Your Customized Persona", 
                       data=pdf_bytes, 
                       file_name=f"persona_{name}.pdf", 
                       mime="application/pdf")



if __name__ == "__main__":
    main()
