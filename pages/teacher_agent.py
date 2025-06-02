import ast
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

from coding.utils import paging, merge_csv

# ------------------------
# 中英文對照字典 (i18n)
# ------------------------
i18n = {
    "zh": {
        "title": "🔍｜實習職缺導航｜",
        "language_label": "語言切換",
        "selected_lang": "已選語言：",
        "current_search": "🔑 目前搜尋條件:",
        "no_keywords": "*尚未輸入關鍵字*",
        "clear_keywords": "🧹 清除所有關鍵字",
        "chat_placeholder": "請輸入有興趣的公司或職缺或技能來搜尋實習職缺...",
        "saved_jobs_header": "🗂 你已儲存的職缺清單",
        "jobs_count": "共 {n} 個職缺",
        "no_saved_jobs": "尚未儲存任何職缺。",
        "job_desc_label": "職缺描述:",
        "job_keywords_label": "關鍵技能:",
        "apply_button": "🔗 前往投遞頁面",
        "remove_button": "移除這個職缺",
        "clear_saved": "❌ 清除所有已儲存職缺",
        "export_header": "📤 匯出已儲存職缺",
        "download_button": "📥 點我下載 CSV",
        "no_export": "尚未儲存任何職缺，無法匯出。",
    },
    "en": {
        "title": "🔍｜Internship Navigator｜",
        "language_label": "Language",
        "selected_lang": "Selected language:",
        "current_search": "🔑 Current Search Conditions:",
        "no_keywords": "*No keywords entered yet*",
        "clear_keywords": "🧹 Clear all keywords",
        "chat_placeholder": "Type a company, job title, or skill to search internships...",
        "saved_jobs_header": "🗂 Your Saved Jobs List",
        "jobs_count": "{n} saved jobs",
        "no_saved_jobs": "No saved jobs yet.",
        "job_desc_label": "Job Description:",
        "job_keywords_label": "Job Keywords:",
        "apply_button": "🔗 Go to application page",
        "remove_button": "Remove this job",
        "clear_saved": "❌ Clear all saved jobs",
        "export_header": "📤 Export Saved Jobs",
        "download_button": "📥 Download CSV",
        "no_export": "No saved jobs to export.",
    }
}

def load_job_data(lang):
    if lang == "English":
        df = pd.read_csv("pages/merged_jobs_en.csv")
        df.rename(columns={
            'Company': 'comp',
            'Job Title': 'job_title',
            'Full Description': 'job_desc',
            'Tags': 'job_tags',
            'Job URL': 'job_url'
        }, inplace=True)
    else:
        df = pd.read_csv("pages/merged_jobs.csv")
        df.rename(columns={
            '公司名稱': 'comp',
            '職缺名稱': 'job_title',
            '完整描述': 'job_desc',
            '技能關鍵字': 'job_tags',
            '職缺網址': 'job_url'
        }, inplace=True)
    df.fillna("", inplace=True)
    return df

def count_keyword_occurrences(text, keyword):
    if not isinstance(text, str):
        return 0
    return text.lower().count(keyword)

def format_job_tags(tag_string):
    try:
        tags = ast.literal_eval(tag_string)
        tags = [t.strip() for t in tags if isinstance(t, str) and t.strip()]
        return '、'.join(tags)
    except:
        return ""

def unified_search_multiple_or(df, keywords):
    filtered = df.copy()
    scores = [0] * len(filtered)
    for keyword in keywords:
        keyword = keyword.lower().strip()
        for i, row in filtered.iterrows():
            score = 0
            title_count = count_keyword_occurrences(row['job_title'], keyword)
            desc_count = count_keyword_occurrences(row['job_desc'], keyword)
            comp_count = count_keyword_occurrences(row['comp'], keyword)
            try:
                tags = ast.literal_eval(row['job_tags'])
                tags_lower = [t.lower().strip() for t in tags if isinstance(t, str)]
                tags_count = sum(keyword in t for t in tags_lower)
            except:
                tags_count = 0

            score += title_count * 10
            score += desc_count * 2
            score += tags_count * 6
            score += comp_count * 10
            scores[i] += score

    filtered['score'] = scores
    filtered = filtered[filtered['score'] > 0]

    if filtered.empty:
        return pd.DataFrame(columns=['comp', 'job_title', 'job_desc', 'job_tags', 'job_url'])

    filtered.sort_values(by='score', ascending=False, inplace=True)
    filtered['job_tags'] = filtered['job_tags'].apply(format_job_tags)
    return filtered.head(20)[['comp', 'job_title', 'job_desc', 'job_tags', 'job_url']].reset_index(drop=True)

