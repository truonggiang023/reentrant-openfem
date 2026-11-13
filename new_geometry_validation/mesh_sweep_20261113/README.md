# Khảo sát mesh trên geometry LOCAL trong ZIP corrected

[Xem CSV stress–strain](mesh_sweep/assessment/curves_common_grid.csv) · [Bảng so sánh mesh](mesh_sweep/assessment/mesh_comparison.csv) · [Đồ thị FEM](mesh_sweep/assessment/mesh_sensitivity.svg)

Input và kết quả: [mesh 1.2](mesh_sweep/mesh_1.2/) · [mesh 1.4](mesh_sweep/mesh_1.4/) · [mesh 1.6](mesh_sweep/mesh_1.6/) · [mesh 1.8](mesh_sweep/mesh_1.8/).

Đã chạy độc lập đủ bốn mesh danh nghĩa 1.2, 1.4, 1.6 và 1.8 mm bằng OpenCourant explicit trên cloud, 2 threads. Kèm baseline 2 mm đã chạy mới từ ZIP. Tất cả giữ một lớp phần tử qua chiều sâu 30 mm. Đây là khảo sát mesh trong mặt; chưa phải hội tụ lưới 3D.

Các đường tâm được đọc từ ZIP. Trước khi remesh, mesh 2 mm được tái tạo và so sánh: mọi tọa độ nút và connectivity đều giống INP nguồn. Các mesh giữ nguyên biên hình học và liên thông; khối lượng shell đều 47.340 g. Không hiệu chỉnh vật liệu hoặc kích thước để khớp paper.

