<video src="https://github.com/user-attachments/assets/e4d6abf1-1300-460b-84e7-74237eac6b27" controls="controls" width="100%"></video>

# Klondike Project (Python + Tkinter)

Project Klondike Solitaire được viết bằng Python với GUI Tkinter.

## 1. Yêu cầu

- Windows
- Miniconda (hoặc Anaconda)

## 2. Tạo môi trường ảo bằng Conda

Trong thư mục project, chạy:

```powershell
conda env create -f environment.yml
```

Nếu bạn đã tạo môi trường trước đó, có thể dùng:

```powershell
conda activate klondike-conda
```

Hoặc tạo thủ công:

```powershell
conda create -n klondike-conda python=3.11 tk -y
conda activate klondike-conda
```

## 3. Chạy game

Tại thư mục gốc project, sau khi activate môi trường:

```powershell
python main.py
```

## 4. Tính năng chính đã có

- Bộ bài 52 lá dùng cấu trúc array và thuật toán Fisher-Yates shuffle.
- Stock, Waste, Foundation dùng Stack với push/pop.
- Tableau dùng 2 Stack (`face_down` và `face_up`) để tự động lật bài khi cần.
- Logic kiểm tra chồng bài đúng luật khi di chuyển 1 lá hoặc cả chồng.
- Undo/Redo dùng 2 Stack lịch sử.
- Tính điểm và bảng xếp hạng có sắp xếp.
- Lưu xếp hạng tại `data/rankings.json` sau khi bấm Save Result.

## 5. Cách tính điểm:
 - Rút từ Stock sang Waste +5, nếu Stock rỗng và chỉ quay Waste về Stock thì +0 (thao tác đơn giản).
 - Rút từ Waste về Foundation +5.
 - Rút từ Waste về Tableau +5.
 - Rút từ Tableau về Foundation +10 nếu lật bài, còn không +8.
 - Rút từ Tableau về Tableau: +6 nếu lật bài, còn không +3.
 - Rút từ Foundation về Tableau: -15 (thao tác này làm game dễ đi, -15 điểm như một cách tăng tính hấp dẫn của trò chơi).

## 5. Cách thao tác

- Click vào Stock để rút 1 lá sang Waste (khi hết Stock sẽ tự quay Waste về Stock).
- Kéo-thả trực tiếp để di chuyển bài: giữ chuột ở lá nguồn rồi kéo sang lá/cột đích.
- Click lại đúng lá nguồn đang chọn để bỏ chọn.
- Dùng Undo/Redo để hoàn tác hoặc làm lại.
- Nhấn `F11` để bật/tắt chế độ toàn màn hình.
- Bấm nút `Toggle Ranking` để ẩn/hiện bảng xếp hạng và mở rộng vùng chơi khi cần.

## 6. Lưu ý
- Nếu cần xóa môi trường:
```powershell
conda remove -n klondike-conda --all -y
```
