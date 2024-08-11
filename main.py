"""
程式名稱：104 人力銀行職缺搜尋與分析工具
版本：1.0
作者：[您的名字]
最後更新日期：[YYYY-MM-DD]

程式概述：
本程式是一個強大的工具，用於自動化搜尋、獲取和分析 104 人力銀行的職缺資訊。
它能夠幫助求職者、HR 專業人員和市場分析師快速獲取大量職缺數據，
並進行初步的數據分析。

主要功能：
1. 根據指定的關鍵字和篩選條件搜索職缺
2. 獲取職缺的基本資訊和詳細資訊
3. 將獲取的資訊匯出為 Excel 文件
4. 提供簡單的職缺統計分析

技術細節：
- 使用的程式語言：Python 3.7+
- 主要依賴庫：asyncio, aiohttp, pandas, tqdm, openpyxl
- 運行環境要求：支持異步操作的 Python 環境

使用說明：
1. 確保已安裝所有必要的依賴庫
2. 在 main 函數中設置搜索參數（關鍵字、最大結果數、排序方式等）
3. 運行程式
4. 程式將自動搜索職缺，獲取詳細信息，並將結果保存為 Excel 文件

注意事項：
- 請遵守 104 人力銀行的使用條款和爬蟲政策
- 大量快速請求可能會導致 IP 被暫時封鎖，請適當控制請求頻率
- 本程式僅供學習和研究使用，請勿用於商業目的

更新日誌：
- [YYYY-MM-DD]：初始版本發布
"""

import asyncio
import random
import aiohttp
import pandas as pd
from tqdm import tqdm
import logging
from openpyxl.utils import get_column_letter

# 設置日誌
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 常數定義
BASE_URL = "https://www.104.com.tw/jobs/search/list"
REFERER_URL = "https://www.104.com.tw/jobs/search/"
JOB_DETAIL_URL_TEMPLATE = "https://www.104.com.tw/job/ajax/content/{job_id}"

# 用戶代理列表，用於模擬不同的瀏覽器訪問，降低被識別為爬蟲的風險
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59",
]

# 排序選項，用於指定職缺列表的排序方式
SORT_OPTIONS = {
    "relevance": "14",  # 符合度
    "experience": "3",  # 經歷
    "education": "4",  # 學歷
    "applicants": "7",  # 應徵人數
    "salary": "13",  # 待遇
    "date": "16",  # 日期
}


