import streamlit as st
import asyncio
from main import (
    JobSearcher,
    search_and_export_basic_job_info,
    fetch_and_export_detailed_job_info,
)
import pandas as pd
import io
import zipfile
import base64

# 定義選項列表
ro_options = [("0", "全部"), ("1", "全職"), ("2", "兼職"), ("3", "高階"), ("4", "派遣")]
isnew_options = [
    ("0", "本日最新"),
    ("3", "三日內"),
    ("7", "一週內"),
    ("14", "二週內"),
    ("30", "一個月內"),
]
s5_options = [("0", "不需輪班"), ("256", "輪班")]
s9_options = [("1", "日班"), ("2", "夜班"), ("4", "大夜班"), ("8", "假日班")]
wktm_options = [("0", "不限"), ("1", "週休二日")]
remote_options = [("1", "完全遠端"), ("2", "部份遠端")]
jobexp_options = [
    ("1", "1年以下"),
    ("3", "1-3年"),
    ("5", "3-5年"),
    ("10", "5-10年"),
    ("99", "10年以上"),
]
indcat_options = [
    ("1001000000", "電子資訊/軟體/半導體相關業"),
    ("1002000000", "一般製造業"),
    ("1003000000", "批發/零售/傳直銷業"),
    ("1001001000", "軟體及網絡相關業"),
    ("1007000000", "旅遊/休閒/運動業"),
]
newZone_options = [
    ("1", "竹科"),
    ("2", "中科"),
    ("3", "南科"),
    ("4", "內湖"),
    ("5", "南港"),
]
zone_options = [("16", "上市上櫃"), ("5", "外商一般"), ("4", "外商資訊")]
edu_options = [
    ("1", "高中職以下"),
    ("2", "高中職"),
    ("3", "專科"),
    ("4", "大學"),
    ("5", "碩士"),
    ("6", "博士"),
]
wf_options = [
    ("1", "年終獎金"),
    ("2", "三節獎金"),
    ("3", "員工旅遊"),
    ("4", "分紅配股"),
]

# 設置頁面標題
st.set_page_config(page_title="104 人力銀行職缺搜索工具", page_icon="🔍", layout="wide")

st.title("104 人力銀行職缺搜索工具")

# 創建兩列佈局
col1, col2 = st.columns(2)

with col1:
    st.header("搜索參數")
    keyword = st.text_input("搜索關鍵字")
    max_results = st.number_input("最大結果數", min_value=1, value=100)
    sort_type = st.selectbox(
        "排序方式",
        ["relevance", "experience", "education", "applicants", "salary", "date"],
    )
    sort_ascending = st.checkbox("升序排序")

with col2:
    st.header("過濾參數")
    filter_parameters = {}

    filter_parameters["ro"] = st.selectbox(
        "工作類型 (單選)",
        [option[0] for option in ro_options],
        format_func=lambda x: dict(ro_options)[x],
    )
    filter_parameters["area"] = st.multiselect(
        "地區 (複選，最多10個)",
        [
            "6001001000",
            "6001002000",
            "6001003000",
            "6001004000",
            "6001005000",
            "6001006000",
            "6001007000",
            "6001008000",
            "6001009000",
            "6001010000",
            "6001011000",
            "6001012000",
            "6001013000",
            "6001014000",
            "6001015000",
            "6001016000",
            "6001017000",
            "6001018000",
            "6001019000",
            "6001020000",
            "6001021000",
            "6001022000",
        ],
        format_func=lambda x: {
            "6001001000": "台北市",
            "6001002000": "新北市",
            "6001003000": "桃園市",
            "6001004000": "台中市",
            "6001005000": "台南市",
            "6001006000": "高雄市",
            "6001007000": "基隆市",
            "6001008000": "新竹市",
            "6001009000": "新竹縣",
            "6001010000": "苗栗縣",
            "6001011000": "彰化縣",
            "6001012000": "南投縣",
            "6001013000": "雲林縣",
            "6001014000": "嘉義市",
            "6001015000": "嘉義縣",
            "6001016000": "屏東縣",
            "6001017000": "宜蘭縣",
            "6001018000": "花蓮縣",
            "6001019000": "台東縣",
            "6001020000": "澎湖縣",
            "6001021000": "金門縣",
            "6001022000": "連江縣",
        }[x],
    )
    if len(filter_parameters["area"]) > 10:
        st.warning("地區最多只能選擇10個")
        filter_parameters["area"] = filter_parameters["area"][:10]

    filter_parameters["isnew"] = st.selectbox(
        "更新日期 (單選)",
        [option[0] for option in isnew_options],
        format_func=lambda x: dict(isnew_options)[x],
    )
    filter_parameters["s9"] = st.multiselect(
        "上班時段 (複選)",
        [option[0] for option in s9_options],
        format_func=lambda x: dict(s9_options)[x],
    )
    filter_parameters["s5"] = st.selectbox(
        "輪班 (單選)",
        [option[0] for option in s5_options],
        format_func=lambda x: dict(s5_options)[x],
    )
    filter_parameters["wktm"] = st.selectbox(
        "休假制度",
        [option[0] for option in wktm_options],
        format_func=lambda x: dict(wktm_options)[x],
    )
    filter_parameters["remoteWork"] = st.multiselect(
        "上班型態 (複選)",
        [option[0] for option in remote_options],
        format_func=lambda x: dict(remote_options)[x],
    )
    filter_parameters["jobexp"] = st.multiselect(
        "工作經驗 (複選)",
        [option[0] for option in jobexp_options],
        format_func=lambda x: dict(jobexp_options)[x],
    )
    filter_parameters["indcat"] = st.multiselect(
        "公司產業 (複選，最多5項)",
        [option[0] for option in indcat_options],
        format_func=lambda x: dict(indcat_options)[x],
    )
    if len(filter_parameters["indcat"]) > 5:
        st.warning("公司產業最多只能選擇5項")
        filter_parameters["indcat"] = filter_parameters["indcat"][:5]

    filter_parameters["newZone"] = st.selectbox(
        "科技園區 (單選)",
        [""] + [option[0] for option in newZone_options],
        format_func=lambda x: dict(newZone_options)[x] if x else "不限",
    )
    filter_parameters["zone"] = st.multiselect(
        "公司類型 (複選)",
        [option[0] for option in zone_options],
        format_func=lambda x: dict(zone_options)[x],
    )
    filter_parameters["edu"] = st.multiselect(
        "學歷要求 (複選)",
        [option[0] for option in edu_options],
        format_func=lambda x: dict(edu_options)[x],
    )
    filter_parameters["wf"] = st.multiselect(
        "福利制度 (複選)",
        [option[0] for option in wf_options],
        format_func=lambda x: dict(wf_options)[x],
    )

    col_min, col_max = st.columns(2)
    with col_min:
        filter_parameters["scmin"] = st.number_input("最低月薪", min_value=0)
    with col_max:
        filter_parameters["scmax"] = st.number_input("最高月薪", min_value=0)

    filter_parameters["excludeJobKeyword"] = st.text_input("排除關鍵字")
    filter_parameters["kwop"] = "1" if st.checkbox("只搜尋職務名稱") else "0"

