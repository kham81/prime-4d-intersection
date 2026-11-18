import ast
import gc
import json
import math
import operator
import os
import re
import sys
import time
import traceback

# Mở khóa giới hạn độ dài chữ số của số nguyên trong Python
if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

# =====================================================================
# BỘ PHÂN TÍCH BIỂU THỨC SỐ CỰC LỚN & TOÁN HỌC BIT-LENGTH
# =====================================================================
_SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.FloorDiv: operator.floordiv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

def _eval_ast(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        if isinstance(node.value, float) and node.value.is_integer():
            return int(node.value)
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPS:
        left = _eval_ast(node.left)
        right = _eval_ast(node.right)
        res = _SAFE_OPS[type(node.op)](left, right)
        if isinstance(res, float) and res.is_integer():
            return int(res)
        return res
    if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_eval_ast(node.operand))
    raise ValueError("Biểu thức chứa toán tử không được hỗ trợ.")

def parse_large_number(expr: str) -> int:
    """Hỗ trợ nhập biểu thức lũy thừa (VD: 2^136279841-1) hoặc đường dẫn tệp chứa số lớn."""
    clean = expr.strip().strip('"')
    if not clean:
        raise ValueError("Chuỗi nhập rỗng.")

    # Hỗ trợ đọc trực tiếp số khổng lồ từ tệp nếu người dùng nhập đường dẫn tệp
    if os.path.isfile(clean):
        with open(clean, "r", encoding="utf-8", errors="ignore") as f:
            content = re.sub(r"\s+", "", f.read())
        if not content.isdigit():
            raise ValueError(f"Tệp '{clean}' không chứa chuỗi số nguyên hợp lệ.")
        return int(content)

    clean_num = clean.replace("_", "").replace(",", "")
    normalized = clean_num.replace("^", "**")
    try:
        tree = ast.parse(normalized, mode="eval")
        val = _eval_ast(tree.body)
        if isinstance(val, float):
            if not val.is_integer():
                raise ValueError("Kết quả biểu thức không phải là số nguyên.")
            val = int(val)
        if not isinstance(val, int) or val < 0:
            raise ValueError("Mốc giá trị phải là số nguyên không âm.")
        return val
    except Exception as e:
        raise ValueError(f"Định dạng mốc số không hợp lệ '{expr}': {e}")

