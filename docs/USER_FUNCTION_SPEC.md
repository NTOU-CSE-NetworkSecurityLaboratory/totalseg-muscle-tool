# 使用者功能與情境總表

這份文件只講一件事：

這個工具目前到底提供了哪些功能，使用者在什麼情境下會用到它，輸入什麼，期待得到什麼結果。

這份文件故意不從程式檔案、模組、CLI 架構去講。

## 1. 產品定位

這個工具是拿來處理醫學影像 case 的。

目前主要服務 3 種需求：

1. 對 DICOM 影像做 AI 分割
2. 把分割結果轉成可讀的數值與圖片
3. 把 AI 結果拿去和人工標註做比較

使用者通常不是只想要一個 mask 檔，而是想同時知道：

- AI 分到了哪裡
- 每一張 slice 的數值是多少
- 哪些 slice 有結果
- 圖和數值能不能對得起來
- AI 和人工標註差多少

## 2. 主要使用者情境

### 情境 A：我要對一個 CT case 做肌肉分析

使用者會提供一個 CT 的 DICOM 資料夾，指定 task，執行分割。

使用者期待得到：

- segmentation 結果
- 對應的 CSV 數值
- 對應的 PNG overlay

這是目前最核心的使用情境。

### 情境 B：我要對一個 MRI case 做對應分析

使用者會提供 MRI 的 DICOM 資料夾。

系統需要依 MRI 規則使用可用 task，不能直接把 CT task 原封不動套上去。

使用者期待得到：

- MRI 對應 task 的 segmentation
- MRI case 的 CSV
- MRI case 的 PNG overlay

### 情境 C：我只想看某一段切片，不想跑整包

這是很重要的使用情境。

使用者不一定要看整個 case，有時只想看中間段、腰椎附近、特定 slice 區段。

例如：

- 只看第 20 到第 40 張
- 只看中間段
- 只看臨床上有興趣的部位

使用者期待：

- segmentation 的數值計算只針對指定範圍
- CSV 只反映指定範圍的結果
- PNG 只輸出指定範圍
- 超出病例範圍時要自動修正或明確報錯

### 情境 D：我想知道脊椎層級

有些使用者不是只想看肌肉輪廓，還想知道目前看到的是哪一節脊椎附近。

所以系統支援脊椎相關功能，目的不是只多做一份 segmentation，而是幫助使用者定位。

使用者期待：

- 可以啟用脊椎分析
- 影像上能顯示脊椎標記
- 知道目前 slice 對應的大致脊椎層級

### 情境 E：我要一次處理很多病例

臨床或研究時，常常不是跑一個 case，而是一次跑一批。

使用者會提供一個根目錄，裡面可能有很多病例資料夾。

使用者期待：

- 系統自動找出有效病例
- 可以勾選要跑哪些病例
- 可以看到每個病例的處理狀態
- 某個病例失敗時，其他病例的行為要明確
- 最後有批次 log 可追

### 情境 F：我要用圖片肉眼確認 AI 有沒有畫對

單靠 CSV 不夠。

使用者需要看到原始影像上面疊了哪些 mask，才知道 AI 是不是真的分到正確位置。

使用者期待：

- 每張 slice 都能輸出對應 PNG
- 有 mask 的地方會有顏色標示
- 同一張圖上若有多個結構，要能區分顏色
- 圖上要能看 legend
- 如果有開脊椎功能，圖上也能看到脊椎標記

### 情境 G：我要做 AI 跟人工標註的比較

研究或驗證時，使用者會拿 AI mask 和 manual mask 做比較。

使用者期待：

- 能選 AI 檔案
- 能選 manual 檔案
- 系統能算出 Dice
- 系統能顯示雙方的面積差異
- 系統要告訴我它拿哪一張 slice 來比

### 情境 H：我遇到授權或執行錯誤，但我想繼續工作

這不是附帶需求，而是真正的使用情境。

像 TotalSegmentator 某些 task 可能需要授權，或執行時可能遇到設定壞掉、權限、記憶體等問題。

使用者期待：

- 系統能告訴我失敗原因
- 如果是授權問題，可以補金鑰
- 補完後可以重試失敗病例
- 不要整批工作直接變成黑盒子

## 3. 功能總表

以下是目前應該被視為正式功能的內容。

### 功能 1：讀取與辨識病例

系統可以處理單一病例，也可以處理多病例根目錄。

目前辨識邏輯包含：

- 支援 `.dcm`
- 也支援部分沒有副檔名的 DICOM
- 會自動掃描子資料夾
- 會略過 `_output`
- 會略過 `TotalSeg_Backend`

使用者在這個階段最在意的是：

- 哪些資料夾被當成病例
- 一共有幾個可跑的 case
- 每個 case 有多少 slices

### 功能 2：依影像類型選擇可用任務

系統不是所有 task 都對所有 modality 一樣。

目前有 CT 與 MRI 兩種主要影像類型。

使用者的要求是：