class JobSearcher:
    """
    職缺搜索器類別

    負責構建搜索查詢、發送請求並獲取職缺資訊。
    """

    def __init__(
        self,
        keyword,
        max_results=10,
        filter_parameters=None,
        sort_by="relevance",
        ascending_order=False,
    ):
        """
        初始化 JobSearcher 實例

        :param keyword: 搜索關鍵字
        :param max_results: 最大結果數量，預設為 10
        :param filter_parameters: 篩選參數字典，預設為 None
        :param sort_by: 排序方式，預設為 'relevance'
        :param ascending_order: 是否升序排序，預設為 False
        """
        self.keyword = keyword
        self.max_results = max_results
        self.filter_parameters = filter_parameters or {}
        self.sort_by = sort_by
        self.ascending_order = ascending_order
        self.semaphore = asyncio.Semaphore(10)  # 限制同時進行的請求數量

    def build_search_query(self):
        """
        構建搜索查詢字符串

        :return: 完整的查詢字符串
        """
        query_string = f"kwop=7&keyword={self.keyword}&expansionType=area,spec,com,job,wf,wktm&mode=s&jobsource=index_s"
        if self.filter_parameters:
            query_string += "".join(
                [f"&{key}={value}" for key, value in self.filter_parameters.items()]
            )

        sort_parameter = SORT_OPTIONS.get(self.sort_by, "1")
        query_string += (
            f"&order={sort_parameter}&asc={'1' if self.ascending_order else '0'}"
        )
        return query_string

    async def search_jobs(self):
        """
        執行職缺搜索

        :return: 總職缺數量、職缺列表、錯誤列表
        """
        search_query = self.build_search_query()
        job_listings, total_job_count, errors = await self.fetch_all_jobs(search_query)
        return total_job_count, job_listings, errors

    async def fetch_all_jobs(self, search_query):
        """
        獲取所有符合條件的職缺

        :param search_query: 搜索查詢字符串
        :return: 職缺列表、總職缺數量、錯誤列表
        """
        job_listings = []
        total_job_count = 0
        errors = []
        pages_to_fetch = (self.max_results - 1) // 20 + 1

        async with aiohttp.ClientSession() as session:
            tasks = [
                self.fetch_page(session, search_query, page)
                for page in range(1, pages_to_fetch + 1)
            ]

            for future in tqdm(
                asyncio.as_completed(tasks),
                total=pages_to_fetch,
                desc="正在獲取職缺基本資訊",
                unit="頁",
            ):
                search_data, error = await future
                if error:
                    errors.append(error)
                    logger.error(f"獲取頁面時發生錯誤: {error}")
                else:
                    total_job_count = search_data.get("totalCount", 0)
                    new_job_listings = search_data.get("list", [])
                    job_listings.extend(new_job_listings)

                    if len(job_listings) >= self.max_results:
                        break

        return job_listings[: self.max_results], total_job_count, errors

    async def fetch_page(self, session, search_query, page_number):
        """
        獲取單頁職缺資訊

        :param session: aiohttp 客戶端會話
        :param search_query: 搜索查詢字符串
        :param page_number: 頁碼
        :return: 頁面數據、錯誤信息（如果有）
        """
        query_parameters = f"{search_query}&page={page_number}"
        headers = {"User-Agent": random.choice(USER_AGENTS), "Referer": REFERER_URL}
        async with self.semaphore:
            try:
                async with session.get(
                    BASE_URL, params=query_parameters, headers=headers
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    await asyncio.sleep(random.uniform(0.5, 1.5))  # 添加隨機延遲
                    return data.get("data", {}), None
            except aiohttp.ClientError as e:
                return None, str(e)

    async def fetch_job_details(self, session, job_id):
        """
        獲取單個職缺的詳細信息

        :param session: aiohttp 客戶端會話
        :param job_id: 職缺 ID
        :return: 職缺詳細信息、錯誤信息（如果有）
        """
        job_detail_url = JOB_DETAIL_URL_TEMPLATE.format(job_id=job_id)
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Referer": f"https://www.104.com.tw/job/{job_id}",
        }
        async with self.semaphore:
            try:
                async with session.get(job_detail_url, headers=headers) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return data.get("data", {}), None
            except aiohttp.ClientError as e:
                return None, str(e)


