# TEAM — Day04, K4-L3B

**Làm nhóm.** Mỗi người tự viết và commit phần INDIVIDUAL của mình.

## Thông tin bài nộp

- Tên nhóm: 3soldiers
- Người đại diện / MSSV: Đoàn Quang Thanh / 2A202602841
- Tên repo: `K4B-DAY04-3soldiers` (theo mẫu tên repo BTC đã cập nhật)
- URL repo, nhánh nộp, commit chốt: <https://github.com/dqtxdy/K4B-DAY04-3soldiers>, `main`, `[ĐIỀN SAU COMMIT TÍCH HỢP CUỐI]`
- Deadline mặc định: 23:59 ngày 16/09/2026, múi giờ Asia/Ho_Chi_Minh; thay bằng thông báo BTC nếu lớp có deadline khác.

## Thành viên

| Họ và tên | MSSV | GitHub | Vai trò và công việc | File/commit/PR |
|---|---|---|---|---|
| Đoàn Quang Thanh | 2A202602841 | dqtxdy | v0–v1, tích hợp UI/transcript/README/report | `89117de`, `d88b446`, commit tích hợp cuối đang chờ |
| Phạm Minh Đăng | 2A202602591 | pmdangbn04 | v2 tool declarations, 10 case nhóm và group run | `bf0391b`, `b01134a` |
| Đỗ Trọng Bình | 2A202602855 | DTB2324 | v3, safety gate, bonus tool/test và final regression | `9bf1aa0`, `6e25036` |

## Thứ tự tích hợp

1. `dqtxdy`: v0 và v1 (`89117de`, `d88b446`).
2. `pmdangbn04`: v2 artifact, version log và v2 run.
3. `DTB2324`: v3 artifact, version log và v3 run 30/30.
4. `DTB2324`: safety gate, bonus tool/test, final base regression và adversarial evidence.
5. `pmdangbn04`: 10 case nhóm và group run trên artifact đã có bonus tool.
6. `dqtxdy`: UI, transcript, README Linux và report tích hợp.
7. Mỗi thành viên tự viết rồi commit mục INDIVIDUAL của mình.

## Nhận xét chung

- Kết quả và bằng chứng: base tăng từ 23/30 ở v0 lên 30/30 ở v3; xem `starter_v0/runs/` và `starter_v0/artifacts/version_log.csv`.
- Thay đổi hiệu quả nhất: đưa routing/argument boundary về đúng `tools.yaml`, chỉ giữ policy tổng quát và enum grounding ngắn gọn trong system prompt.
- Giới hạn còn lại: kết quả phụ thuộc provider/model snapshot; dữ liệu và ticket đều là local mock, không kết nối helpdesk thật.
- Cách phân công và tích hợp: commit tuần tự theo thứ tự trên; mỗi người review/run file thuộc bundle trước khi tự commit.

## INDIVIDUAL

### Đoàn Quang Thanh — 2A202602841

- Phần việc và file/commit/PR: v0–v1 (`89117de`, `d88b446`); tích hợp `README.md`, `TEAM.md`, `starter_v0/web_ui.py`, transcripts và `starter_v0/artifacts/REPORT.md` trong commit cuối.
- Quyết định, khó khăn và cách xử lý: Giữ system prompt ở mức policy tổng quát, chuyển routing/argument cụ thể về tool descriptions và dùng trace để cải thiện từng version. Khó khăn chính là hướng dẫn ban đầu thiên về WSL, kết quả model chưa ổn định và các thành viên cần commit tuần tự; tôi chuyển lệnh sang Linux, cố định model snapshot, giữ snapshot local và tích hợp từng commit bằng stash/fast-forward để không mất artifact cuối.
- Điều đã học: Cần đánh giá agent bằng cả metric, tool arguments, tool results và filesystem; PASS tự động chưa đủ để chứng minh action an toàn. Artifact hash, model snapshot và lịch sử commit giúp kết quả có thể đối chiếu và tái hiện.
- AI/công cụ đã dùng và cách kiểm tra: Dùng Codex hỗ trợ phân tích trace, chỉnh code/report và rà rubric; dùng OpenAI API với `gpt-4.1-mini-2025-04-14` cho live eval. Tôi kiểm tra lại bằng run JSON, `unittest` 12/12, `py_compile`, `git diff --check`, secret scan, transcript UI/API và review thủ công tool trace trước khi giữ evidence.
- Thời điểm đã tự nộp URL repo chung trên VLearn: 01:47:52 ngày 16/09/2026 (Asia/Ho_Chi_Minh).

### Phạm Minh Đăng — 2A202602591

- Phần việc và file/commit/PR: v2 tools/version log/run (`bf0391b`); 10 case nhóm và group run (`b01134a`).
- Quyết định, khó khăn và cách xử lý:
- Điều đã học:
- AI/công cụ đã dùng và cách kiểm tra:
- Thời điểm đã tự nộp URL repo chung trên VLearn:

### Đỗ Trọng Bình — 2A202602855

- Phần việc và file/commit/PR: v3 core (`9bf1aa0`); safety gate, bonus tool/tests và final regression (`6e25036`).
- Quyết định, khó khăn và cách xử lý:
- Điều đã học:
- AI/công cụ đã dùng và cách kiểm tra:
- Thời điểm đã tự nộp URL repo chung trên VLearn:
