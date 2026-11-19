# Hình học parametric mới — vật liệu PA12 và điều kiện biên validation ban đầu

Đây là bản thay thế theo xác nhận mới: **core PA12, phần tử shell S4R và platen rigid R3D4**. Không dùng mô hình AlSi10Mg/C3D8R cho phân tích trong bộ này.

## Cấu hình đã khôi phục

| Đại lượng | Cấu hình áp dụng cho mọi lambda |
|---|---|
| Core | PA12, E=1300 MPa, nu=0.33, density=1e-9 tonne/mm³ |
| Plastic | Cùng 9 điểm Table-2 trung bình đã dùng trong bộ validation trước; không phải đường Test-1 gốc |
| Damage / mass scaling | Không dùng |
| Phần tử | S4R, shell thickness 0.30 mm theo hình học mới; 5 integration points |
| Platen | Hai mặt rigid R3D4, không phải solid thép đàn hồi |
| Contact | General contact, all exterior/self-contact; hard normal contact; friction 0.25 |
| Đáy | Khóa DOF 1–6 tại RP_BOTTOM |
| Đỉnh | Khóa U1, U3, UR1–UR3; prescribed V2=-100 mm/s tại RP_TOP |
| Tải | Constant velocity, không SmoothStep/ramp; nén 50% |
| Step | Abaqus/Explicit, NLGEOM=YES, bulk viscosity 0.06 / 1.2 |
| Core U3 | Không thêm khóa U3 trên hai mặt trước/sau |
| Gap | 0.002 mm mỗi platen |
| Mesh profile | In-plane target 2.0 mm, 1 lớp qua chiều sâu, giống baseline shell cloud trước |
| Outputs | 200 field intervals, history duration/1000; U/V/RF, S/LE/PEEQ, các năng lượng |

Với hình học này, chiều cao ngoài H0=48 mm; nén 50% tương ứng 24 mm, nên thời gian step = 24/100 = **0.24 s**. Không dùng lại thời gian 0.26254 s của mẫu cũ cao 52.508 mm vì giữ nguyên tốc độ và strain mới là cùng điều kiện tải.

`analysis_profile.json` và `geometry_lock.json` khóa cấu hình. JSON từng case chỉ được đổi lambda_m và ID; nếu trộn case của bộ AlSi hoặc thay profile không khớp SHA, chương trình từ chối.

## Hình học và kích thước giữ theo code bạn gửi

L1=L2=12 mm; L_BEVEL=5.66 mm; wall thickness=0.30 mm; 6 hàng × 5 cột; chiều cao đường tâm CORE_HEIGHT=47.70 mm; DEPTH=25 mm. Chỉ quét LAMBDA_M theo các công thức nguồn. Không scale, không chỉnh L1/L2 hoặc số hàng/cột.

Bản shell dùng **midsurface theo đường tâm** của các cột, thanh ngang chung và ligament; không giữ các khối Boolean solid hoặc phần góc miter của C3D8R. Đây là chuyển đổi biểu diễn sang S4R theo yêu cầu, không phải thay hình dạng đường tâm. File nguồn AlSi được lưu dưới dạng TXT chỉ để truy vết; chương trình chỉ đọc các hàm toán hình học, không thực thi phần vật liệu/mesh/BC của file đó.

Bề rộng thực vẫn thay đổi với lambda theo chính công thức PITCH_X. Platen footprint vẫn **76 × 25 mm** theo kích thước nguồn, không tự nới rộng. Với lambda làm core rộng hơn platen, `platen_covers_shell_width=False` và coverage fraction được ghi để không đánh đồng với nén đồng đều toàn bộ bề rộng.

- `shell_envelope_xy_mm`: bao ngoài của các dải có chiều dày shell theo pháp tuyến midsurface, trước biến dạng.
- `solid_source_miter_width_mm`: chiều rộng của biểu diễn solid miter trong code nguồn; có thể khác shell envelope.
- `engineering_reference_area_mm2`: width shell envelope × depth, dùng chuẩn hóa stress theo kích thước mẫu mới, như chính sách width×depth trong validation trước.
- `source_reference_area_mm2=1900`: diện tích platen cũ trong code nguồn, giữ để truy vết; không tự dùng thay diện tích specimen khi xuất nominal stress.

Mesh C3D8R với edge counts 19/10 và target 10068 của bản trước không áp dụng cho S4R. Bộ shell cố định mesh profile 2 mm / 1 lớp Z cho mọi lambda; chưa có kiểm tra hội tụ lưới cho hình học mới.