class JobTransformer:
    """
    職缺資訊轉換器類別

    負責將原始職缺數據轉換為結構化的字典格式。
    """

    @staticmethod
    def transform_job_list_data(job_data):
        """
        轉換職缺列表數據

        :param job_data: 原始職缺數據
        :return: 轉換後的職缺數據字典
        """
        return {
            "job_id": JobTransformer.extract_job_id(job_data),
            "job_type": job_data["jobType"],
            "job_name": job_data["jobName"],
            "posting_date": job_data["appearDate"],
            "application_count": int(job_data["applyCnt"]),
            "application_description": job_data["applyDesc"],
            "company_name": job_data["custName"],
            "company_address": f"{job_data['jobAddrNoDesc']} {job_data['jobAddress']}",
            "job_url": f"https:{job_data['link']['job']}",
            "job_analysis_url": f"https:{job_data['link']['applyAnalyze']}",
            "company_url": f"https:{job_data['link']['cust']}",
            "longitude": job_data["lon"],
            "latitude": job_data["lat"],
            "required_education": job_data["optionEdu"],
            "experience_required": job_data["periodDesc"],
            "salary_description": job_data["salaryDesc"],
            "salary_high": int(job_data["salaryHigh"]),
            "salary_low": int(job_data["salaryLow"]),
            "tags": job_data["tags"],
        }

    @staticmethod
    def transform_job_detail_data(job_data):
        """
        轉換職缺詳細資訊數據

        :param job_data: 原始職缺詳細數據
        :return: 轉換後的職缺詳細資訊字典
        """
        header = job_data.get("header", {})
        condition = job_data.get("condition", {})
        welfare = job_data.get("welfare", {})
        jobDetail = job_data.get("jobDetail", {})
        contact = job_data.get("contact", {})

        # 從 header 中的 analysisUrl 提取 job_id
        analysis_url = header.get("analysisUrl", "")
        job_id = analysis_url.split("/")[-1] if analysis_url else ""

        return {
            "job_id": job_id,  # 使用從 URL 提取的 job_id
            "job_name": header.get("jobName", ""),
            "company_name": header.get("custName", ""),
            "posting_date": header.get("appearDate", ""),
            "job_category": ", ".join(
                [cat["description"] for cat in jobDetail.get("jobCategory", [])]
            ),
            "work_location": f"{jobDetail.get('addressRegion', '')} {jobDetail.get('addressDetail', '')}",
            "salary": jobDetail.get("salary", ""),
            "job_type": "全職" if jobDetail.get("jobType") == 1 else "兼職",
            "work_period": jobDetail.get("workPeriod", ""),
            "work_exp": condition.get("workExp", ""),
            "education": condition.get("edu", ""),
            "required_skills": ", ".join(
                [skill["description"] for skill in condition.get("skill", [])]
            ),
            "required_certificates": ", ".join(
                [cert["name"] for cert in condition.get("certificate", [])]
            ),
            "welfare_tags": ", ".join(welfare.get("tag", [])),
            "legal_tags": ", ".join(welfare.get("legalTag", [])),
            "job_description": jobDetail.get("jobDescription", ""),
            "hr_name": contact.get("hrName", ""),
            "contact_email": contact.get("email", ""),
            "contact_phone": ", ".join(contact.get("phone", [])),
            "industry": job_data.get("industry", ""),
            "company_size": job_data.get("employees", ""),
            "needed_employees": jobDetail.get("needEmp", ""),
            "manage_responsibility": jobDetail.get("manageResp", ""),
            "business_trip": jobDetail.get("businessTrip", ""),
            "postal_code": job_data.get("postalCode", ""),
            "close_date": job_data.get("closeDate", ""),
            "cust_no": job_data.get("custNo", ""),
            "industry_no": job_data.get("industryNo", ""),
            "china_corp": "是" if job_data.get("chinaCorp", False) else "否",
        }

    @staticmethod
    def extract_job_id(job_data):
        """
        從職缺 URL 中提取 job_id

        :param job_data: 職缺數據
        :return: 提取的 job_id
        """
        job_url = f"https:{job_data['link']['job']}"
        job_id = job_url.split("/job/")[-1]
        if "?" in job_id:
            job_id = job_id.split("?")[0]
        return job_id


async def search_and_export_basic_job_info(job_searcher):
    """
    搜索並匯出基本職缺信息

    :param job_searcher: JobSearcher 實例
    :return: 包含基本職缺信息的 DataFrame
    """
    logger.info("開始搜尋職缺基本資訊")
    total_job_count, job_listings, errors = await job_searcher.search_jobs()
    logger.info(f"找到的總職缺數量: {total_job_count}")
    if errors:
        logger.warning(f"搜尋過程中遇到的錯誤: {errors}")

    transformed_jobs = [
        JobTransformer.transform_job_list_data(job) for job in job_listings
    ]
    jobs_df = pd.DataFrame(transformed_jobs)

    export_to_excel(jobs_df, "job_listings.xlsx")
    return jobs_df


async def fetch_and_export_detailed_job_info(job_searcher, jobs_df):
    """
    獲取並匯出詳細職缺信息

    :param job_searcher: JobSearcher 實例
    :param jobs_df: 包含基本職缺信息的 DataFrame
    :return: 包含詳細職缺信息的 DataFrame
    """
    logger.info("開始獲取職缺詳細資訊")
    job_ids = jobs_df["job_id"].tolist()
    jobs_details = []

    async with aiohttp.ClientSession() as session:
        tasks = [job_searcher.fetch_job_details(session, job_id) for job_id in job_ids]

        for future in tqdm(
            asyncio.as_completed(tasks),
            total=len(job_ids),
            desc="正在獲取職缺詳細資訊",
            unit="個",
        ):
            job_info, error = await future
            if job_info:
                transformed_job_info = JobTransformer.transform_job_detail_data(
                    job_info
                )
                jobs_details.append(transformed_job_info)
            elif error:
                logger.error(f"獲取職缺詳細資訊時發生錯誤: {error}")

    jobs_details_df = pd.DataFrame(jobs_details)
    export_to_excel(jobs_details_df, "job_listings_details.xlsx")
    return jobs_details_df


