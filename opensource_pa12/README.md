# Mô hình PA12 re-entrant trên solver mã nguồn mở

Bộ này tạo input **native Radioss `.rad`**, chạy **OpenCourant** (dự án tiếp nối OpenRadioss), xuất CSV lực/ứng suất/biến dạng và VTK để xem trong **ParaView**. Không cần Abaqus hoặc license thương mại. Cùng mesh được xuất thêm `.inp` để đối chiếu; formulation/contact của hai solver không đồng nhất.

**Đây là bộ triển khai để tự chạy, chưa tái lập định lượng bài báo.** Có cảnh báo tự tiếp xúc ban đầu tại các giao thành shell và mâu thuẫn hình học đã nêu ở dưới. Chạy xong Engine không có nghĩa là validation đã đạt.

## 1. Cài đặt Windows

1. Cài Python 3.10 trở lên; kiểm tra `py -3 --version`.
2. Tải binary Windows từ [OpenCourant Releases](https://github.com/OpenCourant/OpenCourant/releases). Giải nén toàn bộ, giữ các thư mục `exec`, `extlib`, `hm_cfg_files`. Ví dụ root là `C:\OpenCourant`, bên trong có `exec\starter_win64.exe`, `engine_win64.exe`, `th_to_csv_win64.exe`, `anim_to_vtk_win64.exe`.
3. Tải ZIP repository này bằng **Code → Download ZIP**, giải nén và mở thư mục `opensource_pa12`.
4. Mở CMD tại thư mục đó, cài dependency cho hậu xử lý:

```bat
py -3 -m pip install -r requirements.txt
set "OPENCOURANT_ROOT=C:\OpenCourant"
```

Root phải là thư mục trực tiếp chứa `exec`, không phải thư mục `exec` hay một thư mục ngoài còn lồng thêm cấp giải nén. Runner tự cấu hình PATH/thư viện/config của release. Không cần MPI vì dùng SMP.

Chạy `run_smoke_windows.bat` trước. `run_full_windows.bat` chạy mô hình đủ khung đến 50% nominal strain và có thể mất nhiều thời gian. Các batch dùng root từ biến môi trường hoặc mặc định `C:\OpenCourant`.

**Windows chưa được chạy thử trong môi trường hiện tại.** Đường dẫn và executable names theo hướng dẫn chính thức của OpenCourant; kiểm chứng thực tế bên dưới dùng Linux x86-64.

## 2. Lệnh chạy từng bước

Ví dụ Windows, mẫu nhỏ kiểm tra pipeline:

```bat
py -3 build_radioss.py --out runs\smoke --smoke --strain 0.1
py -3 run_solver.py runs\smoke --root "%OPENCOURANT_ROOT%" --starter-only --allow-initial-penetrations
py -3 run_solver.py runs\smoke --root "%OPENCOURANT_ROOT%" --allow-initial-penetrations --vtk
py -3 postprocess.py runs\smoke
```

Lệnh thứ ba chạy lại Starter rồi chạy Engine. Đây là chủ ý: không phụ thuộc restart cũ nếu input đã đổi. Runner từ chối ghi đè history của lần Engine trước; để chạy lại, chọn tên thư mục mới hoặc lưu/chuyển kết quả cũ ra ngoài.

Mô hình đủ khung 80×64×30 mm, mesh 1 mm, nén 50%, tốc độ theo ảnh điều kiện biên 1 m/s:

```bat
py -3 build_radioss.py --out runs\full --mode TABLE --strain 0.5 --speed 1000 --mesh 1
py -3 run_solver.py runs\full --root "%OPENCOURANT_ROOT%" --allow-initial-penetrations --vtk
py -3 postprocess.py runs\full
```

Linux tương tự, dùng `python3` thay `py -3` và `/` trong đường dẫn:

```sh
python3 build_radioss.py --out runs/smoke --smoke --strain 0.1
python3 run_solver.py runs/smoke --root /path/to/OpenCourant --allow-initial-penetrations --vtk
python3 postprocess.py runs/smoke
```

Bộ sinh input không cần NumPy; chỉ `postprocess.py` cần. `--threads 2` mặc định, có thể đổi theo máy. Không tự dùng mass scaling. Solver binary không được đóng gói vào repository; tải từ nguồn chính thức và giữ giấy phép/third-party notices đi kèm.

## 3. Điều kiện biên, vật liệu và phần tử

Hệ **mm–N–s–tonne–MPa**. PA12: E=1300 MPa, ν=0.33, ρ=1e-9 tonne/mm³; bảng true stress–plastic strain trung bình Table 2 của Alomarah. Không dùng density biểu kiến 300 kg/m³ làm mật độ vật liệu đặc. Không damage, không strain-rate dependence.

Mẫu re-entrant-X được xoay: bề ngang global X=80 mm, chiều cao chịu nén global Y=64 mm, chiều sâu Z=30 mm. H=8 mm, L₁=4.5 mm, θ=50°, dày thành 0.8 mm. Bàn dưới là rigid body, khóa 6 DOF; bàn trên rigid body khóa Ux/Uz và cả ba góc quay, áp VY=-1000 mm/s. Không khóa DOF của specimen. Mặc định vận tốc hằng, không ramp. Dùng `--speed 100` nếu muốn tốc độ FEM của bài Alomarah thay vì 1000 mm/s theo ảnh người dùng cung cấp.

- Specimen dùng **QEPH, Ishell=24**, 5 integration points qua dày. Đây là formulation Radioss, **không đồng nhất S4R Abaqus**. Hình học phi tuyến được bật qua mặc định Ismstr=2; Engine không yêu cầu chuyển sang small strain.
- Bàn ép dùng một mặt shell carrier dày 0.1 mm, LAW1, liên kết rigid body. Độ dày carrier không làm bàn ép biến dạng đàn hồi.
- Contact TYPE7 node-to-surface, ma sát Coulomb 0.25; specimen self-contact và hai bàn ép.
- Self-contact dùng Igap=3 và giới hạn gap theo 0.5 kích thước mesh; contact bàn ép dùng Igap=2. `Inacti=6` điều chỉnh gap ban đầu để xử lý giao thành. Đây là thay đổi số học so với Abaqus general contact, có thể ảnh hưởng độ cứng và thời điểm densification. TYPE7 chưa thay thế đầy đủ edge-to-edge contact của general contact.
- Mỗi bàn ép có clearance số 0.002 mm ngoài vị trí bề mặt danh nghĩa, tổng seating thêm 0.004 mm. Strain hiện tính theo hành trình reference point, chưa trừ seating.
- Carrier steel density chỉ dùng tính mass/inertia bàn ép; chuyển động vẫn bị áp đặt cứng.

## 4. Cảnh báo Starter không bị che đi

Bản hiện tại xuất **warning 343**: initial penetrations của self-contact tại các giao thành shell. Runner mặc định dừng khi có warning. Cờ `--allow-initial-penetrations` cho phép duy nhất warning này sau khi người dùng đã đọc/kiểm tra `.out`; vẫn ghi warning vào `run_status.json` và `summary.json`. Cảnh báo khác hoặc bất kỳ lỗi input nào vẫn làm runner dừng. Không loại bỏ self-contact để làm hết cảnh báo.

Kết quả chạy hiện tại chứng minh pipeline hoạt động, **chưa chứng minh xử lý gap tại giao thành cho đáp ứng cơ học chính xác**. Cần kiểm tra tọa độ/gap, năng lượng và hội tụ contact/mesh trước khi dùng đường cong để kết luận vật lý.

## 5. Hai lựa chọn hình học

`--mode TABLE` (mặc định) giữ các kích thước thành và cắt mạng trong khung danh nghĩa 80×64. Cách xếp ô ở biên và số hàng chưa trùng hình nguồn. Khối lượng shell khoảng 57.706 g, cao hơn 46.08 g suy ra từ mật độ biểu kiến trong bài khoảng 25.23%.

`--mode IMAGE` giữ 16 mức thanh ngang/15 khoảng đứng và pha biên theo hình người dùng gửi. Với cách hiểu kích thước đường giữa hiện tại, khung dựng khoảng 77.412×52.508 mm, không bằng 80×64. Khối lượng khoảng 47.34 g; gần khối lượng không đủ chứng minh hình học đúng.

`--smoke` thay hình học bằng mẫu nhỏ khoảng 21.230×14.589×3 mm, chỉ để thử solver và workflow, **không đại diện mẫu thí nghiệm**. H và L₁ của thành vẫn giữ theo bảng. Mọi kết quả dùng kích thước của chính lần chạy ghi trong `model.json`, không mặc nhiên chia cho 2400 mm² nếu chọn IMAGE/smoke.

Cần CAD/tọa độ/bản vẽ đầy đủ để giải quyết đồng thời topology và kích thước. Không kéo dãn khác tỷ lệ hai trục nhưng vẫn báo H/L₁/góc không đổi, không sửa E/yield/density để che sai hình học.

## 6. Xem kết quả

- `compression_0000.rad`: Starter, material, mesh, contact, BC.
- `compression_0001.rad`: Engine, thời gian kết thúc, output; không mass scaling.
- `starter.log`, `compression_0000.out`, `engine.log`, `compression_0001.out`: luôn đọc trước khi diễn giải kết quả.
- `compressionT01.csv`: dữ liệu TH gốc sau converter của release.
- `compression_curve.csv`: lực nén có dấu, nominal stress/strain, năng lượng của core.
- `summary.json`: trạng thái chạy và giới hạn; luôn có `paper_validated=false`.
- `initial_mesh.vtk`: mở bằng ParaView để xem lưới ban đầu.
- `vtk/compressionA*.vtk`: chọn cả chuỗi trong ParaView, Apply và Play để xem chuyển động. Tọa độ animation đã bao gồm biến dạng; kiểm tra trước khi áp thêm Warp By Vector để tránh cộng displacement lần nữa.

TH contact/reaction của release đã thử lưu **xung lượng tích lũy**, nên hậu xử lý dùng `diff(impulse)/diff(time)` lấy lực trung bình trên khoảng thời gian. Giữ dấu lực, không lấy absolute value để che mất tiếp xúc. Dữ liệu phản lực, contact và chuyển vị RP được xuất riêng để đối chiếu. Nếu dùng release khác, cần xác minh lại quy ước TH; không áp dụng công thức này cho output vốn đã là lực.

Nominal stress = signed top contact force / (width × depth); nominal strain = downward RP displacement / height. Mẫu TABLE dùng area=2400 mm², height=64 mm. Các biến năng lượng raw có trong TH CSV; summary ghi lỗi năng lượng **do Engine báo**, không tự coi một phép cộng các cột chưa được xác minh là cân bằng năng lượng.

## 7. Đã kiểm tra thực tế đến đâu?

OpenCourant Linux x86-64 double precision, executable banner commit `cb760c206e346eff12161a2268b134ef9d48a4ef`, binary từ bộ cài sẵn trong môi trường. Không gán kết quả này cho mọi release OpenRadioss/OpenCourant.

| Phép thử | Số shell specimen | Mục tiêu strain | Kết quả |
|---|---:|---:|---|
| Smoke nhỏ | 480 | 0.1 | Starter 0 errors, warning 343; Engine normal termination; hậu xử lý/VTK thành công |
| Đủ khung TABLE | 76,530 | 0.002 | Starter 0 errors, warning 343; Engine normal termination; hậu xử lý thành công |

Lịch sử output có thể dừng trước điểm thời gian cuối tối đa một output interval. Kiểm tra kết quả được lưu trong `checks/`.

Bản đầy đủ chỉ chạy đến **0.2%** strain, không phải đường nén hoàn chỉnh đến 50%. Kinetic/internal energy của core còn cao trong giai đoạn khởi động vận tốc hằng: cực đại nửa sau phép thử ngắn khoảng **1.844**. Lỗi năng lượng Engine báo cuối khoảng **-4.6%**. Smoke có tỉ số khoảng 0.00472 trong nửa sau, nhưng mẫu khác và lỗi năng lượng khoảng **-6.9%**. Do đó không tuyên bố quasi-static hay validation dựa vào các phép thử này.

Chưa chạy khảo sát hội tụ mesh/tốc độ, chưa đối chiếu đường thực nghiệm hoặc Abaqus ODB, chưa chạy đủ compression 50%, chưa chạy Windows. Cần kiểm tra các điều kiện đó trước khi dùng kết quả nghiên cứu.

## Nguồn

- [OpenCourant source](https://github.com/OpenCourant/OpenCourant) và [Releases](https://github.com/OpenCourant/OpenCourant/releases); solver GNU AGPL v3, xem giấy phép chính thức.
- [ParaView](https://www.paraview.org/).
- Alomarah et al., DOI 10.1080/17452759.2019.1644184: re-entrant-X Fig.9, material Table 2.
- Chen et al., DOI 10.1016/j.tws.2026.114952: validation Fig.4 dựa trên nghiên cứu trên.
