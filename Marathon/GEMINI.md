# 🌍 AI Coach 全球賽事情報庫 (Global Race Intelligence)

> **Purpose**: 規範全球馬拉松賽事資料的收錄、分析與維護。
> **Scope**: `/app/garmin-ai-coach/Marathon/` 下的所有 Markdown 檔案。
> **Core Value**: **專業分析、實戰導向、結構一致**。

## 1. 檔案定位與關係
- **README.md (總索引)**: 以地區分類(五大洲) -> 國家，提供快速對照表（國家）。
- **twn/README.md (國家索引)**: 提供 國家 台灣 快速對照表（名稱、月份、特色、連結）。
- **jpn/README.md (國家索引)**: 提供 國家 日本 快速對照表（名稱、月份、特色、連結）。
- **地區檔案 (詳情庫)**: (如 `twn/info.md`, `jpn/info.md`, `hkg/info.md`, `chn/info.md`, `kor/info.md`) 存放具體賽事的深度分析。
- **INTRO.md**: 存放特殊專題（如世界大滿貫 WMM 深度報告）。

## 2. 賽事收錄標準格式
每一場新增或更新的賽事必須嚴格遵守以下四段式結構，並使用 `###` 作為標題：

### [賽事名稱 (中文)] ([Race Name (English)])
1. **歷史背景 (Historical Background)**: 描述賽事起源、文化意義、城市特色及在跑者心中的地位。
2. **賽道技術分析 (Course Technical Analysis)**: 
   - 地形描述（平緩、起伏、坡度位置）。
   - 環境變量（風向、氣溫、濕度、GPS 訊號）。
   - 具體技術建議（配速策略、步頻調整、核心穩定要求）。
3. **補給特色 (Supply Characteristics)**: 描述官方補給（電解質、能量膠）與民間私補（特色美食），以及補給對腸胃或競技節奏的影響。
4. **教練專業評論 (Coach Professional Comments)**: 
   - 以資深教練視角出發，定義賽事定位（如：PB 聖殿、LSD 訓練跑、耐熱硬仗、心智淬煉）。
   - 提供針對性的訓練重點（如：離心收縮訓練、山徑模擬、熱適應）。

## 3. 維護原則
- **連結一致性**: `README.md` 表格中的「詳情」連結必須精確指向子檔案的 `###` Anchor。
- **日期與作者**: 每個檔案頂部必須包含 `Last Updated` 與 `Author: AI Coach`。
- **數據準確性**: 標籤（如金標、白金標、WMM 候選）必須與最新國際田總 (World Athletics) 資訊同步。
- **專業術語**: 評論中應適時使用科學訓練術語，如 `PB`, `BQ`, `LSD`, `RPE`, `Negative Split`, `離心收縮`, `熱適應`。

## 4. 新增地區檔案範本
若需新增國家檔案（如 `usa/info.md`），請使用以下標頭：
```markdown
# [國旗] [國家/地區名稱] 賽事詳情 ([Country Name] Marathon Details)

> **Purpose**: 紀錄該地區馬拉松賽事的詳細分析、補給特色與教練建議。
> **Parent**: [README.md](README.md)
> **Last Updated**: YYYY-MM-DD
> **Author**: AI Coach
```

## 5. 禁止行為
- 禁止在賽事詳情中使用「略」、「請參考官網」等模糊字眼。
- 禁止破壞 `README.md` 的表格對齊格式。
- 禁止修改現有的賽事歷史與專業評論邏輯，除非有重大的賽道變更。