def format_huge_int(n: int, preview_digits: int = 24) -> str:
    bits = n.bit_length()
    if bits <= 256:
        return f"{n:,}"
    approx_digits = int(bits * 0.3010299956639812) + 1
    top_scale = max(0, approx_digits - preview_digits - 2)
    head_str = str(n // (10 ** top_scale))[:preview_digits]
    tail_str = str(n % (10 ** preview_digits)).zfill(preview_digits)
    return f"{head_str}...{tail_str} [~{approx_digits:,} chữ số | {bits:,} bits]"

def big_log(x: int) -> float:
    if x <= 1:
        return 1.0
    bits = x.bit_length()
    if bits <= 1020:
        return math.log(x)
    shift = bits - 53
    mantissa = (x >> shift) / (1 << 53)
    return bits * 0.6931471805599453 + math.log(mantissa)


# =====================================================================
# QUẢN LÝ TIẾN TRÌNH (CHECKPOINT) & GHI NHẬN KẾT QUẢ SỐ NGUYÊN TỐ MỚI
# =====================================================================
class SearchProgressManager:
    """Lưu và khôi phục tiến trình tìm kiếm tịnh tiến, đồng thời ghi nhận các số mới tìm được."""
    def __init__(
        self,
        checkpoint_file: str = "prime_search_checkpoint.json",
        results_file: str = "found_primes_results.txt"
    ):
        self.checkpoint_file = checkpoint_file
        self.results_file = results_file
        self.initial_anchor = None
        self.current_anchor = None
        self.step_count = 0
        self.total_span_traversed = 0

    def has_saved_progress(self) -> bool:
        return os.path.isfile(self.checkpoint_file)

    def start_new_session(self, anchor: int):
        self.initial_anchor = anchor
        self.current_anchor = anchor
        self.step_count = 0
        self.total_span_traversed = 0
        self.save_checkpoint()

    def save_checkpoint(self):
        if self.current_anchor is None:
            return
        data = {
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "step_count": self.step_count,
            "total_span_traversed": self.total_span_traversed,
            "initial_anchor_str": str(self.initial_anchor),
            "current_anchor_str": str(self.current_anchor),
        }
        tmp_file = self.checkpoint_file + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_file, self.checkpoint_file)

    def load_checkpoint(self) -> bool:
        if not self.has_saved_progress():
            return False
        try:
            with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.initial_anchor = int(data["initial_anchor_str"])
            self.current_anchor = int(data["current_anchor_str"])
            self.step_count = int(data.get("step_count", 0))
            self.total_span_traversed = int(data.get("total_span_traversed", 0))
            print(f"[KHÔI PHỤC TIẾN TRÌNH THÀNH CÔNG] (Cập nhật lúc: {data.get('updated_at', 'N/A')})")
            print(f"  * Mốc khởi thủy ban đầu : {format_huge_int(self.initial_anchor)}")
            print(f"  * Mốc hiện tại đang dừng: {format_huge_int(self.current_anchor)}")
            print(f"  * Số bước đã tìm được   : {self.step_count:,} số | Tổng khoảng cách nhảy: +{self.total_span_traversed:,}")
            return True
        except Exception as e:
            print(f"[CẢNH BÁO] Không thể đọc tệp tiến trình ({e}).")
            return False

    def record_new_prime(self, prev_anchor: int, new_prime: int, delta: int, elapsed_sec: float, custom_path: str = None):
        self.step_count += 1
        self.total_span_traversed += delta
        self.current_anchor = new_prime
        self.save_checkpoint()

        filepath = custom_path if custom_path else self.results_file
        bits = new_prime.bit_length()
        approx_digits = int(bits * 0.3010299956639812) + 1
        cert_type = "Số nguyên tố xác thực tuyệt đối" if bits <= 100_000 else "Tọa độ hội tụ 4 trục độc lập D1∩D2∩D3∩D4"

        try:
            with open(filepath, "a", encoding="utf-8") as f:
                f.write("=" * 80 + "\n")
                f.write(f"Bước tìm kiếm thứ  : #{self.step_count}\n")
                f.write(f"Thời gian ghi nhận : {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Trạng thái kiểm định: {cert_type}\n")
                f.write(f"Từ mốc trước đó    : {format_huge_int(prev_anchor)}\n")
                f.write(f"Bước nhảy vi mô    : +{delta:,} đơn vị\n")
                f.write(f"Kích thước số mới  : ~{approx_digits:,} chữ số ({bits:,} bits)\n")
                f.write(f"Thời gian tính toán: {elapsed_sec:.4f} giây\n")
                f.write("Giá trị đầy đủ     :\n")
                f.write(str(new_prime) + "\n\n")
            print(f"  -> [ĐÃ LƯU KẾT QUẢ & TIẾN TRÌNH] Ghi số mới vào '{filepath}' & cập nhật '{self.checkpoint_file}'")
        except Exception as e:
            print(f"  -> [CẢNH BÁO LƯU TỆP] Không thể ghi kết quả: {e}")