# 搜索按鈕
if st.button("搜索職缺"):
    job_searcher = JobSearcher(
        keyword=keyword,
        max_results=max_results,
        filter_parameters={
            k: ",".join(v) if isinstance(v, list) else v
            for k, v in filter_parameters.items()
            if v
        },
        sort_by=sort_type,
        ascending_order=sort_ascending,
    )

    with st.spinner("正在搜索職缺並獲取詳細資訊..."):
        basic_job_info = asyncio.run(search_and_export_basic_job_info(job_searcher))
        detailed_job_info = asyncio.run(
            fetch_and_export_detailed_job_info(job_searcher, basic_job_info)
        )

    st.success(f"搜索完成！找到 {len(basic_job_info)} 個職缺。")

    # 處理 'tags' 列的數據類型問題
    if "tags" in basic_job_info.columns:
        basic_job_info["tags"] = basic_job_info["tags"].apply(
            lambda x: str(x) if x is not None else ""
        )
    if "tags" in detailed_job_info.columns:
        detailed_job_info["tags"] = detailed_job_info["tags"].apply(
            lambda x: str(x) if x is not None else ""
        )

    # 顯示結果
    st.subheader("基本職缺資訊")
    st.dataframe(basic_job_info)

    st.subheader("詳細職缺資訊")
    st.dataframe(detailed_job_info)

    # 創建 zip 檔案
    if not basic_job_info.empty and not detailed_job_info.empty:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            basic_excel = io.BytesIO()
            with pd.ExcelWriter(basic_excel, engine="openpyxl") as writer:
                basic_job_info.to_excel(
                    writer, index=False, sheet_name="Basic Job Info"
                )
            zip_file.writestr("job_listings.xlsx", basic_excel.getvalue())

            detailed_excel = io.BytesIO()
            with pd.ExcelWriter(detailed_excel, engine="openpyxl") as writer:
                detailed_job_info.to_excel(
                    writer, index=False, sheet_name="Detailed Job Info"
                )
            zip_file.writestr("job_listings_details.xlsx", detailed_excel.getvalue())

        zip_buffer.seek(0)
        b64 = base64.b64encode(zip_buffer.getvalue()).decode()

        href = f'<a href="data:application/zip;base64,{b64}" download="job_listings.zip">下載所有資訊 (Excel格式)</a>'
        st.markdown(href, unsafe_allow_html=True)

# 添加頁腳
st.markdown("---")
st.markdown("#### 使用說明")
st.markdown(
    """
1. 在左側填寫搜索關鍵字和設置搜索參數。
2. 在右側選擇需要的過濾條件。
3. 點擊「搜索職缺」按鈕開始搜索。
4. 搜索結果將顯示在下方，您可以查看基本資訊和詳細資訊。
5. 使用提供的下載連結獲取完整的 Excel 文件。
"""
)
st.markdown("#### 注意事項")
st.markdown(
    """
- 請遵守 104 人力銀行的使用條款。
- 大量快速請求可能會導致 IP 被暫時封鎖，請適當控制搜索頻率。
- 本工具僅供學習和研究使用，請勿用於商業目的。
"""
)

# 運行指令：streamlit run your_script.py