def generate_response_multiple(keywords, job_df):
    return unified_search_multiple_or(job_df, keywords)

def save_lang():
    st.session_state["lang_setting"] = st.session_state.get("language_select")

def show_saved_jobs(T):
    saved_jobs_count_placeholder = st.empty()
    if st.session_state.saved_jobs:
        saved_jobs_count_placeholder.write(
            T["jobs_count"].format(n=len(st.session_state.saved_jobs))
        )
    else:
        saved_jobs_count_placeholder.write(T["no_saved_jobs"])

    for i, job in enumerate(st.session_state.saved_jobs, start=1):
        unique_key = job['Job Title'] + "__" + job['Company']
        if unique_key in st.session_state.hidden_saved_jobs:
            continue

        with st.expander(f"{i}. {job['Job Title']} ({job['Company']})", expanded=False):
            full_desc = job.get('Job Description', 'N/A')
            if full_desc.strip() == "":
                full_desc = "N/A"
            st.markdown(f"**{T['job_desc_label']}** {full_desc}")

            keywords = job.get('Job Keywords', 'N/A')
            if keywords.strip() == "":
                keywords = "N/A"
            st.markdown(f"**{T['job_keywords_label']}** {keywords}")

            url = job.get('Job URL', '').strip()
            if url:
                if not url.startswith("http"):
                    url = "https://" + url
                st.markdown(f"""
                    <a href="{url}" target="_blank" rel="noopener noreferrer"
                    style="display:inline-block; padding:8px 16px; background-color:#4CAF50; color:white; text-decoration:none;
                            border-radius:6px; font-weight:bold; font-size:15px;">
                    {T['apply_button']}
                    </a>
                    """, unsafe_allow_html=True)
            else:
                st.markdown(f"{T['apply_button'][:2]}：無")

            if st.button(f"{T['remove_button']}", key=f"remove_{unique_key}"):
                st.session_state.hidden_saved_jobs.add(unique_key)