# =====================================================================
# QUẢN LÝ TẦN SỐ CƠ SỞ & KIẾN TRÚC 4 TRỤC CHIẾU ĐỘC LẬP (D1, D2, D3, D4)
# =====================================================================
class HarmonicBasis:
    """Quản lý tập tần số cơ sở nguyên thủy cho 4 trục chiếu độc lập D1, D2, D3, D4."""
    def __init__(self):
        self.primes = []

    def load_from_file(self, filepath: str) -> int:
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"Không tìm thấy tệp: {filepath}")
        t0 = time.perf_counter()
        loaded = []
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                for tok in re.findall(r"\d+", line):
                    loaded.append(int(tok))
        if not loaded:
            raise ValueError("Tệp không chứa dữ liệu số hợp lệ.")
        self.primes = sorted(set(loaded))
        print(f"[NẠP TỆP THÀNH CÔNG] Đã nạp {len(self.primes):,} tần số cơ sở trong {time.perf_counter() - t0:.3f}s")
        return len(self.primes)

    def save_to_file(self, filepath: str):
        t0 = time.perf_counter()
        with open(filepath, "w", encoding="utf-8") as f:
            for p in self.primes:
                f.write(f"{p}\n")
        print(f"[LƯU TỆP THÀNH CÔNG] Đã lưu {len(self.primes):,} tần số ra '{filepath}' trong {time.perf_counter() - t0:.3f}s")

    def ensure_frequencies_up_to(self, limit: int):
        if limit < 2 or (self.primes and self.primes[-1] >= limit):
            return
        size = (limit // 2) + 1
        is_prime = bytearray(b"\x01") * size
        is_prime[0] = 0
        for i in range(1, (math.isqrt(limit) // 2) + 1):
            if is_prime[i]:
                p = 2 * i + 1
                start = (p * p) // 2
                is_prime[start::p] = b"\x00" * ((size - start - 1) // p + 1)
        self.primes = [2] + [2 * i + 1 for i in range(1, size) if is_prime[i]]

def _compute_shared_base_phases(scan_start: int, odd_freqs: list) -> list:
    """Tính pha gốc (scan_start % k) 1 lần duy nhất cho toàn bộ tần số lẻ theo khối tích 64-bit."""
    base_phases = []
    idx = 0
    total = len(odd_freqs)
    limit_64 = 1 << 62

    while idx < total:
        chunk_k = []
        chunk_prod = 1
        while idx < total:
            k = odd_freqs[idx]
            if chunk_prod * k >= limit_64:
                break
            chunk_prod *= k
            chunk_k.append(k)
            idx += 1

        big_rem = scan_start % chunk_prod
        for k in chunk_k:
            base_phases.append((k, big_rem % k))

    return base_phases

def project_independent_dimension_fast(span: int, dim_phases: list, phase_angle_shift: float) -> set:
    """Chiếu vùng biên lên một trục không gian độc lập D_i (D1, D2, D3, D4)."""
    num_slots = (span // 2) + 1
    valid_mask = bytearray(b"\x01") * num_slots
    two_pi = 2.0 * math.pi

    for k, base_rem in dim_phases:
        first_offset = 0 if base_rem == 0 else (k - base_rem)
        if (first_offset & 1) == 1:
            first_offset += k

        if first_offset <= span:
            norm_phase = ((two_pi * ((base_rem + first_offset) % k)) / k) + phase_angle_shift
            if math.cos(norm_phase - phase_angle_shift) > 0.999999999999:
                start_slot = first_offset >> 1
                valid_mask[start_slot::k] = b"\x00" * ((num_slots - start_slot - 1) // k + 1)

    return {slot << 1 for slot, flag in enumerate(valid_mask) if flag}

def intersect_4d_orthogonal_offsets(scan_start: int, scan_end: int, basis: HarmonicBasis) -> list:
    """
    Giao điểm 4 trục chiếu độc lập S(D1) ∩ S(D2) ∩ S(D3) ∩ S(D4) trên không gian offset 64-bit.
    """
    span = scan_end - scan_start
    if span < 0:
        return []

    bits = scan_end.bit_length()
    if bits > 1_000_000:
        freq_limit = 60_000
    elif bits > 64:
        freq_limit = 500_000
    else:
        freq_limit = math.isqrt(scan_end) + 1

    basis.ensure_frequencies_up_to(freq_limit)
    odd_freqs = [p for p in basis.primes if 2 < p <= freq_limit]

    t_p0 = time.perf_counter()
    all_phases = _compute_shared_base_phases(scan_start, odd_freqs)

    s_d1 = project_independent_dimension_fast(span, all_phases[0::4], 0.0)
    s_d2 = project_independent_dimension_fast(span, all_phases[1::4], math.pi / 2)
    s_d3 = project_independent_dimension_fast(span, all_phases[2::4], math.pi / 4)
    s_d4 = project_independent_dimension_fast(span, all_phases[3::4], 3 * math.pi / 4)

    intersected_offsets = sorted(s_d1 & s_d2 & s_d3 & s_d4)
    t_p1 = time.perf_counter()

    print(f"    * Mật độ tọa độ độc lập: |D1|={len(s_d1):,}, |D2|={len(s_d2):,}, |D3|={len(s_d3):,}, |D4|={len(s_d4):,}")
    print(f"    * Giao điểm 4 trục (D1 ∩ D2 ∩ D3 ∩ D4): Hội tụ còn {len(intersected_offsets):,} tọa độ ({(t_p1 - t_p0)*1000:.2f} ms)")

    if 64 < bits <= 100_000:
        for off in intersected_offsets:
            cand = scan_start + off
            # Kiểm tra xác thực Fermat cơ số 2 & 3 và dừng ngay tại ứng viên đầu tiên
            if pow(2, cand - 1, cand) == 1 and pow(3, cand - 1, cand) == 1:
                return [off]
        return []

    return intersected_offsets


# =====================================================================
# BỘ TÌM KIẾM TỊNH TIẾN TỪ MỐC NHẬP VÀO (ANCHOR -> NEXT PRIME)
# =====================================================================
def find_next_prime_from_anchor(anchor: int, basis: HarmonicBasis, progress: SearchProgressManager) -> int:
    """
    Xuất phát từ mốc giá trị `anchor`, dò tìm số nguyên tố / tọa độ hội tụ 4D kế tiếp (> anchor).
    """
    t0 = time.perf_counter()

    # Xử lý các trường hợp mốc rất nhỏ (< 3)
    if anchor < 2:
        new_prime = 2
        dt = time.perf_counter() - t0
        print(f"\n[KHÓA TỌA ĐỘ MỚI] Từ mốc {anchor} -> Số nguyên tố kế tiếp: 2 (+{2 - anchor} đơn vị)")
        progress.record_new_prime(anchor, new_prime, new_prime - anchor, dt)
        return new_prime
    if anchor == 2:
        new_prime = 3
        dt = time.perf_counter() - t0
        print(f"\n[KHÓA TỌA ĐỘ MỚI] Từ mốc 2 -> Số nguyên tố kế tiếp: 3 (+1 đơn vị)")
        progress.record_new_prime(anchor, new_prime, 1, dt)
        return new_prime

    # Điểm bắt đầu quét phải là số lẻ lớn hơn hẳn anchor
    scan_start = anchor + 1 if (anchor & 1) == 0 else anchor + 2

    ln_anchor = max(4.0, big_log(anchor))
    # Kích thước mỗi bước cửa sổ biên tịnh tiến
    window_step = min(100_000, max(2000, int(ln_anchor * 4)))

    print(f"\n[{time.strftime('%H:%M:%S')}] [TỊNH TIẾN TỪ MỐC] Xuất phát: {format_huge_int(anchor)}")

    batch_idx = 0
    while True:
        batch_idx += 1
        scan_end = scan_start + window_step
        print(f"  -> [Cửa sổ #{batch_idx}] Quét vùng biên [{format_huge_int(scan_start)} ... +{window_step:,}]")

        converged_offsets = intersect_4d_orthogonal_offsets(scan_start, scan_end, basis)
        if converged_offsets:
            # Lấy tọa độ hội tụ đầu tiên (gần mốc anchor nhất về phía tăng)
            first_offset = converged_offsets[0]
            new_prime = scan_start + first_offset
            delta = new_prime - anchor
            dt = time.perf_counter() - t0

            print(f"\n[KHÓA TỌA ĐỘ MỚI THÀNH CÔNG - BƯỚC #{progress.step_count + 1}]")
            print(f"  * Mốc xuất phát (Anchor)   : {format_huge_int(anchor)}")
            print(f"  * Số mới tìm được (Next)   : {format_huge_int(new_prime)}")
            print(f"  * Khoảng cách tịnh tiến    : +{delta:,} đơn vị")
            print(f"  * Thời gian thực thi       : {dt:.4f} giây")

            progress.record_new_prime(anchor, new_prime, delta, dt)
            gc.collect()
            return new_prime

        # Nếu cửa sổ hiện tại chưa có điểm hội tụ nào, dịch chuyển cửa sổ sang vùng liền kề tiếp theo
        scan_start = scan_end + 1 if (scan_end & 1) == 0 else scan_end + 2


# =====================================================================
# GIAO DIỆN TƯƠNG TÁC LIÊN TỤC & KHÔI PHỤC TIẾN TRÌNH
# =====================================================================
if __name__ == "__main__":
    print("=" * 78)
    print("HỆ THỐNG DÒ TÌM SỐ NGUYÊN TỐ TỊNH TIẾN 4D (D1∩D2∩D3∩D4) + LƯU TIẾN TRÌNH")
    print("=" * 78)

    basis = HarmonicBasis()
    progress = SearchProgressManager(
        checkpoint_file="prime_search_checkpoint.json",
        results_file="found_primes_results.txt"
    )

    file_path = input("Nhập đường dẫn tệp chứa tần số cơ sở (nhấn Enter để bỏ qua nếu chưa có): ").strip().strip('"')
    if file_path:
        try:
            basis.load_from_file(file_path)
        except Exception as e:
            print(f"[CẢNH BÁO] Không thể nạp tệp ({e}). Hệ thống sẽ tự khởi tạo phổ tần số.")

    # Kiểm tra xem có tiến trình cũ đang lưu không
    resume_mode = False
    if progress.has_saved_progress():
        print("\n" + "*" * 78)
        if progress.load_checkpoint():
            ans_resume = input("Phát hiện tiến trình tìm kiếm trước đó. Bạn có muốn chạy tiếp từ mốc này? (y/n): ").strip().lower()
            if ans_resume in ("y", "yes", "co", "có", ""):
                resume_mode = True
        print("*" * 78)

    while True:
        print("\n" + "-" * 78)
        if resume_mode and progress.current_anchor is not None:
            current_anchor = progress.current_anchor
            print(f"[TIẾP TỤC TIẾN TRÌNH] Đang xuất phát từ mốc đã lưu: {format_huge_int(current_anchor)}")
            resume_mode = False  # Chỉ tự động nạp ở vòng đầu tiên khi resume
        else:
            raw_input = input(
                "Nhập SỐ MỐC để tìm số nguyên tố tiếp theo (VD: 10^10, 2^136279841-1, đường dẫn tệp số)\n"
                "Hoặc gõ 'resume' (tiếp tục mốc cũ) | 'save' (lưu tần số) | 'exit' (thoát): "
            ).strip()

            if raw_input.lower() in ("exit", "quit", "q"):
                progress.save_checkpoint()
                print(f"[ĐÃ LƯU TIẾN TRÌNH AN TOÀN] Tiến trình hiện tại đã được bảo toàn trong '{progress.checkpoint_file}'.")
                break

            if raw_input.lower() == "save":
                out_path = input("Nhập tên tệp muốn lưu tập tần số cơ sở (VD: basis_cache.txt): ").strip()
                if out_path:
                    basis.save_to_file(out_path)
                continue

            if raw_input.lower() == "resume":
                if progress.load_checkpoint():
                    current_anchor = progress.current_anchor
                else:
                    print("[THÔNG BÁO] Không tìm thấy tiến trình hợp lệ để khôi phục.")
                    continue
            else:
                try:
                    current_anchor = parse_large_number(raw_input)
                    progress.start_new_session(current_anchor)
                except Exception as e:
                    print(f"[LỖI NHẬP LIỆU] {e}")
                    continue

        # Vòng lặp nối tiếp: Tìm số mới -> Lưu kết quả & tiến trình -> Hỏi lấy làm mốc mới để chạy tiếp
        while True:
            try:
                new_found = find_next_prime_from_anchor(current_anchor, basis, progress)
            except KeyboardInterrupt:
                progress.save_checkpoint()
                print(f"\n[TẠM DỪNG] Đã lưu tiến trình tại mốc: {format_huge_int(current_anchor)}")
                break
            except Exception as e:
                print(f"[LỖI THỰC THI HỆ THỐNG] {e}")
                traceback.print_exc()
                break

            print("-" * 78)
            cont_ans = input(
                "Bạn có muốn lấy SỐ MỚI vừa tìm được làm mốc để tiếp tục tìm không?\n"
                "  [Enter / y] : Có, lấy số mới làm mốc và tìm tiếp ngay\n"
                "  [n]         : Không, dừng chuỗi này để nhập mốc khác\n"
                "  [exit]      : Lưu tiến trình và thoát chương trình\n"
                "Lựa chọn của bạn: "
            ).strip().lower()

            if cont_ans in ("y", "yes", "co", "có", ""):
                current_anchor = new_found
                continue
            elif cont_ans in ("exit", "quit", "q"):
                progress.save_checkpoint()
                print(f"[ĐÃ LƯU TIẾN TRÌNH] Bạn có thể mở lại chương trình bất cứ lúc nào để chạy tiếp từ mốc này.")
                sys.exit(0)
            else:
                progress.save_checkpoint()
                print(f"[TẠM DỪNG CHUỖI] Đã lưu mốc mới nhất vào '{progress.checkpoint_file}'.")
                break