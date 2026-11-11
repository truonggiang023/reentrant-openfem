# Abaqus re-entrant PA12 — bản dựng để tự chạy

Script độc lập `Abaqus_Reentrant_X.py` tạo mesh, input Explicit, CAE orphan mesh và Job. Không cần file cấu hình ngoài. Không tự submit Job.

## Tải và chạy

Tải file Python bằng nút **Raw / Download raw file**, hoặc tải ZIP của repository qua **Code → Download ZIP**. Trong Abaqus/CAE chọn **File → Run Script**, hoặc chạy:

```text
abaqus cae noGUI=Abaqus_Reentrant_X.py
```

Nếu chỉ muốn tạo INP, có thể chạy `abaqus python Abaqus_Reentrant_X.py` hoặc Python 3 thông thường. Khi không có CAE kernel, script chỉ tạo INP và metadata.

Đầu ra mặc định trong `Reentrant_X_TABLE_files/`:
- `reentrant_X.inp`
- `Reentrant_X_TABLE.cae` (chỉ khi chạy CAE)
- `model_metadata.json`, `centerlines.csv`

Chạy Data Check trước khi Submit. Để chạy input trực tiếp, chuyển vào thư mục đầu ra rồi dùng:

```text
abaqus job=reentrant_X input=reentrant_X.inp datacheck interactive
abaqus job=reentrant_X input=reentrant_X.inp cpus=4 interactive
```

## Thông số và điều kiện biên

- HP PA12; E=1300 MPa, ν=0.33, density=1e-9 tonne/mm³.
- H=8 mm; L₁=4.5 mm; θ=50°; thành 0.8 mm; chiều sâu 30 mm.
- Bảng bài báo: re-entrant-X có kích thước theo phương X=64 mm, Y=80 mm. Script xoay phương chịu nén của bài báo thành global Y: bề ngang 80 mm, chiều cao nén 64 mm.
- Bàn dưới cố định 6 bậc tự do. Bàn trên chỉ chuyển động theo global -Y.
- Tốc độ mặc định **1000 mm/s = 1 m/s**, theo ảnh điều kiện biên người dùng cung cấp. Đổi `SPEED_MM_S = 100.0` để dùng tốc độ Explicit 100 mm/s của Alomarah.
- Nén đến nominal strain 0.5; thời gian mặc định 0.032 s.
- S4R, kích thước cạnh tối đa 1 mm; bàn ép rigid R3D4; general contact, ma sát 0.25.
- Bảng plasticity là giá trị trung bình Table 2, chưa phải đường Test-1 chính xác.
- Không damage, không mass scaling, không thêm imperfection.

## Giới hạn bắt buộc đọc

**Chưa chạy Abaqus hoặc validation định lượng.** Đã kiểm tra cú pháp Python và thực thi bộ sinh INP bằng Python thường; điều đó không thay thế Abaqus Data Check hay kiểm tra kết quả solver.

`GEOMETRY_MODE = 'TABLE'` (mặc định): giữ H/L₁/góc và cắt mạng theo khung danh nghĩa 80×64, **số hàng và pha biên chưa giống hình nguồn**. Khối lượng shell khoảng 57.706 g, cao hơn 46.08 g suy ra từ mật độ biểu kiến trong bài khoảng 25.23%.

`GEOMETRY_MODE = 'IMAGE'`: giữ 16 mức thanh ngang/15 khoảng đứng và pha biên theo hình. Với cách hiểu kích thước đường giữa hiện tại, khung dựng là khoảng 77.412×52.508 mm, **không bằng 80×64**. Khối lượng shell khoảng 47.34 g; gần khối lượng không chứng minh hình học đúng. Không dùng đường cong của bản này như đã validation với mẫu nominal 80×64.

Không kéo giãn riêng hai trục để ép khung mà vẫn báo các thông số thành không đổi. Cần CAD hoặc bản vẽ đầy đủ để giải quyết đồng thời kích thước và topology. Không điều chỉnh density/E/yield stress để bù sai hình học.

Đây là khung triển khai có thể kiểm tra và sửa, không phải mô hình tái lập đã được xác nhận. Chỉ chạy **một** lựa chọn geometry mỗi lần và giữ metadata tương ứng. Nếu dùng extractor, đặt `extract_odb.py` trong cùng thư mục với `model_metadata.json` của lần chạy đó.

## Nguồn đối chiếu

- Alomarah et al., *Compressive properties of 3D printed auxetic structures: experimental and numerical studies*, DOI: 10.1080/17452759.2019.1644184. Fig.9: re-entrant-X; Table 1/2: hình học và PA12.
- Chen et al., *Machine learning for performance prediction and multi-objective optimization of a novel auxetic structure*, DOI: 10.1016/j.tws.2026.114952. Mục 3.2 và Fig.4: validation dựa trên nghiên cứu trên.
