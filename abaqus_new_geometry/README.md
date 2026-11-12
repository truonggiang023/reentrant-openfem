# Python chạy trực tiếp trong Abaqus/CAE — geometry MỚI

**Tệp chính độc lập:** [`Abaqus_Reentrant_NEW.py`](Abaqus_Reentrant_NEW.py). Không cần NumPy, file JSON hoặc các file của bộ OpenCourant. Có thêm [`Extract_Abaqus_NEW.py`](Extract_Abaqus_NEW.py) để lấy đường ứng suất–biến dạng sau khi bạn chạy solver.

## 1. Cách chạy

1. Tải file `.py` bằng **Raw / Download raw file**, lưu vào thư mục làm việc trên máy.
2. Mở **Abaqus/CAE → File → Run Script**, chọn `Abaqus_Reentrant_NEW.py`.
3. Script tạo thư mục mới `Reentrant_NEW_LOCAL_files/` hoặc `Reentrant_NEW_ENVELOPE_files/`, bên trong có INP, metadata và preview SVG. Khi chạy trong CAE, script tạo thêm model nhập từ INP, file `.cae` và một **input-file Job**.
4. Mở **Job Manager → Data Check**. Đọc `.dat/.msg/.sta`, kiểm tra contact/thickness/initial overclosure. Khi Data Check ổn, bạn tự **Submit**. Script không tự chạy phân tích.

Hoặc chạy ngoài giao diện:

```text
abaqus cae noGUI=Abaqus_Reentrant_NEW.py
```

Nếu dùng Python thường hoặc `abaqus python`, phần sinh INP vẫn chạy nhưng không tạo CAE/Job nếu thiếu CAE kernel.

Mỗi lần chạy script chọn tên/thư mục mới khi tên cũ đã tồn tại, để giữ lại kết quả trước. Nếu chạy nhiều case trong cùng phiên CAE, kiểm tra Working Directory trùng thư mục output của Job trước khi Submit.

## 2. Chọn geometry ở đầu file

```python
GEOMETRY_CASE = 'LOCAL'   # hoặc 'ENVELOPE'
INPLANE_MESH_MM = 2.0
Z_LAYERS = 1
SPEED_MM_S = 100.0
END_STRAIN = 0.50
```

| Lựa chọn | Khung dựng ngang × cao × sâu (mm) | H đường giữa (mm) | L₁ đường giữa (mm) |
|---|---:|---:|---:|
| `LOCAL` — mặc định, giữ H/L₁ | 77,411836 × 52,508 × 30 | 8 | 4,5 |
| `ENVELOPE` — giữ khung 80×64 | 80 × 64 × 30 | 8,815406 | 5,500116 |

Cả hai dùng góc 50°, thành 0,8 mm, 16 mức thanh ngang/15 khoảng đứng, 7 thanh đầy đủ + nửa thanh ở mép trên/dưới và pha biên như ảnh đã kiểm tra. Không có lựa chọn TABLE cũ.

**Đây vẫn là hai giả thuyết về quy ước kích thước của bài, chưa xác nhận CAD gốc.** Không tự hiểu bản LOCAL có khung 80×64. Khung dựng có dự phòng thickness ở mép, không phải phép đo bề bao solid ở mọi đầu cắt. Kiểm tra `geometry_preview.svg` và `model_metadata.json` trước khi chạy.

Thiết lập mặc định mesh 2 mm, 1 lớp Z khớp lưới của hai đường full 50% đã chạy trên cloud. Muốn tăng lưới theo chiều sâu, đặt `Z_LAYERS = 3`; muốn thử 1 mm cả theo thành và chiều sâu 30 mm, đặt:

```python
INPLANE_MESH_MM = 1.0
Z_LAYERS = 30
```

Tăng Z_LAYERS không đổi chiều sâu vật lý 30 mm và không đổi 5 điểm tích phân qua dày thành 0,8 mm. Chưa có kiểm chứng hội tụ đầy đủ của mọi thiết lập; mô hình mịn hơn cần thêm thời gian chạy và kiểm tra tiếp xúc.

## 3. Mô hình và điều kiện biên

