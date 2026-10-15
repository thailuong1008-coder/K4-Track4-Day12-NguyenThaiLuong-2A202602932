# REPORT — Lab Day 12

> Điền **bằng lời và số liệu của chính bạn** (lấy từ màn hình và từ `evidence/*.json`). Mỗi câu 4–8 dòng là đủ. Số không có trong bằng chứng của bạn sẽ bị trừ điểm. Báo cáo công khai trên GitHub; giảng viên đối chiếu với `evidence/` và với bài của các bạn khác.

| | |
|---|---|
| Họ và tên | Nguyễn Thái Lương |
| MSSV (đúng bằng `--student-id` bạn đã chạy) | 2A202602932 |
| GitHub | thailuong1008-coder |
| Seed chia dữ liệu / seed mô hình (xem `evidence/closedloop.json`, mục `student`) | 5409 / 2583 |
| Số seed huấn luyện bạn dùng (`--seeds`) | 3 |

## Kết quả cuối

Điền từ `evidence/closedloop.json`, `openloop.json`, `gate.json` (cho mỗi mô hình học, lấy **dải qua các seed**).

| Bộ điều khiển | L2 vòng hở (m) | Va chạm vòng kín trên log (%) | Quyết định cổng |
|---|---|---|---|
| constant-velocity | 1.256 | 19.9% | BLOCK |
| IDM | 1.556 | 0.1% | RELEASE (baseline) |
| EgoMLP | 0.763 | 20.4..37.1% | BLOCK |
| PercMLP | 0.613 | 0.2..1.2% | BLOCK |
| PercMLP+ (sau khi sửa) | 0.824 | 0.2..0.2% | RELEASE |

## Câu 1 · Dữ liệu
Bước 0 bạn phát hiện những vấn đề gì ở dữ liệu? Vì sao không dùng cột `Acc_LV`, và bạn thay bằng gì? Bao nhiêu quỹ đạo bị loại vì trùng, và vì sao chia theo quỹ đạo?

Trong bước 0 (kiểm tra tập dữ liệu OpenPAV-Trajectory với 992.679 dòng và 9.993 quỹ đạo thô), tôi phát hiện ba vấn đề lớn:
1. Trùng lặp dữ liệu: Có 383 quỹ đạo bị trùng lặp hoàn toàn (`exact_duplicates_removed = 383`), giữ lại 9.610 quỹ đạo sạch. Các quỹ đạo trùng nhau xuất hiện ở các Trajectory_ID cách xa nhau; nếu không khử trùng, việc chia tập train/test ngẫu nhiên sẽ làm dữ liệu test bị rò rỉ vào train (data leakage).
2. Cột gia tốc xe dẫn `Acc_LV` không sử dụng được: Hệ số tương quan tuyến tính giữa cột `Acc_LV` và đạo hàm vận tốc d(Speed_LV)/dt chỉ đạt 0.0453 (`acc_lead_column_corr_with_dv_dt = 0.0453`), gần như bằng 0 do nhiễu cảm biến thô cực lớn, trong khi cột gia tốc của xe sau `Acc_FAV` đạt tương quan tới 0.9291. Do đó, gia tốc xe dẫn bắt buộc phải được tính bằng đạo hàm của vận tốc xe dẫn sau khi đã làm mượt (`Speed_LV` smoothed) để các thuật toán nhận diện phanh hoạt động chính xác.
3. Chia theo quỹ đạo (trajectory-level): Mỗi quỹ đạo là một chuỗi thời gian liên tục 10 Hz kéo dài 7–11 giây. Nếu chia theo khung hình (frame-based split), các khung hình liền kề chỉ cách nhau 0.1 giây sẽ bị xé lẻ vào cả hai tập train và test, dẫn đến mô hình học vẹt quá khứ/tương lai gần thay vì học khả năng khái quát hóa hành vi lái.

## Câu 2 · Phát lại
Bản refactor float32 khác bit ở bao nhiêu đoạn, vượt dung sai ở bao nhiêu? Thay đổi AEB làm lệch bao nhiêu đoạn, và vì sao lệch ở đúng những khung đó (mở một đoạn ra xem)? Phát theo thời gian thật làm lộ ra điều gì mà phát nhanh nhất che đi?