def main():
    #st.title(i18n["zh"]["title"])  # 畫面尚未載入前先放一行預設，稍後會更新

    if "lang_setting" not in st.session_state:
        st.session_state.lang_setting = "English"

    # 側邊欄：導航 & 語言切換
    user_image = "https://www.w3schools.com/howto/img_avatar.png"
    with st.sidebar:
        # 導航
        paging()

        # 語言選擇
        selected_lang = st.selectbox(
            i18n["zh"]["language_label"],  # 先顯示中文標籤，之後動態覆蓋
            ["English", "繁體中文"],
            index=0 if st.session_state.lang_setting == "English" else 1,
            on_change=save_lang,
            key="language_select",
        )
        st.session_state.lang_setting = selected_lang
        lang_code = "zh" if st.session_state.lang_setting == "繁體中文" else "en"
        T = i18n[lang_code]
        st.write(f"{T['selected_lang']} {selected_lang}")
        st.image(user_image, use_container_width=True)

    # 根據當前語言顯示標題
    lang_code = "zh" if st.session_state.lang_setting == "繁體中文" else "en"
    T = i18n[lang_code]
    st.title(T["title"])

    # Merge CSV（如有需要，取消註解）
    # merge_csv()

    # 載入對應語系的資料
    job_df = load_job_data(st.session_state.lang_setting)

    # 顯示目前搜尋條件
    st.markdown(f"### {T['current_search']}")
    if st.session_state.get("search_keywords"):
        keyword_str = "、".join(st.session_state.search_keywords)
        st.markdown(f"**{keyword_str}**")
    else:
        st.markdown(T["no_keywords"])

    # 清除所有關鍵字按鈕
    if st.button(T["clear_keywords"]):
        st.session_state.search_keywords = []
        st.session_state.result_df = pd.DataFrame()
        st.session_state.selected_jobs = []
        st.rerun()

    # 聊天輸入框
    user_input = st.chat_input(T["chat_placeholder"], key="chat_input")
    if user_input:
        st.chat_message("user").write(user_input)
        if user_input.lower() not in [k.lower() for k in st.session_state.search_keywords]:
            st.session_state.search_keywords.append(user_input.strip())
        st.session_state.result_df = generate_response_multiple(
            st.session_state.search_keywords, job_df
        )
        st.session_state.selected_jobs = []
        st.rerun()

    # 顯示搜尋結果
    if not st.session_state.get("result_df", pd.DataFrame()).empty:
        df = st.session_state.result_df.rename(columns={
            'comp': 'Company',
            'job_title': 'Job Title',
            'job_desc': 'Job Description',
            'job_tags': 'Job Keywords',
            'job_url': 'Job URL'
        })

        df["Short Description"] = df["Job Description"].apply(
            lambda x: x[:60] + "..." if len(x) > 60 else x
        )
        df = df[['Company', 'Job Title', 'Short Description', 'Job Description', 'Job Keywords', 'Job URL']]

        gb = GridOptionsBuilder.from_dataframe(df.drop(columns=['Job Description', 'Job URL']))
        gb.configure_selection(selection_mode="multiple", use_checkbox=True)
        gb.configure_column("Short Description", header_name="Job Description", wrapText=True, autoHeight=True)
        gb.configure_grid_options(domLayout='autoHeight')
        grid_options = gb.build()

        grid_response = AgGrid(
            df.drop(columns=['Job Description', 'Job URL']),
            gridOptions=grid_options,
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            enable_enterprise_modules=False,
            fit_columns_on_grid_load=True,
            height=400,
            key=st.session_state.aggrid_key
        )

        selected_rows = grid_response['selected_rows']
        if not isinstance(selected_rows, list) and hasattr(selected_rows, 'empty'):
            selected_rows = selected_rows.to_dict('records')

        if selected_rows and len(selected_rows) > 0:
            for job in selected_rows:
                if not any(
                    saved_job['Job Title'] == job['Job Title'] and
                    saved_job['Company'] == job['Company']
                    for saved_job in st.session_state.saved_jobs
                ):
                    full_job = job_df[
                        (job_df['comp'] == job['Company']) &
                        (job_df['job_title'] == job['Job Title'])
                    ]
                    if not full_job.empty:
                        full_job_dict = {
                            'Company': job['Company'],
                            'Job Title': job['Job Title'],
                            'Job Description': full_job.iloc[0]['job_desc'],
                            'Job Keywords': full_job.iloc[0]['job_tags'],
                            'Job URL': full_job.iloc[0]['job_url'],
                        }
                        st.session_state.saved_jobs.append(full_job_dict)

    # 顯示已儲存職缺
    if st.session_state.saved_jobs:
        st.markdown("---")
        st.markdown(f"### {T['saved_jobs_header']}")

        if st.button(T["clear_saved"]):
            st.session_state.saved_jobs = []
            st.session_state.hidden_saved_jobs = set()
            st.session_state.aggrid_key = "job_grid_" + str(pd.Timestamp.now().timestamp())

        show_saved_jobs(T)

    # 匯出已儲存職缺
    st.markdown("---")
    st.markdown(f"### {T['export_header']}")
    if st.session_state.saved_jobs:
        export_df = pd.DataFrame(st.session_state.saved_jobs)
        export_df.to_csv("pages/saved_jobs.csv", index=False, encoding='utf-8-sig')
        csv_data = export_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label=T["download_button"],
            data=csv_data,
            file_name="saved_jobs.csv",
            mime="text/csv"
        )
    else:
        st.info(T["no_export"])

if __name__ == "__main__":
    # 初始化一些 session_state 變數
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

    main()

# import ast
# import streamlit as st
# import pandas as pd
# from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
# from coding.utils import paging, merge_csv

# def load_job_data(lang):
#     if lang == "English":
#         df = pd.read_csv("pages/merged_jobs_en.csv")
#         df.rename(columns={
#             'Company': 'comp',
#             'Job Title': 'job_title',
#             'Full Description': 'job_desc',
#             'Tags': 'job_tags',
#             'Job URL': 'job_url'
#         }, inplace=True)
#     else:
#         df = pd.read_csv("pages/merged_jobs.csv")
#         df.rename(columns={
#             '公司名稱': 'comp',
#             '職缺名稱': 'job_title',
#             '完整描述': 'job_desc',
#             '技能關鍵字': 'job_tags',
#             '職缺網址': 'job_url'
#         }, inplace=True)
#     df.fillna("", inplace=True)
#     return df

# def count_keyword_occurrences(text, keyword):
#     if not isinstance(text, str):
#         return 0
#     return text.lower().count(keyword)

# def format_job_tags(tag_string):
#     try:
#         tags = ast.literal_eval(tag_string)
#         tags = [t.strip() for t in tags if isinstance(t, str) and t.strip()]
#         return '、'.join(tags)
#     except:
#         return ""