| Mesh danh nghĩa (mm) | Shells | E (MPa) | Sai lệch E so với 9.7 MPa | RMSE Alomarah (MPa) | RMSE Chen (MPa) | ERR năng lượng cuối | Thời gian (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1.2 | 1748 | 11.278 | +16.27% | 0.0692 | 0.0633 | -9.8% | 894.2 |
| 1.4 | 1620 | 11.303 | +16.52% | 0.1211 | 0.0724 | -14.1% | 643.5 |
| 1.6 | 1283 | 11.891 | +22.59% | 0.1093 | 0.0671 | -7.9% | 455.4 |
| 1.8 | 1283 | 11.891 | +22.59% | 0.1093 | 0.0671 | -7.9% | 421.5 |
| 2.0 | 1155 | 11.920 | +22.89% | 0.0900 | 0.0761 | -10.7% | 308.7 |

RMSE với paper dùng cùng miền strain 0.06–0.40, nội suy tuyến tính 341 điểm. E là hồi quy có intercept ở strain 0–0.01 (bốn điểm history, do đó chỉ là ước lượng độ dốc). Tham chiếu E=9.7 MPa là Table 3 thí nghiệm re-entrant-X, không phải E=1300 MPa của nhựa đặc.

| Mesh (mm) | NRMSE với mesh 1.2 (%) | Sai lệch E với mesh 1.2 (%) | Sai lệch năng lượng hấp thụ tới strain 0.49 (%) |
|---:|---:|---:|---:|
| 1.2 | 0.00 | +0.00 | +0.00 |
| 1.4 | 16.90 | +0.22 | -11.03 |
| 1.6 | 12.86 | +5.44 | -1.36 |
| 1.8 | 12.86 | +5.44 | -1.36 |
| 2.0 | 6.80 | +5.69 | -1.72 |

So sánh giữa các lưới dùng strain 0.02–0.49. NRMSE = RMSE chia stress trung bình của mesh 1.2 trong miền đó; không phải trung bình phần trăm sai số từng điểm. Mesh 1.2 chỉ là lưới mịn nhất được khảo sát, không phải nghiệm chính xác.

**Chưa xác lập hội tụ toàn đường nén hoặc validation đạt.** Độ cứng của 1.2 và 1.4 gần nhau nhưng đường crush chưa ổn định tương ứng; chỉ nhìn đoạn đàn hồi sẽ bỏ sót khác biệt này. Các sai số năng lượng cuối cũng còn đáng kể. Không chọn một mesh chỉ vì nó tình cờ gần đường paper hơn.

Mesh danh nghĩa 1.6 và 1.8 tạo cùng một lưới: 2372 nút, 1283 shell. Cả hai deck Starter và Engine giống từng byte. Mỗi thanh được chia ceil(length/h) đoạn nên thay h chưa chắc thay số đoạn. Hai trường hợp được chạy độc lập; RMSE giữa hai lượt trên strain 0.02–0.49 = 0 MPa. Đây là kiểm tra lặp lại, không phải hai mức refinement độc lập.

Cạnh trong mặt lớn nhất thực tế: 1.142857 mm (h=1.2), 1.333333 mm (h=1.4), 1.600000 mm (h=1.6/1.8), 2.000000 mm (baseline). Các phần tử vẫn có cạnh 30 mm theo Z; chưa kiểm tra độ nhạy theo chiều sâu trong đợt này. Không áp dụng Richardson/GCI từ các mức danh nghĩa có lưới trùng nhau và đáp ứng crush chưa ổn định.

Cấu hình giữ nguyên: frame 77.411836346 × 52.507999911 × 30 mm; wall 0.8 mm; E=1300 MPa, nu=0.33, density=1e-9 tonne/mm³, plastic Table 2 trung bình; friction 0.25; đáy cố định; platen trên chỉ chuyển động Y với -100 mm/s; end time 0.262539999553 s, nén 50%; không ramp, damage hoặc mass scaling. QEPH, 5 điểm tích phân chiều dày; TYPE7 penalty self/platen contact. Các điều khiển TYPE7 giữ nguyên nhưng effective gap phụ thuộc kích thước mesh; đây là một yếu tố ảnh hưởng khảo sát.

Mesh 1.2 có cảnh báo Starter 343: 60 initial self-contact penetrations, liên quan 32 nút. Đã kiểm tra và cho phép đúng warning này; Inacti=6 điều chỉnh initial gap. Không xóa cảnh báo khỏi log. Các warning khác nếu có được liệt kê trong metrics.json. Normal termination không chứng minh contact chính xác hoặc cân bằng năng lượng đạt.

Stress = lực tiếp xúc platen trên / (77.411836346 × 30); strain = rút ngắn platen / 52.507999911. TH của bản solver này xuất xung lượng tích lũy; lấy đạo hàm sai phân theo thời gian thành lực trung bình khoảng, giữ dấu, không lọc để khớp paper. History cuối ở strain khoảng 0.4975; lực/stress là giá trị tại midpoint, không ngoại suy tới 0.5. Engine đã chạy đủ thời gian mục tiêu.

Paper Alomarah dùng frame 80 × 64 × 30 mm, S4R nominal 1 mm và đường vật liệu Test-1. ZIP dùng frame LOCAL khác và bảng vật liệu trung bình. QEPH/TYPE7 khác S4R/Abaqus general hard contact. Do đó khảo sát này kiểm tra cấu hình ZIP và mức khớp với paper, chưa chứng minh đã tái lập đúng mô hình paper. Mesh 1.6 mm tối ưu cho RHS trong bài Chen không tự động áp dụng cho mẫu PA12 re-entrant-X này.

Tham chiếu: Alomarah et al., DOI 10.1080/17452759.2019.1644184, Fig.9(c) Specimen-1; Chen et al., DOI 10.1016/j.tws.2026.114952, Fig.4(b) experimental replot. Đường Chen là bản vẽ lại từ Alomarah, không phải thí nghiệm độc lập. Dữ liệu so sánh số hóa từ hình, không phải raw experimental CSV; độ bất định đọc stress khoảng 0.0115–0.0140 MPa.

File chính: mesh_sweep/assessment/mesh_comparison.csv (bảng chỉ số), mesh_sweep/assessment/curves_common_grid.csv (các đường FEM trên cùng lưới strain), mesh_sweep/assessment/mesh_sensitivity.png (độ nhạy giữa lưới). Mỗi thư mục mesh_sweep/mesh_*/ có input native .rad, CSV lực–stress–strain, history gốc CSV, log và VTK cho ParaView.

Chạy lại: dùng OpenCourant commit cb760c206e346eff12161a2268b134ef9d48a4ef (AGPLv3), không kèm binary. Chép hai deck .rad và model.json của case vào thư mục trống, rồi chạy `python code/run_solver.py CASE --root PATH_TO_OPENCOURANT --threads 2 --allow-initial-penetrations --vtk` và `python code/postprocess.py CASE`. Runner từ chối ghi đè kết quả đã có. Các script mesh_sweep.py và assess_sweep.py dùng đường tương đối từ thư mục gốc của bộ kết quả; đường cloud cũ chỉ được lưu thêm làm provenance.

## Gói công khai

Thư mục này gồm input native cho bốn mesh, CSV history và stress–strain, log, metadata, code, đồ thị FEM và VTK cuối của từng lượt. Các VTK trung gian có thể tạo lại bằng runner với `--vtk`. Không chứa PDF, hình paper, tọa độ đường paper số hóa hoặc đồ thị chồng đường paper. Chỉ số đối chiếu paper là kết quả tính toán được ghi trong báo cáo. `assess_sweep.py` cần người chạy cung cấp thư mục `references/` nếu muốn tái tạo phép đối chiếu; dữ liệu tham chiếu không được công khai trong gói.

Các log, VTK và PNG lớn được nén riêng bằng gzip (`.gz`); input `.rad` và CSV có thể dùng trực tiếp. Chạy `python unpack_gzip.py` sau khi tải thư mục để giải nén các tệp này. Đồ thị SVG có thể xem trực tiếp.