Khi kiểm thử phát lại trên 600 đoạn log (`evidence/replay.json`):
1. Bản chạy lại cùng mã gốc giống hệt từng bit (0 đoạn khác bit). Bản refactor sang float32 và thay đổi thứ tự tính toán khác bit ở toàn bộ 600/600 đoạn (`not_bit_identical = 600`) do tính không kết hợp của phép cộng số thực dấu phẩy động ((0.1+0.2)+0.3 != 0.1+(0.2+0.3)). Tuy nhiên, độ lệch tuyệt đối lớn nhất chỉ là 2.3368e-05 m/s², hoàn toàn nằm trong dung sai `atol=1e-3, rtol=1e-3`, nên có đúng 0/600 đoạn vượt dung sai (`differ_beyond_tol = 0`). Điều này chứng minh kiểm thử phần mềm tự hành cần dùng dung sai thực tế thay vì so khớp bit tuyệt đối.
2. Bản thay đổi logic phanh khẩn cấp AEB (`aeb_ttc=1.5`) làm lệch vượt dung sai ở đúng 7/600 đoạn (đoạn 143, 176, 183, 247, 273, 319, 508) với độ lệch lớn nhất 1.976 m/s². Mở các đoạn này ra cho thấy lệnh điều khiển chỉ lệch ở đúng các khung hình mà khoảng cách thu hẹp quá nhanh khiến TTC tụt xuống dưới 1.5 giây, còn ở các khung lái xe bình thường (TTC > 1.5s) lệnh điều khiển hoàn toàn trùng khớp với IDM gốc.
3. Chế độ phát lại: Phát nhanh nhất (fastest replay) phát lại toàn bộ 59.535 khung hình với 0 khung trễ hạn (late) và 0 khung rớt (dropped). Ngược lại, phát theo thời gian thực (realtime replay) làm lộ ra 581 khung bị trễ deadline và 579 khung bị rớt, khiến 374/600 đoạn bị thay đổi lệnh điều khiển với sai lệch lên tới 8.544 m/s². Phát nhanh nhất đã che giấu hoàn toàn các lỗi nghẽn cổ chai và trễ thời gian thực của hệ thống.

## Câu 3 · Kịch bản
Lưới của bạn (tốc độ cruise, giới hạn khoảng cách, số ô): bao nhiêu % ô **không ai tránh được**? Độ trễ phản ứng 0 → 0,6 s làm vùng đâm của IDM tăng bao nhiêu? Log có phủ vùng khó không? (dẫn giới hạn phanh mạnh nhất của người lái trong log, và phần lưới đòi hỏi hơn thế)

Lưới kịch bản thử thách cắt đầu xe (cut-in grid) được thiết lập với các thông số:
1. Thông số lưới cho mã sinh viên 2A202602932: Tốc độ cruise `v_ego = 14.0 m/s`, khoảng cách từ 2.76 m đến 59.31 m (60 mốc), chênh lệch tốc độ tiến gần từ 0.0 m/s đến 14.0 m/s (45 mốc), tạo thành lưới 2.700 ô kịch bản.
2. Ranh giới bất khả thi (unavoidable frontier): Khi độ trễ phản ứng `t_react = 0.0 s`, có 3.63% diện tích lưới (98/2700 ô) là không thể tránh khỏi va chạm theo quy luật vật lý kể cả khi phanh tối đa 9.0 m/s². Khi độ trễ phản ứng tăng lên `t_react = 0.6 s`, vùng bất khả thi tăng vọt lên 10.22% diện tích (276/2700 ô), tức tăng thêm 6.59 điểm phần trăm (gấp gần 3 lần). Bộ điều khiển IDM bám khít 100% ranh giới vật lý này (0 ô lệch ngoài biên ở cả hai mức trễ).
3. Độ bao phủ của log lái thật: Trong 9.610 quỹ đạo log, chỉ khai thác được 614 sự kiện xe dẫn phanh gấp (6.39%), với trung vị giảm tốc chỉ là -2.53 m/s² và phân vị 99% là -4.21 m/s². Giới hạn phanh khẩn cấp nhất mà con người từng đạp trong log (phân vị 99.9%) chỉ đạt 3.62 m/s² (`human_brake_limit_p99.9 = 3.62 m/s²`). Trong khi đó, có tới 12.67% diện tích của lưới kịch bản đòi hỏi gia tốc hãm lớn hơn 3.62 m/s². Như vậy, dữ liệu log thông thường phân bố lệch và hoàn toàn không bao phủ các kịch bản biên phanh khẩn cấp nguy hiểm.

