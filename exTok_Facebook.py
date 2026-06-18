import requests
import os
import time
import json
import subprocess
import re
import random
import sys
from colorama import Fore, Style, init

# Khởi tạo màu sắc
init(autoreset=True)

# --- CẤU HÌNH ---
CONFIG_FILE = "config_exTok.json"
ERROR_FILE = "error_jobs_exTok.json"
BASE_URL = "https://api.extok.net/api"

# --- HÀM HỖ TRỢ ---
def print_header(text):
    print(Fore.MAGENTA + Style.BRIGHT + f"\n=== {text} ===")

def print_success(text):
    print(Fore.GREEN + Style.BRIGHT + f"[✅] {text}")

def print_error(text):
    print(Fore.RED + Style.BRIGHT + f"[!] {text}")

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            try: return json.load(f)
            except: return {"TOKEN": "", "ACCOUNTS": {}}
    return {"TOKEN": "", "ACCOUNTS": {}}

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_error_jobs():
    if os.path.exists(ERROR_FILE):
        with open(ERROR_FILE, "r") as f:
            try: return json.load(f)
            except: return []
    return []

def save_error_job(job_id):
    errors = load_error_jobs()
    if job_id not in errors:
        errors.append(job_id)
        with open(ERROR_FILE, "w") as f:
            json.dump(errors, f)

def extract_uid(url_or_uid):
    patterns = [r"id=(\d+)", r"facebook\.com/(\d+)"]
    for pattern in patterns:
        match = re.search(pattern, url_or_uid)
        if match:
            return match.group(1)
    return url_or_uid.strip()

# --- HÀM XỬ LÝ JOB ---
def run_jobs(headers, uid, package, delay_min, delay_max):
    print_header(f"ĐANG CHẠY JOB CHO UID: {uid}")
    print(Fore.CYAN + "Điều khiển: [Enter] Hoàn thành | [n] Bỏ qua | [x] Báo lỗi (Lưu vĩnh viễn)")
    
    while True:
        try:
            params = {"fb_id": uid, "limit": 1}
            res = requests.get(f"{BASE_URL}/facebook-jobs", params=params, headers=headers, timeout=10).json()
            
            if res.get("status") == 200 and res.get("data"):
                job = res["data"][0]
                job_id = job['id']
                
                # Kiểm tra danh sách lỗi
                if job_id in load_error_jobs():
                    print(Fore.RED + f"Job {job_id} đã nằm trong danh sách lỗi, đang bỏ qua...")
                    requests.post(f"{BASE_URL}/facebook-jobs/skip", json={"job_id": job_id, "fb_id": uid}, headers=headers)
                    continue

                print(Fore.GREEN + f"\n=> Loại Job: {job['type']} | Link: {job['link']}")
                
                # Mở trình duyệt
                subprocess.run(['am', 'start', '-n', f'{package}/mark.via.Shell', '-a', 'android.intent.action.VIEW', '-d', job["link"]],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                # Chờ người dùng tương tác
                user_action = input(Fore.YELLOW + "\nNhập lệnh ([Enter]: Xong, [n]: Bỏ qua, [x]: Báo lỗi): ").strip().lower()
                
                if user_action == 'x':
                    save_error_job(job_id)
                    print_error(f"Đã lưu Job {job_id} vào danh sách lỗi!")
                    continue
                elif user_action == 'n':
                    requests.post(f"{BASE_URL}/facebook-jobs/skip", json={"job_id": job_id, "fb_id": uid}, headers=headers)
                    print(Fore.RED + "Đã bỏ qua job này.")
                    continue
                else:
                    # Mặc định là hoàn thành
                    resp = requests.post(f"{BASE_URL}/facebook-jobs/complete", json={"job_id": job_id, "uid": uid, "success": True}, headers=headers).json()
                    
                    if resp.get('status') == 200:
                        coin = resp.get('data', {}).get('coin', '0')
                        print_success(f"Hoàn thành! Xu cộng: {coin}")
                    else:
                        print_error(f"Lỗi từ server: {resp.get('message')}")
                    
            else:
                print(Fore.WHITE + "Chưa có job, đợi 30s...", end="\r")
                time.sleep(30)
        except Exception as e:
            print_error(f"Lỗi hệ thống: {e}")
            time.sleep(10)

# --- HÀM MAIN ---
def main():
    data = load_config()
    if not data["TOKEN"]:
        data["TOKEN"] = input(Fore.YELLOW + "Nhập JWT Token: ").strip()
        save_config(data)
    
    print_header("THIẾT LẬP THỜI GIAN CHỜ")
    d_min = int(input("Nhập Delay MIN (giây): ") or 5)
    d_max = int(input("Nhập Delay MAX (giây): ") or 10)
    
    while True:
        print_header("MENU QUẢN LÝ")
        print("1. Thêm tài khoản\n2. Chạy Job tự động\n3. Thoát")
        c = input("Chọn: ")
        
        if c == '1':
            uid = extract_uid(input("Nhập UID/Link: "))
            data["ACCOUNTS"][uid] = input("Nhập Package Name (ví dụ: mark.via.gp): ")
            save_config(data)
            print_success("Đã lưu tài khoản!")
        elif c == '2':
            keys = list(data["ACCOUNTS"].keys())
            if not keys:
                print_error("Chưa có tài khoản nào!")
                continue
            print(f"{Fore.CYAN}Danh sách tài khoản đã lưu:")
            for i, uid in enumerate(keys, 1): 
                print(f"{i}. {uid}")
            
            user_input = input("Chọn STT hoặc dán Link/UID: ").strip()
            
            if user_input.isdigit() and int(user_input) <= len(keys):
                target_uid = keys[int(user_input) - 1]
            else:
                target_uid = extract_uid(user_input)
            
            if target_uid in data["ACCOUNTS"]:
                run_jobs({"Authorization": f"Bearer {data['TOKEN']}", "Content-Type": "application/json"}, 
                         target_uid, data["ACCOUNTS"][target_uid], d_min, d_max)
            else:
                print_error("Không tìm thấy tài khoản này trong cấu hình!")
        else: break

if __name__ == "__main__":
    main()