- CT 看到的是 CT 可用 task
- MRI 看到的是 MRI 可用 task
- MRI 下如果 task 有對應 MR 版本，系統要用對的版本

目前可見的 task 範圍包含：

- `abdominal_muscles`
- `aortic_sinuses`
- `appendicular_bones`
- `appendicular_bones_mr`
- `body`
- `body_mr`
- `brain_structures`
- `breasts`
- `cerebral_bleed`
- `coronary_arteries`
- `craniofacial_structures`
- `face`
- `face_mr`
- `head_glands_cavities`
- `head_muscles`
- `headneck_bones_vessels`
- `headneck_muscles`
- `heartchambers_highres`
- `hip_implant`
- `kidney_cysts`
- `liver_segments`
- `liver_segments_mr`
- `lung_nodules`
- `lung_vessels`
- `oculomotor_muscles`
- `pleural_pericard_effusion`
- `thigh_shoulder_muscles`
- `thigh_shoulder_muscles_mr`
- `tissue_4_types`
- `tissue_types`
- `tissue_types_mr`
- `ventricle_parts`
- `vertebrae_body`
- `vertebrae_mr`
- `total`
- `total_mr`

這代表產品上不能只說「可以選 task」。

必須說清楚：

- task 會隨 modality 改變
- MRI 不是照搬 CT 規則

### 功能 3：執行主要分割

這是整個產品的主流程起點。

使用者提供：

- DICOM case
- modality
- task
- 是否快速模式

系統會產生：

- segmentation 輸出資料夾
- mask 檔
- statistics 資料

如果這一步沒成功，後面 CSV 和 PNG 都不應該被視為成功。

### 功能 4：快速模式

使用者可以開啟 fast mode。

這代表：

- 速度優先
- 精度可能較低
- 比較適合 preview 或資源有限時使用

這個選項會影響：

- segmentation 執行方式
- 輸出資料夾命名
- CSV 檔名
- 後續 draw 讀取哪個 segmentation 結果

### 功能 5：脊椎相關功能

脊椎功能是正式功能，不是裝飾。

它有兩層需求。

第一層是脊椎 segmentation。

當使用者有開啟脊椎功能，而且主 task 不是整體 total 類時，系統會另外跑脊椎相關分割，產生脊椎輸出與脊椎 CSV。

第二層是脊椎標記顯示。

在畫 PNG overlay 時，系統會試著找出該 slice 是否對應某個脊椎 mask，並把脊椎名稱畫到圖上。

使用者在這個功能上的期待包含：

- 知道目前看到的是哪一節附近
- 輔助判讀中段切片或特定位置
- 在肌肉分析時能用脊椎作為定位參考

### 功能 6：切片範圍控制

這是非常重要的正式功能。

使用者可以輸入：

- `slice_start`
- `slice_end`

目的包含：

- 只分析前段
- 只分析中段
- 只分析末段
- 只看某個臨床感興趣區間
- 降低不必要的處理量

系統在這個功能上必須做到：

- 起始值必須是整數
- 結束值必須是整數
- 起始值不能小於 1
- 起始值不能大於結束值
- 起始值不能超過病例總 slice 數
- 結束值若超過病例總 slice 數，要能自動夾限
- 夾限後要能給 warning

這個功能會影響：

- CSV 計算
- PNG 輸出
- 使用者對中間區段的專注分析

### 功能 7：CSV 數值輸出

CSV 是主要正式輸出，不是附屬品。

它的用途包括：

- 開 Excel 檢查
- 看每張 slice 的變化
- 做統計分析
- 交給其他人二次處理

目前 CSV 的內容包含 4 段：

1. 每一張 slice 的面積
2. 每一張 slice 的平均 HU
3. 每一張 slice 的 HU 標準差
4. summary 資訊

summary 目前包含：

- `structure`
- `pixelcount`
- `volume_cm3`
- `mean_hu`

使用者在這個功能上最在意的事有：

- 第 1 張是不是就代表第 1 張 DICOM
- 第 N 張 CSV 能不能對到第 N 張 PNG
- 左右肌肉是分開還是合併

目前行為是：

- 面積段保持左右分開
- HU 平均值段會合併左右
- HU 標準差段會合併左右
- summary 也會依結構做合併邏輯

### 功能 8：HU 計算時的 erosion

這也是正式功能，不只是內部參數。

使用者可以設定 `erosion_iters`。

它的目的，是讓 HU 計算不要太受邊緣影響。

目前這個參數影響：

- 每張 slice 的 mean HU
- 每張 slice 的 HU std
- eroded PNG 輸出

它不直接改變面積和體積本身的統計邏輯。

使用者期待的是：

- 可以控制邊緣收縮程度
- 在數值分析時有比較穩定的 HU
- 圖像上能看到 erosion 後版本

### 功能 9：PNG overlay 輸出

這是主要視覺驗證功能。

系統會把 mask 疊回原始 DICOM slice，逐張輸出 PNG。

目前輸出包含：

- 一般 PNG overlay
- `png_eroded` 版本

圖上目前可包含：