## Câu 4 · Vòng hở và vòng kín
Dán bảng L2 và tỷ lệ va chạm của bốn bộ điều khiển (kèm hạng ở mỗi cách chấm). Cặp nào đổi thứ tự? Vì sao IDM có L2 như vậy mà vẫn lái tốt? Vì sao EgoMLP có L2 tốt hơn constant-velocity mà vẫn đâm?

Bảng so sánh 4 bộ điều khiển qua 3 seed huấn luyện:
| Bộ điều khiển | L2 vòng hở (m) | Hạng L2 | Va chạm vòng kín (%) | Hạng vòng kín |
|---|---|---|---|---|
| PercMLP | 0.613 m | 1 | 0.6% (0.2..1.2%) | 2 |
| EgoMLP | 0.763 m | 2 | 27.5% (20.4..37.1%) | 4 |
| const-vel | 1.256 m | 3 | 19.9% | 3 |
| IDM | 1.556 m | 4 | 0.1% | 1 |

Hiện tượng đảo chiều thứ tự xếp hạng (order flips): Có 4 cặp bị đảo ngược hoàn toàn giữa hai cách chấm gồm: `(const-vel, IDM)`, `(const-vel, EgoMLP)`, `(IDM, EgoMLP)` và `(IDM, PercMLP)`.
Giải thích bản chất kỹ thuật:
1. Vì sao IDM có L2 tệ nhất (1.556 m) nhưng lái vòng kín tốt nhất (0.1% va chạm)? IDM là thuật toán dựa trên luật vật lý giữ khoảng cách an toàn, không học bắt chước thói quen cụ thể của từng tài xế con người trong log nên điểm L2 vòng hở cao. Nhưng trong vòng kín, IDM liên tục phản hồi theo khoảng cách thực tế và phanh dứt khoát khi nguy hiểm, do đó tránh va chạm gần như tuyệt đối.
2. Vì sao EgoMLP có L2 tốt hơn const-vel (0.763 m vs 1.256 m) nhưng đâm nhiều hơn (27.5% vs 19.9%)? EgoMLP chỉ nhận đầu vào là lịch sử vận tốc của chính nó (`Speed_FAV`) mà hoàn toàn mù thông tin khoảng cách (`gap`) và tốc độ xe dẫn (`v_lead`). Trong vòng hở, bám theo vận tốc lịch sử giúp nó đạt L2 rất đẹp trên phần lớn quãng đường êm đềm. Nhưng trong vòng kín khi xe trước phanh gấp, EgoMLP không hề biết có chướng ngại vật phía trước, tiếp tục duy trì tốc độ và gây tai nạn nặng nề (đâm tới 37.1% ở seed xấu nhất và 61.4% trên lát cắt phanh gấp).

## Câu 5 · Một lần chạy chưa đủ
EgoMLP dao động bao nhiêu giữa các seed? Khoảng tin cậy Wilson nói gì? Nếu bạn chỉ chạy đúng một seed thì có thể báo kết quả nào, và vì sao điều đó nguy hiểm?

Phân tích tính biến thiên và độ tin cậy thống kê qua 3 seed huấn luyện:
1. Dao động giữa các seed của EgoMLP: Tỷ lệ va chạm vòng kín của EgoMLP dao động mạnh từ 20.4% đến 37.1% (`per_seed = [37.1%, 25.1%, 20.4%]`), chênh lệch lên tới 16.7 điểm phần trăm giữa các lần khởi tạo trọng số ngẫu nhiên. Ngay cả PercMLP cũng dao động từ 0.2% đến 1.2% (chênh lệch gấp 6 lần).
2. Khoảng tin cậy Wilson 95%: Với seed xấu nhất của EgoMLP, khoảng tin cậy Wilson 95% là [35.3%, 38.9%] (trên n=2883 quỹ đạo kiểm thử). Khoảng tin cậy của seed tốt nhất (20.4%) và seed xấu nhất (37.1%) hoàn toàn không giao nhau (non-overlapping). Điều này chứng minh sự chênh lệch này là do tính bất ổn định cố hữu của mô hình học sâu khi lái vòng kín tương tác, không phải do phương sai ngẫu nhiên của mẫu thử.
3. Nguy cơ khi chỉ báo cáo một lần chạy: Nếu kỹ sư tình cờ chọn đúng seed tốt nhất (20.4%) để báo cáo, họ sẽ ngộ nhận rằng hệ thống an toàn hơn thực tế gần 17%. Khi đưa vào sản xuất trên diện rộng, hệ thống có thể rơi vào vùng trọng số tồi tệ (37.1% va chạm). Việc chỉ dựa vào một lần chạy duy nhất là cực kỳ nguy hiểm, che giấu rủi ro hệ thống và vi phạm nguyên tắc kiểm thử an toàn tự hành.