- Hệ đơn vị **mm–N–s–tonne–MPa**.
- PA12: E=1300 MPa, ν=0,33, density=1e-9 tonne/mm³.
- Plastic hardening dùng bảng trung bình Table 2: 38 MPa tại plastic strain 0, tăng đến 56,2 MPa tại 0,12. Chưa phải đường Test-1 gốc.
- Specimen là mặt shell đùn sâu 30 mm, mesh **S4R**, shell section dày 0,8 mm, 5 integration points qua dày.
- Hai bàn ép là **R3D4 rigid surfaces**. Bàn dưới khóa 6 DOF; bàn trên khóa U1/U3/UR1/UR2/UR3, áp **V2=-100 mm/s**. Global X ngang ảnh, Y là phương nén, Z là chiều sâu.
- General contact **ALL EXTERIOR**, gồm self-contact; hard normal contact, ma sát 0,25. Không tie mẫu vào bàn ép, không khóa DOF specimen.
- Clearance 0,002 mm mỗi bàn ép so với vị trí bề mặt danh nghĩa, để gần với contact-plane clearance của bản cloud. R3D4 là mặt rigid không có carrier thickness 0,1 mm của OpenCourant.
- Explicit, biến dạng lớn, strain mục tiêu 0,5. Thời gian tự tính: LOCAL khoảng 0,26254 s; ENVELOPE 0,32 s với 100 mm/s.
- Không damage, không mass scaling, không thêm imperfection; vận tốc hằng, không ramp. Muốn 1 m/s theo ảnh mô hình nhôm thì đổi `SPEED_MM_S=1000.0`, nhưng đó khác tốc độ 100 mm/s của Alomarah dùng ở lần đối chiếu cloud.
- History tại hai RP: U2, V2, RF2; global ALLIE/ALLKE/ALLAE/ALLVD/ALLFD/ETOTAL. Field: U/V/RF/S/LE/PEEQ.

**Abaqus S4R/general contact khác OpenCourant QEPH/TYPE7.** Dù mesh specimen, vật liệu và tải giống nhau, không mặc nhiên khẳng định đường Abaqus sẽ trùng kết quả OpenCourant.

## 4. Model CAE và Job là gì?

Model được nhập từ input dưới dạng **orphan mesh**, không phải bộ feature CAD sketch/extrude để kéo kích thước. Mục đích là giữ node/connectivity của geometry đã kiểm tra và tránh phụ thuộc lựa chọn face/edge bằng tọa độ trong CAE.

**Job tạo từ INP để giữ nguyên các keyword và node labels. Sửa model trong CAE không tự cập nhật input-file Job này.** Cách đổi thông số an toàn là sửa các biến ở đầu script rồi Run Script lại. Nếu muốn chạy các chỉnh sửa trực tiếp trong model CAE, tạo một Job mới từ model đó sau khi kiểm tra keyword/output/BC đã được nhập đủ.

Nếu CAE không nhập được một keyword, script báo lỗi import và giữ file INP cùng input-file Job; không coi import thành công là thay thế Data Check. Script mở hướng nhìn Front khi import được.

## 5. Lấy stress–strain từ ODB — hỗ trợ CAE và Command

Dùng bản `Extract_Abaqus_NEW.py` phiên bản **2.1_GUI** trở lên. Job đã chạy xong thì chỉ cần xuất lại, không phải chạy lại phân tích.

### Trong Abaqus/CAE

1. Mở ODB kết quả và **hiển thị đúng ODB đó trong viewport đang hoạt động**.
2. Chọn **File → Run Script → Extract_Abaqus_NEW.py**.
3. Script dùng ODB đang hiển thị, tìm `model_metadata.json` cùng thư mục với ODB và ghi CSV ngay tại đó.

Nếu mở nhiều ODB, script ưu tiên ODB trong viewport, không chọn cơ sở dữ liệu đầu tiên. Nếu không có ODB đang hiển thị và có nhiều ODB mở, script báo cần chọn rõ thay vì đoán. ODB đang xem không bị đóng sau khi xuất.

Các tham số khởi động CAE như `--mlog` / `--lmlog` được bỏ qua. Chúng không còn bị hiểu thành đường dẫn metadata.

Nếu cần chọn thủ công, sửa hai dòng ở đầu exporter, ví dụ:

```python
ODB_PATH = r'C:\temp\Reentrant_NEW_LOCAL_files\Reentrant_NEW_LOCAL.odb'
METADATA_PATH = r'C:\temp\Reentrant_NEW_LOCAL_files\model_metadata.json'
```

Để trống hai biến thì dùng cách tự nhận diện ở trên. Console CAE in phiên bản exporter, ODB đã chọn, metadata và đường dẫn CSV để kiểm tra.

### Trong Abaqus Command

```text
abaqus python Extract_Abaqus_NEW.py "duong_dan/Reentrant_NEW_LOCAL.odb"
```

Nếu metadata ở thư mục khác, truyền thêm đường dẫn JSON:

```text
abaqus python Extract_Abaqus_NEW.py "duong_dan/Job.odb" "duong_dan/model_metadata.json"
```

Không cần di chuyển file exporter vào thư mục ODB. Cần giữ đúng metadata của lần chạy; không tạo lại từ một cấu hình mesh khác.

Đầu ra bên cạnh ODB:

- `*_stress_strain.csv`: phản lực thô hai bàn, lực nén có dấu, nominal strain/stress.
- `*_energy.csv`: năng lượng, KE/IE và AE/IE.
- `*_extraction_summary.json`: case, kích thước chuẩn hóa, phiên bản exporter và thời gian.

Công thức:

`strain = -U2_top / height_of_this_case`

`stress_top = -RF2_top / (width_of_this_case × 30)`

`stress_bottom = +RF2_bottom / (width_of_this_case × 30)`

Quy ước lực nén dương giả định lực constraint tại bàn trên theo -Y là RF2 âm; kiểm tra hai phản lực và cân bằng trước khi diễn giải. Không dùng abs(RF2) để che mất tiếp xúc hoặc sai dấu. Nominal stress từ phản lực là đại lượng dùng đối chiếu đường paper.

Exporter từ chối ODB/step chưa đủ thời gian yêu cầu. Nếu chủ động chạy đến strain khác, đổi END_STRAIN trong builder trước khi sinh input để metadata khớp lần chạy.

Đã kiểm tra logic chọn active ODB khi mở hai database, bỏ qua `--lmlog`, nhận metadata CLI/GUI, giữ handle GUI mở và đóng handle do CLI tự tạo bằng đối tượng mô phỏng. Chưa có Abaqus kernel/ODB thật trong môi trường này để xác nhận chạy thực tế.

## 6. Đã kiểm tra đến đâu?

Đã kiểm tra bằng Python thường:

- LOCAL và ENVELOPE có đúng 16 mức thanh, 7 thanh đầy đủ + nửa thanh ở mỗi mép, pha biên và một mạng liên thông.
- **Tọa độ nút và connectivity specimen trùng chính xác với input native của hai geometry MỚI đã chạy cloud**, ở cùng mesh 2 mm/1 lớp Z. Chỉ phần tử và bàn/contact chuyển sang loại Abaqus tương ứng.
- Mặt shell không lặp nút, diện tích dương; BC nén và self-contact có trong INP.
- Lưới 1 mm/3 lớp Z vẫn giữ nguyên khối lượng hình học.
- Có xử lý các hàm Python bị Abaqus ghi đè (`sum`, `min`, `max`, v.v.) và dung sai cắt biên để không làm mất thanh trên.
- Exporter được kiểm tra quy đổi dấu lực/strain và từ chối dữ liệu chưa hoàn tất bằng history tổng hợp.

**Chưa kiểm tra thực tế:** Abaqus/CAE API, keyword Data Check, reader với ODB thật và Abaqus solver, vì môi trường cloud này không có Abaqus/license. Không có kết quả Abaqus mới được nhận là đã chạy hoặc validation đạt. Các kết quả cloud trước là OpenCourant; việc chuyển solver này cần bạn chạy và kiểm tra lại.

## Tham chiếu

Alomarah et al., DOI 10.1080/17452759.2019.1644184, re-entrant-X Fig.9, Tables 1–2. Chen et al., DOI 10.1016/j.tws.2026.114952, validation Fig.4. Không đổi các giả thuyết kích thước thành khẳng định CAD gốc.