## File đã chuẩn bị

- `baseline_input/PA12_BASELINE.inp`: input baseline lambda=1, có thể chạy trực tiếp bằng Abaqus.
- `baseline_input/model_metadata.json`: kích thước, RP, reference area, thời gian và profile.
- `examples/cases/*/*.inp`: 21 input cho lambda từ -1 tới +1, cách nhau 0.1.
- `examples/previews/*.png`: preview hình học chưa biến dạng.
- `initial_mesh.vtk` trong mỗi case: xem lưới shell/rigid bằng ParaView, không phải kết quả mô phỏng.
- `examples/features.csv`, `manifest.json`: bảng input và thông tin tái lập.
- `results_template.csv`: các nhãn cơ học để trống, status=not_run.

## Chạy ngay file input baseline

Trong Abaqus Command, chuyển vào thư mục `baseline_input`, rồi:

```bash
abaqus job=PA12_BASELINE input=PA12_BASELINE.inp interactive
```

Hoặc Abaqus/CAE → File → Import → Model → chọn INP, kiểm tra rồi tạo/chạy job. Để giữ chính xác mọi keyword, cách khuyến nghị là dùng input-file job qua adapter dưới đây.

## Dùng Python tạo CAE và input-file job

Từ thư mục bộ mã:

```bash
abaqus cae noGUI=abaqus_case.py -- --config baseline.json --out my_baseline
```

Adapter tạo INP, import model vào CAE và tạo `JobFromInputFile` dùng đúng file INP; không phụ thuộc việc CAE importer diễn giải lại đầy đủ contact. Không tự submit job. Chạy Data Check rồi Submit trong Job Manager. `--out` phải là thư mục mới.

Nếu chạy script bằng Python thường (không có Abaqus), nó vẫn ghi được INP; không tạo CAE và không chạy solver. Trong GUI File → Run Script có thể chọn `abaqus_case.py`; mặc định dùng baseline và một thư mục output mới.

## Sinh thêm cấu hình cho ML

Python 3.10+; chỉ cần Matplotlib để tạo preview:

```bash
python -m pip install -r requirements-preview.txt
python make_dataset.py --n 41 --lambda-min -1 --lambda-max 1 --out my_dataset
```

Mỗi mẫu dùng một profile vật liệu/BC/mesh giống nhau và chỉ khác lambda. Geometry_id dùng để nhóm cùng hình học; analysis_id còn bao gồm hash profile để không trộn kết quả PA12 với bộ AlSi trước đó.

Tạo nhiều CAE, trước hết xem lệnh:

```bash
python run_batch.py --dataset examples --out my_cae_models --limit 3
```

Thực thi (cần Abaqus và license):

```bash
python run_batch.py --dataset examples --out my_cae_models --abaqus abaqus --execute
```

Các INP đã có sẵn nên không bắt buộc tạo CAE trước khi giải. Batch này chỉ tạo model/job, không tự submit phân tích.

## Xuất stress–strain sau khi giải

Giữ `model_metadata.json` cạnh ODB tương ứng, rồi:

```bash
abaqus python extract_odb.py path/to/PA12_BASELINE.odb
```

Trong CAE Visualization có thể mở đúng ODB và File → Run Script → `extract_odb.py`. Extractor dùng active viewport, không lấy nhầm các cờ GUI như --lmlog làm tên file. Nếu cần chỉ định metadata khác: thêm đường dẫn JSON sau ODB.

Compression force ở RP trên = -RF2_top; strain=-U2_top/H0; stress=-RF2_top/A0, với H0 và A0 đọc từ metadata của **đúng case**. Không lấy trị tuyệt đối để che sai dấu. Extractor từ chối step chưa hoàn tất và ghi thêm energy CSV. Kiểm tra cân bằng lực và ALLKE/ALLIE trước khi dùng làm nhãn ML.

## Giới hạn xác minh

Đã tạo và kiểm tra cấu trúc keyword, vật liệu/BC, connectivity và dữ liệu metadata của các INP trên cloud. Chưa có Abaqus kernel/license trên cloud, nên **chưa chạy Data Check hoặc solver Abaqus** cho bộ hình học mới này. Không gán nhãn cơ học giả và không chuyển kết quả validation PA12 hình học cũ thành kết quả của hình học mới.