## Câu 6 · Tác nhân phản ứng
Dán bảng "xe sau phát lại" và "xe sau phản ứng". `T` bạn hiệu chỉnh là bao nhiêu, xe sau chân thực đến mức nào so với xe không phản ứng? Vì sao IDM bị tính "va chạm giả" khi xe sau chỉ phát lại, và điều này làm đổi kết luận về bộ điều khiển ra sao?

Bảng so sánh tỷ lệ va chạm trên lưới kịch bản cắt đầu xe (`t_react = 0.6 s`):
| Bộ điều khiển | Xe sau phát lại (%) | Xe sau phản ứng (%) | Va chạm đuôi (Phát lại / Phản ứng) |
|---|---|---|---|
| const-vel | 80.6% | 80.6% | 0.0% / 0.0% |
| IDM | 80.9% | 10.2% | 70.6% / 0.0% |
| EgoMLP | 79.4% | 79.4% | 0.0% / 0.0% |
| PercMLP | 81.9% | 32.2% | 49.9% / 0.0% |
| PercMLP+ | 81.3% | 10.4% | 70.9% / 0.0% |

Phân tích tác nhân môi trường:
1. Hiệu chỉnh tham số $T$: Khoảng thời gian bám đuôi tối ưu được hiệu chỉnh là `T = 1.4 s`, đạt khoảng cách Wasserstein W1 = 0.341 so với phân bố người lái thật (trung vị thời gian bám đuôi trong log là 1.87 s). Tác nhân phản ứng với T=1.4s chân thực hơn rất nhiều so với một xe đi sau không bao giờ phản ứng (khoảng cách W1 lên tới 0.847).
2. Va chạm giả (fake rear collisions): Khi xe sau chỉ "phát lại" thụ động theo log cũ, IDM bị tính tỷ lệ va chạm đuôi lên tới 70.6%, khiến tổng va chạm bị đội lên 80.9%. Lý do là IDM phanh rất thông minh và kịp thời để tránh xe cắt đầu phía trước, nhưng xe sau phát lại không hề biết xe trước vừa phanh nên đâm thẳng vào đuôi IDM. Khi chuyển sang xe sau phản ứng thông minh, tỷ lệ va chạm đuôi của IDM giảm về đúng 0.0% và tổng va chạm rơi xuống 10.2% (trùng khít ranh giới bất khả thi vật lý). Nếu không có tác nhân phản ứng, kiểm thử sẽ phạt oan bộ điều khiển lái tốt nhất và đảo lộn hoàn toàn kết luận thẩm định.

## Câu 7 · Cổng phát hành và sửa
Quy tắc nào chặn PercMLP và nguyên nhân gốc là gì (dẫn số)? Bạn sửa bằng gì và vì sao nó chữa đúng nguyên nhân? Sau khi qua cổng, PercMLP+ có **tốt hơn** IDM không? Nó có nên được phát hành không, và bạn đề xuất làm gì trước khi quyết định?

Đánh giá cổng phát hành và giải pháp sửa lỗi:
1. Nguyên nhân PercMLP bị chặn: PercMLP bị cổng phát hành chặn (BLOCK) bởi các quy tắc R2, R3, R4, R5, R6. Hai nguyên nhân gốc cốt lõi:
   - Sai số tích lũy vòng kín (Covariate Shift): Trên log kiểm thử, tỷ lệ va chạm của PercMLP là 1.2% (cận trên 95% là 1.7%), vượt quá ngưỡng IDM baseline 0.1% + 1.0% = 1.1% (FAIL R2). Trên lát cắt phanh gấp, va chạm là 6.5% (cận trên 11.1% so với ngưỡng 6.1%, FAIL R3).
   - Phân phối ngoài tầm quan sát (OOD scenarios): Trên lưới cắt đầu xe tránh được, PercMLP va chạm tới 22.0% diện tích (FAIL R4, ngưỡng <= 2.0%) và 32.2% trong môi trường phản ứng (FAIL R6, ngưỡng <= 12.2%).
