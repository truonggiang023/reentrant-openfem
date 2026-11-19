# reentrant-openfem

## Bộ mới: geometry parametric + PA12 / S4R

- [Hướng dẫn và mã Python](parametric_PA12_S4R/README.md)
- [Input baseline PA12_BASELINE.inp](parametric_PA12_S4R/baseline_input/PA12_BASELINE.inp)
- [21 cấu hình lambda: INP, metadata và preview](parametric_PA12_S4R/examples/)
- [Vật liệu và điều kiện biên cố định](parametric_PA12_S4R/analysis_profile.json)

Bộ mới dùng PA12, core S4R, platen rigid R3D4; nén 100 mm/s tới 50%, friction 0.25, không damage/mass scaling. Chỉ quét LAMBDA_M, giữ các kích thước đầu vào theo code đã cung cấp. Thư mục này thay bản AlSi10Mg/C3D8R cho yêu cầu hiện tại. Input đã được kiểm tra cấu trúc, **chưa chạy Data Check hoặc solver Abaqus cho hình học mới**.

Tải toàn bộ repository qua **Code → Download ZIP**, rồi mở thư mục `parametric_PA12_S4R`. Các kết quả cloud và plot của hình học validation trước vẫn ở `new_geometry_validation/mesh_sweep_20261113`; không chuyển các kết quả đó thành nhãn ML cho hình học mới.

