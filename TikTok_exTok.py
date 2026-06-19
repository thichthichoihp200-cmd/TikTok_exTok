import requests
import json
import time
import threading
import os
from queue import Queue
from colorama import Fore, Style, init

# Khởi tạo colorama
init(autoreset=True)

CONFIG_FILE = "config_TikTok_ExTok.json"
USER_AGENT = "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"

class ExTokBot:
    def __init__(self):
        self.base_url = "https://api.extok.net/api"
        self.task_queue = Queue()
        self.load_config()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                self.token = json.load(f).get("token")
        else:
            self.token = input(f"{Fore.CYAN}Chưa có Token, hãy nhập Token: {Style.RESET_ALL}").strip()
            with open(CONFIG_FILE, "w") as f:
                json.dump({"token": self.token}, f)
        print(f"{Fore.GREEN}[*] Đã xác thực với Token: {self.token[:10]}...{Style.RESET_ALL}")

    def get_headers(self):
        return {"Authorization": f"Bearer {self.token}", "User-Agent": USER_AGENT, "Content-Type": "application/json"}

    def display_accounts(self, accounts):
        print(f"\n{Fore.MAGENTA}" + "="*95)
        print(f"{'STT':<5} | {'ID':<8} | {'Nickname':<20} | {'Jobs Hôm Nay':<12} | {'Tổng Jobs':<10} | {'Số dư'}")
        print("-"*95 + Style.RESET_ALL)
        for idx, acc in enumerate(accounts):
            nick = str(acc.get('nickname', 'N/A'))[:18]
            balance = acc.get('balance', 0)
            print(f"{idx:<5} | {acc.get('id'):<8} | {nick:<20} | {acc.get('count_jobs_today',0):<12} | {acc.get('total_jobs',0):<10} | {Fore.YELLOW}{balance}{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}" + "="*95 + Style.RESET_ALL + "\n")

    def get_accounts(self):
        try:
            res = requests.get(f"{self.base_url}/tiktok-account", headers=self.get_headers())
            data = res.json().get("data", [])
            return [a for a in data if a.get('is_banned') == 0]
        except Exception as e:
            print(f"{Fore.RED}[!] Lỗi kết nối server: {e}{Style.RESET_ALL}")
            return []

    def countdown(self, seconds, label, thread_name):
        for i in range(seconds, 0, -1):
            print(f"\r{Fore.CYAN}[Luồng {thread_name}] {Fore.YELLOW}{label}: {i}s...{Style.RESET_ALL} ", end="", flush=True)
            time.sleep(1)
        print(f"\r{Fore.CYAN}[Luồng {thread_name}] {Fore.GREEN}{label}: Đã xong!{' '*15}{Style.RESET_ALL}")

    def worker(self, delay_job, delay_complete, max_fails, max_jobs):
        thread_name = threading.current_thread().name
        while True:
            acc = self.task_queue.get()
            if acc is None:
                self.task_queue.task_done()
                break
            
            u_id = acc['unique_id']
            acc_name = acc.get('nickname', 'Unknown')
            balance = acc.get('balance', 0)
            jobs_done = 0 
            fail_count = 0
            empty_scan_count = 0
            
            print(f"\n{Fore.CYAN}[Luồng {thread_name}] Bắt đầu làm cho: {acc_name} | {Fore.YELLOW}Số dư: {balance} Xu{Style.RESET_ALL}")

            while jobs_done < max_jobs:
                try:
                    res = requests.get(f"{self.base_url}/tiktok-jobs", headers=self.get_headers(), params={"unique_id": u_id, "type": "follow"})
                    jobs = res.json().get("data", [])
                    
                    if not jobs:
                        empty_scan_count += 1
                        if empty_scan_count >= 2:
                            print(f"{Fore.YELLOW}[!] {acc_name} hết job, chuyển acc tiếp theo.{Style.RESET_ALL}")
                            break
                        time.sleep(3)
                        continue
                    
                    empty_scan_count = 0
                    for job in jobs:
                        if jobs_done >= max_jobs: break
                        print(f"{Fore.BLUE}[Luồng {thread_name}] {Fore.WHITE}Acc: {acc_name} | {Fore.GREEN}Job: {job.get('type')} | @{job['tiktok_username']}{Style.RESET_ALL}")
                        self.countdown(delay_job, "Chờ làm job", thread_name)
                        
                        complete_res = requests.post(f"{self.base_url}/tiktok-jobs/complete", 
                                      json={"job_id": job['id'], "unique_id": u_id, "success": True}, headers=self.get_headers())
                        
                        if complete_res.status_code == 200:
                            jobs_done += 1
                            fail_count = 0
                            print(f"{Fore.GREEN}[+] Hoàn thành job thành công!{Style.RESET_ALL}")
                            self.countdown(delay_complete, "Nghỉ sau job", thread_name)
                        else:
                            fail_count += 1
                            print(f"{Fore.RED}[!] Job lỗi ({fail_count}/{max_fails}){Style.RESET_ALL}")
                            if fail_count >= max_fails: 
                                print(f"{Fore.RED}[!] Tài khoản {acc_name} đã lỗi quá {max_fails} lần. Chuyển sang tài khoản tiếp theo...{Style.RESET_ALL}")
                                jobs_done = max_jobs 
                                break
                except Exception as e:
                    print(f"\n{Fore.RED}[!] Lỗi xử lý {acc_name}: {e}{Style.RESET_ALL}")
                    break
            self.task_queue.task_done()

    def start(self):
        mode = input(f"{Fore.YELLOW}Chọn chế độ (1: Đa luồng, 2: Chọn lọc): {Style.RESET_ALL}")
        delay_job = int(input(f"{Fore.YELLOW}Thời gian chờ job (s): {Style.RESET_ALL}"))
        delay_complete = int(input(f"{Fore.YELLOW}Thời gian nghỉ sau job (s): {Style.RESET_ALL}"))
        max_fails = int(input(f"{Fore.YELLOW}Số lần lỗi tối đa: {Style.RESET_ALL}"))
        max_jobs = int(input(f"{Fore.YELLOW}Số job mỗi acc: {Style.RESET_ALL}"))
        
        if mode == "2":
            accounts = self.get_accounts()
            self.display_accounts(accounts)
            selection = input(f"{Fore.YELLOW}Nhập STT tài khoản (vd: 1,3,4): {Style.RESET_ALL}")
            selected_indices = [int(i.strip()) for i in selection.split(',')]
            num_threads = min(len(selected_indices), 5)
        else:
            num_threads = int(input(f"{Fore.YELLOW}Nhập số luồng chạy: {Style.RESET_ALL}"))

        while True:
            accounts = self.get_accounts()
            if not accounts:
                print(f"{Fore.RED}[!] Không có tài khoản, thử lại sau 60s...{Style.RESET_ALL}")
                time.sleep(60)
                continue
            
            if mode == "1":
                for acc in accounts: self.task_queue.put(acc)
            else:
                for idx in selected_indices:
                    if 0 <= idx < len(accounts): self.task_queue.put(accounts[idx])
            
            for _ in range(num_threads): self.task_queue.put(None)
            
            threads = []
            for i in range(num_threads):
                t = threading.Thread(target=self.worker, args=(delay_job, delay_complete, max_fails, max_jobs), name=str(i+1))
                t.start()
                threads.append(t)
            
            for t in threads: t.join()
            print(f"\n{Fore.MAGENTA}[*] Hoàn thành vòng chạy. Nghỉ 30s rồi bắt đầu lại...{Style.RESET_ALL}")
            time.sleep(30)

if __name__ == "__main__":
    bot = ExTokBot()
    bot.start()