# def unified_search_multiple_or(df, keywords):
#     filtered = df.copy()
#     scores = [0] * len(filtered)
#     for keyword in keywords:
#         keyword = keyword.lower().strip()
#         for i, row in filtered.iterrows():
#             score = 0
#             title_count = count_keyword_occurrences(row['job_title'], keyword)
#             desc_count = count_keyword_occurrences(row['job_desc'], keyword)
#             comp_count = count_keyword_occurrences(row['comp'], keyword) 
#             try:
#                 tags = ast.literal_eval(row['job_tags'])
#                 tags_lower = [t.lower().strip() for t in tags if isinstance(t, str)]
#                 tags_count = sum(keyword in t for t in tags_lower)
#             except:
#                 tags_count = 0

#             score += title_count * 10
#             score += desc_count * 2
#             score += tags_count * 6
#             score += comp_count * 10
#             scores[i] += score

#     filtered['score'] = scores
#     filtered = filtered[filtered['score'] > 0]

#     if filtered.empty:
#         return pd.DataFrame(columns=['comp', 'job_title', 'job_desc', 'job_tags', 'job_url'])

#     filtered.sort_values(by='score', ascending=False, inplace=True)
#     filtered['job_tags'] = filtered['job_tags'].apply(format_job_tags)
#     return filtered.head(20)[['comp', 'job_title', 'job_desc', 'job_tags', 'job_url']].reset_index(drop=True)

# def generate_response_multiple(keywords, job_df):
#     return unified_search_multiple_or(job_df, keywords)

# def save_lang():
#     st.session_state["lang_setting"] = st.session_state.get("language_select")

# def show_saved_jobs():
#     saved_jobs_count_placeholder = st.empty()
#     if st.session_state.saved_jobs:
#         saved_jobs_count_placeholder.write(f"共 {len(st.session_state.saved_jobs)} 個職缺")
#     else:
#         saved_jobs_count_placeholder.write("尚未儲存任何職缺。")

#     for i, job in enumerate(st.session_state.saved_jobs, start=1):
#         unique_key = job['Job Title'] + "__" + job['Company']
#         if unique_key in st.session_state.hidden_saved_jobs:
#             continue

#         with st.expander(f"{i}. {job['Job Title']} ({job['Company']})", expanded=False):
#             full_desc = job.get('Job Description', 'N/A')
#             if full_desc.strip() == "":
#                 full_desc = "N/A"
#             st.markdown(f"**職缺描述:** {full_desc}")

#             keywords = job.get('Job Keywords', 'N/A')
#             if keywords.strip() == "":
#                 keywords = "N/A"
#             st.markdown(f"**關鍵技能:** {keywords}")

#             url = job.get('Job URL', '').strip()
#             if url:
#                 if not url.startswith("http"):
#                     url = "https://" + url
#                 st.markdown(f"""
#                     <a href="{url}" target="_blank" rel="noopener noreferrer"
#                     style="display:inline-block; padding:8px 16px; background-color:#4CAF50; color:white; text-decoration:none;
#                             border-radius:6px; font-weight:bold; font-size:15px;">
#                     🔗 前往投遞頁面
#                     </a>
#                     """, unsafe_allow_html=True)
#             else:
#                 st.markdown("職缺連結：無")

#             if st.button(f"移除這個職缺", key=f"remove_{unique_key}"):
#                 st.session_state.hidden_saved_jobs.add(unique_key)

# user_image = "https://www.w3schools.com/howto/img_avatar.png"

# def main():
#     # merge_csv()

#     st.title("🔍｜實習職缺導航｜")

#     if "lang_setting" not in st.session_state:
#         st.session_state.lang_setting = "English"

#     if "search_keywords" not in st.session_state:
#         st.session_state.search_keywords = []
#     if "result_df" not in st.session_state:
#         st.session_state.result_df = pd.DataFrame()
#     if "selected_jobs" not in st.session_state:
#         st.session_state.selected_jobs = []
#     if "saved_jobs" not in st.session_state:
#         st.session_state.saved_jobs = []
#     if "hidden_saved_jobs" not in st.session_state:
#         st.session_state.hidden_saved_jobs = set()
#     if "aggrid_key" not in st.session_state:
#         st.session_state.aggrid_key = "job_grid"

#     with st.sidebar:
#         paging()
#         selected_lang = st.selectbox(
#             "Language",
#             ["English", "繁體中文"],
#             index=0 if st.session_state.lang_setting == "English" else 1,
#             on_change=save_lang,
#             key="language_select",
#         )
#         lang_setting = st.session_state.get("lang_setting", selected_lang)
#         st.session_state["lang_setting"] = lang_setting

#         st.image(user_image)

