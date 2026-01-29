# 子午觀眾數據分析

這裡是配合交大VTuber社FF46社刊〈境界殘響〉中的〈透過子午看Vtuber觀眾趨勢〉使用的資料

這裡包含了原始資料跟圖表網頁

## 原始資料

database資料夾中有原始資料的檔案，檔案用的sql是sqlite

- origin_data.db : 這是純抓取器做的檔案
- calculate_data.db : 這是已經有一些計算後的表格的圖片，也是做圖用的檔案

## 圖表

圖表是用 Altair 和 Matplotlib 套件做的 

網址如下：https://ff46-data.streamlit.app/

## 其他

如果對數據有更多問題或網站掛了可以email我：ray0411ray@gmail.com