def export_to_excel(df, filename):
    """
    將 DataFrame 匯出為 Excel 文件

    :param df: 要匯出的 DataFrame
    :param filename: 輸出的 Excel 文件名
    """
    with pd.ExcelWriter(filename, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="職缺資訊")
        worksheet = writer.sheets["職缺資訊"]
        for idx, col in enumerate(df.columns):
            max_length = max(df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.column_dimensions[get_column_letter(idx + 1)].width = max_length
    logger.info(f"資訊已匯出到 {filename}")


def display_job_statistics(jobs_df):
    """
    顯示職缺統計信息

    :param jobs_df: 包含職缺信息的 DataFrame
    """
    print(jobs_df.head(10))
    print(jobs_df.describe())
    print(jobs_df["job_type"].value_counts())
    print(jobs_df["salary_description"].value_counts())


async def main():
    """
    主函數，協調整個程序的運行
    """
    try:
        # 配置區域
        SEARCH_KEYWORD = "你的職務名稱"
        MAX_RESULTS = 100
        SORT_TYPE = "relevance"
        SORT_ASCENDING = False
        FILTER_PARAMETERS = {
            # 在這裡添加您需要的篩選參數
            "ro": 0,  # 0 全部, 1 全職, 2 兼職, 3 高階, 4 派遣
            # 'area': '6001001000,6001016000',  # 地區：台北市, 高雄市 (複選，最多10個)
            # 'isnew': '0',  # 更新日期：0為本日最新,3 三日內,7 一週內,14 二週內,30 一個月內 (單選)
            # 's9': '1,2,4,8',  # 上班時段：日班, 夜班, 大夜班, 假日班 (複選)
            # 's5': '0',  # 輪班：0 不需輪班, 256 輪班 (單選)
            # 'wktm': '1',  # 休假制度：1 週休二日
            # 'remoteWork': '1',  # 上班型態：1為完全遠端, 2部份遠端 (複選)
            # 'jobexp': '1,3,5,10,99',  # 經歷要求：1年以下, 1-3年, 3-5年, 5-10年, 10年以上 (複選)
            # 'indcat': '1001000000,1002000000,1003000000,1001001000,1007000000', # 公司產業：1001000000公司產業電子資訊 /軟體/半導體相關業 1002000000一般製造業 1003000000批發/零售/傳直銷業 1001001000軟體及網絡相關業 1007000000旅遊/休閒/運動業 (複選, 最多5項, 詳細代碼見上表)
            # 'newZone': '1,2,3,4,5',  # 科技園區：竹科, 中科, 南科, 內湖, 南港 (單選)
            # 'zone': '16',  # 公司類型：16為上市上櫃, 5 外商一般, 4 外商資訊 (複選)
            # 'edu': '1,2,3,4,5,6',  # 學歷要求：高中職以下, 高中職, 專科, 大學, 碩士, 博士 (複選)
            # 'wf': '1,2,3,4,5,6,7,8,9,10',  # 福利制度：年終獎金, 三節獎金, 員工旅遊, 分紅配股
            # 'scmin':30000, # 月薪最少
            # 'scmax':50000, # 月薪最高
            # 'excludeJobKeyword': '科技',  # 排除關鍵字
            # 'kwop': '1',  # 只搜尋職務名稱
        }

        job_searcher = JobSearcher(
            keyword=SEARCH_KEYWORD,
            max_results=MAX_RESULTS,
            filter_parameters=FILTER_PARAMETERS,
            sort_by=SORT_TYPE,
            ascending_order=SORT_ASCENDING,
        )

        basic_job_info = await search_and_export_basic_job_info(job_searcher)
        detailed_job_info = await fetch_and_export_detailed_job_info(
            job_searcher, basic_job_info
        )
        display_job_statistics(basic_job_info)

        logger.info("職缺搜尋和分析完成")
        return basic_job_info, detailed_job_info
    except Exception as e:
        logger.error(f"執行過程中發生錯誤: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