#     # 根據語言設定讀取對應資料
#     job_df = load_job_data(lang_setting)

#     st.markdown(f"### 🔑 目前搜尋條件:")
#     if st.session_state.search_keywords:
#         keyword_str = "、".join(st.session_state.search_keywords)
#         st.markdown(f"**{keyword_str}**")
#     else:
#         st.markdown("*尚未輸入關鍵字*")

#     if st.button("🧹 清除所有關鍵字"):
#         st.session_state.search_keywords = []
#         st.session_state.result_df = pd.DataFrame()
#         st.session_state.selected_jobs = []
#         st.rerun()

#     user_input = st.chat_input("請輸入有興趣的公司或職缺或技能來搜尋實習職缺...", key="chat_input")

#     if user_input:
#         st.chat_message("user").write(user_input)
#         if user_input.lower() not in [k.lower() for k in st.session_state.search_keywords]:
#             st.session_state.search_keywords.append(user_input.strip())
#         st.session_state.result_df = generate_response_multiple(st.session_state.search_keywords, job_df)
#         st.session_state.selected_jobs = []
#         st.rerun()

#     if not st.session_state.result_df.empty:
#         df = st.session_state.result_df.rename(columns={
#             'comp': 'Company',
#             'job_title': 'Job Title',
#             'job_desc': 'Job Description',
#             'job_tags': 'Job Keywords',
#             'job_url': 'Job URL'
#         })

#         df["Short Description"] = df["Job Description"].apply(lambda x: x[:60] + "..." if len(x) > 60 else x)
#         df = df[['Company', 'Job Title', 'Short Description', 'Job Description', 'Job Keywords', 'Job URL']]

#         gb = GridOptionsBuilder.from_dataframe(df.drop(columns=['Job Description', 'Job URL']))
#         gb.configure_selection(selection_mode="multiple", use_checkbox=True)
#         gb.configure_column("Short Description", header_name="Job Description", wrapText=True, autoHeight=True)
#         gb.configure_grid_options(domLayout='autoHeight')
#         grid_options = gb.build()

#         grid_response = AgGrid(
#             df.drop(columns=['Job Description', 'Job URL']),
#             gridOptions=grid_options,
#             update_mode=GridUpdateMode.SELECTION_CHANGED,
#             enable_enterprise_modules=False,
#             fit_columns_on_grid_load=True,
#             height=400,
#             key=st.session_state.aggrid_key
#         )

#         selected_rows = grid_response['selected_rows']
#         if not isinstance(selected_rows, list) and hasattr(selected_rows, 'empty'):
#             selected_rows = selected_rows.to_dict('records')

#         if selected_rows and len(selected_rows) > 0:
#             for job in selected_rows:
#                 if not any(saved_job['Job Title'] == job['Job Title'] and
#                            saved_job['Company'] == job['Company']
#                            for saved_job in st.session_state.saved_jobs):
#                     full_job = job_df[
#                         (job_df['comp'] == job['Company']) &
#                         (job_df['job_title'] == job['Job Title'])
#                     ]
#                     if not full_job.empty:
#                         full_job_dict = {
#                             'Company': job['Company'],
#                             'Job Title': job['Job Title'],
#                             'Job Description': full_job.iloc[0]['job_desc'],
#                             'Job Keywords': full_job.iloc[0]['job_tags'],
#                             'Job URL': full_job.iloc[0]['job_url'],
#                         }

#                         st.session_state.saved_jobs.append(full_job_dict)

#     if st.session_state.saved_jobs:
#         st.markdown("---")
#         st.markdown("### 🗂 你已儲存的職缺清單")

#         if st.button("❌ 清除所有已儲存職缺"):
#             st.session_state.saved_jobs = []
#             st.session_state.hidden_saved_jobs = set()
#             st.session_state.aggrid_key = "job_grid_" + str(pd.Timestamp.now().timestamp())

#         show_saved_jobs()

#     st.markdown("---")
#     st.markdown("### 📤 匯出已儲存職缺")

#     if st.session_state.saved_jobs:
#         export_df = pd.DataFrame(st.session_state.saved_jobs)
#         export_df.to_csv("pages/saved_jobs.csv", index=False, encoding='utf-8-sig')
#         csv = export_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
#         st.download_button(
#             label="📥 點我下載 CSV",
#             data=csv,
#             file_name="saved_jobs.csv",
#             mime="text/csv"
#         )
#     else:
#         st.info("尚未儲存任何職缺，無法匯出。")

# if __name__ == "__main__":
#     main()