2. Giải pháp sửa chữa:
   - Bổ sung 20.000 kịch bản cắt đầu xe tổng hợp (`cutin_windows`) gắn nhãn bởi IDM để bao phủ vùng kịch bản mà log chưa từng có.
   - Áp dụng thuật toán DAgger 2 vòng (`dagger_windows`): Cho mô hình tự lái trên 7.688 quỹ đạo thực tế, ghi lại chính xác các trạng thái lệch pha/nguy hiểm mà mô hình tự rơi vào, gắn nhãn điều khiển chuẩn từ chuyên gia IDM và tái huấn luyện.
   - Kết quả: `PercMLP+` đã vượt qua toàn bộ 7/7 quy tắc (RELEASE), giảm va chạm trên lưới từ 22.0% xuống 0.2%, va chạm trên log xuống 0.2% (cận trên 0.5% <= 1.1%).
3. PercMLP+ có tốt hơn IDM không và quyết định phát hành:
   - Tuyệt đối **không thể khẳng định PercMLP+ tốt hơn IDM**, vì nhãn của PercMLP+ được học bắt chước từ chính IDM ("học sinh không thể vượt qua thầy"). Điểm L2 vòng hở của PercMLP+ thậm chí còn tăng từ 0.613 m lên 0.824 m. Trên kịch bản cruise ngoài phân phối 20 m/s, PercMLP+ vẫn đâm 0.4..1.8% diện tích trong khi IDM đâm 0.0%.
   - Đề xuất: Chưa nên phát hành độc lập để thay thế IDM. Cần kết hợp kiến trúc an toàn lai (Hybrid Architecture), sử dụng IDM hoặc bộ lọc an toàn dựa trên luật (Safety Filter / Control Barrier Function) làm lớp dự phòng an toàn (Safety Fallback) phía sau mạng neural.

## Câu 8 · Bài lab này không chứng minh được gì
Chọn **ít nhất ba** giới hạn quan trọng nhất đối với việc quyết định phát hành và giải thích vì sao mỗi cái làm kết luận của bạn kém chắc chắn. Điều gì cần làm tiếp để thu hẹp khoảng cách đến thế giới thật?

Ba giới hạn quan trọng nhất của bài lab đối với quyết định phát hành thực tế:
1. Giả định chuyển động một chiều dọc (1D Longitudinal Only): Bài lab chỉ xem xét chuyển động tiến/lùi theo trục dọc, hoàn toàn bỏ qua điều khiển phương ngang (lateral control), góc đánh lái, độ bám đường (hệ số ma sát lốp - mặt đường thay đổi khi trời mưa/băng tuyết) và độ dốc mặt đường. Trong thực tế khi xe trước phanh gấp hoặc cắt đầu nguy hiểm, xe tự hành có thể chủ động đánh lái chuyển làn sang khoảng trống an toàn thay vì chỉ đạp phanh kịch sàn.
2. Mô hình cảm biến và độ trễ quá lý tưởng (Ideal Perception & Constant Latency): Hệ thống giả định thông tin khoảng cách và tốc độ nhận được gần như hoàn hảo hoặc chỉ có nhiễu Gaussian đơn giản, độ trễ cố định 0.6 giây. Trong thực tế, hệ thống cảm biến (Camera, LiDAR, Radar) thường xuyên gặp hiện tượng che khuất (occlusion), nhận diện nhầm (false positives/negatives), độ trễ biến thiên bất định (latency jitter) và suy giảm tầm nhìn do thời tiết khắc nghiệt.
3. Xe dẫn trong log không phản ứng (Non-reactive Lead Vehicle): Xe dẫn trong log chỉ là dữ liệu phát lại cứng (open-loop replay), hoàn toàn không có tương tác xã hội qua lại (game-theoretic interaction) với xe thử nghiệm. Thế giới mô phỏng là một môi trường đóng với các giả định chủ quan của kỹ sư thiết kế.

Các bước đề xuất tiếp theo để thu hẹp khoảng cách đến thế giới thật:
- Chuyển đổi sang môi trường mô phỏng 3D đa chiều đầy đủ động lực học xe (Vehicle Dynamics, như CARLA hoặc CarSim) với mô hình bề mặt đường và thời tiết đa dạng.
- Tích hợp kiểm thử phần cứng trong vòng lặp (Hardware-in-the-Loop - HIL) và kiểm thử cảm biến đầu cuối để đánh giá độ trễ thực tế của hệ thống nhúng.
- Triển khai thử nghiệm thực địa có giám sát (Shadow Mode / Fleet Testing) trên đường thử kín (Proving Ground) trước khi thương mại hóa trên đường phố công cộng.