- 灰階原始影像
- 多個結構的色彩 overlay
- legend
- 脊椎文字標記

使用者最在意的是：

- 有分到的 slice 要有畫出來
- 沒分到的 slice 不要誤導
- 圖片順序要正確
- 如果只看中間段，輸出的也應該只是一段

### 功能 10：自動在分割後接著出圖

有些使用者不想分兩步做。

所以系統支援分割完成後自動跑 draw。

這代表產品上有兩種工作方式：

1. 只做 segmentation + CSV
2. segmentation 完後自動把 PNG 也做出來

使用者期待的是：

- 不需要手動再跑第二次
- 同一組參數能一路延續到 draw
- 切片範圍與 fast mode 等設定要一致帶過去

### 功能 11：批次處理

批次處理也是正式功能。

使用者可以：

- 掃描一個根目錄
- 看見多個病例
- 勾選或取消勾選個別病例
- 一次執行多個病例

使用者期待：

- 每個病例有自己的狀態
- 能知道哪個在跑、哪個成功、哪個失敗
- 最後能知道整批完成情況
- 有 session log 可以追查

### 功能 12：批次中的停止、失敗與重試

批次工作不可能永遠一次成功。

所以使用者會需要：

- 停止目前批次
- 某個病例失敗後知道原因
- 針對上一個失敗病例重試

這些在產品上都應該視為功能，而不是例外。

### 功能 13：授權處理

部分 task 可能遇到 TotalSegmentator 授權需求。

使用者需要：

- 知道目前是授權問題
- 有地方輸入授權金鑰
- 可以貼原始 key
- 也可以貼 `totalseg_set_license -l ...` 這種指令格式
- 補完授權後能重試失敗病例

這代表授權流程本身就是產品功能的一部分。

### 功能 14：錯誤診斷與提示

除了授權之外，還有其他常見失敗情境，例如：

- GPU 記憶體不足
- 權限不足
- 環境缺套件
- TotalSegmentator 設定檔壞掉
- 路徑有特殊字元
- 找不到 DICOM
- 找不到 mask

使用者期待系統不是只回傳失敗，而是要能提供：

- 失敗原因
- 建議處理方式
- 哪個病例失敗
- 批次 log

### 功能 15：AI 與人工標註比較

這條功能和主分割流程不同，但也很重要。

使用者會提供：

- AI mask
- manual mask

系統目前會：

- 必要時把 AI mask 對齊到 manual mask
- 找 manual mask 第一個有內容的 slice
- 在那張 slice 上比較
- 算出 Dice
- 算出 AI 面積
- 算出 manual 面積
- 給一個 quality 等級

使用者期待知道：

- 比較的是哪一張
- 分數多少
- 面積差多少
- 這個結果是好還是需要人工再看

## 4. 重要輸入

從使用者角度看，目前最重要的輸入有：

- DICOM 資料夾
- 根目錄資料夾
- modality
- task
- 是否開啟脊椎功能
- 是否開啟 fast mode
- 是否自動出圖
- erosion 次數
- `slice_start`
- `slice_end`
- AI compare 檔案
- manual compare 檔案
- TotalSegmentator license key

## 5. 重要輸出

從使用者角度看，目前最重要的輸出有：

- segmentation 資料夾
- `mask_<task>.csv`
- fast mode 對應命名的 CSV
- 脊椎相關 CSV
- `png/`
- `png_eroded/`
- compare 結果
- 批次 log
- 每個病例的狀態

## 6. 使用者最在意的正確性

如果從使用者感受出發，目前最不能錯的有 8 件事。

1. 病例要掃對，不能漏抓或抓錯資料夾。
2. modality 對應的 task 要正確。
3. CT 與 MRI 不可以混用錯 task。
4. 切片範圍要正確，特別是中間段分析。
5. CSV 的第 N 張要對到真正的第 N 張影像。
6. PNG 的第 N 張要對到真正的第 N 張影像。
7. 脊椎標記要能作為定位輔助，而不是亂標。
8. 比對功能要清楚告訴使用者它拿哪一張 slice 在算。

## 7. 目前最需要先釐清的產品決策

如果要往後重構，先不是改程式，而是先把下面幾件事講死。

1. 分割完成後，CSV 是不是必定輸出。
2. PNG 是不是預設正式輸出，還是可選輸出。
3. 脊椎功能到底是預設開啟還是進階選項。
4. 切片範圍是否應被視為核心功能，而不是附加功能。
5. Compare 是否持續維持獨立流程。
6. 批次、重試、授權、錯誤診斷都應不應該算正式功能。

## 8. 建議閱讀方式

如果你要逐條核對這個產品到底是不是你心中的版本，建議順序是：

1. 先看第 2 節的使用者情境，有沒有漏掉真正會發生的工作情境。
2. 再看第 3 節的功能總表，有沒有少了任何功能。
3. 再看第 6 節的正確性要求，這些是不是你最在意的點。
4. 最後才用這份文件去反推程式應該怎麼拆。
