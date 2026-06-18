import requests
import json
import time
import threading
import os
from queue import Queue
from datetime import datetime
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
        print(f"\n{Fore.MAGENTA}" + "="*75)
        print(f"{'ID':<8} | {'Nickname':<20} | {'Jobs Hôm Nay':<12} | {'Tổng Jobs'}")
        print("-"*75 + Style.RESET_ALL)
        for acc in accounts:
            nick = str(acc.get('nickname', 'N/A'))[:18]
            print(f"{acc.get('id'):<8} | {nick:<20} | {acc.get('count_jobs_today',0):<12} | {acc.get('total_jobs',0)}")
        print(f"{Fore.MAGENTA}" + "="*75 + Style.RESET_ALL + "\n")

    def get_accounts(self):
        try:
            res = requests.get(f"{self.base_url}/tiktok-account", headers=self.get_headers())
            data = res.json().get("data", [])
            self.display_accounts(data)
            return [a for a in data if a.get('is_banned') == 0]
        except Exception as e:
            print(f"{Fore.RED}[!] Lỗi kết nối server: {e}{Style.RESET_ALL}")
            return []

    def countdown(self, seconds, label, thread_name):
        for i in range(seconds, 0, -1):
            print(f"\r{Fore.CYAN}[Luồng {thread_name}] {Fore.YELLOW}{label}: {i}s...{Style.RESET_ALL} ", end="", flush=True)
            time.sleep(1)
        print(f"\r{Fore.CYAN}[Luồng {thread_name}] {Fore.GREEN}{label}: Đã xong!{' '*15}{Style.RESET_ALL}")

    def worker(self, delay_job, delay_complete, max_fails):
        thread_name = threading.current_thread().name
        while True:
            acc = self.task_queue.get()
            if acc is None: break
            
            u_id = acc['unique_id']
            acc_name = acc.get('nickname', 'Unknown')
            fail_count = 0
            
            try:
                res = requests.get(f"{self.base_url}/tiktok-jobs", headers=self.get_headers(), params={"unique_id": u_id, "type": "follow"})
                jobs = res.json().get("data", [])
                
                for job in jobs:
                    if fail_count >= max_fails:
                        print(f"\n{Fore.RED}[!] Acc {acc_name} lỗi quá {max_fails} lần, chuyển acc!{Style.RESET_ALL}")
                        break
                    
                    print(f"\n{Fore.BLUE}[Luồng {thread_name}] {Fore.WHITE}Acc: {acc_name} | {Fore.GREEN}Job: {job.get('type', 'follow')} | {Fore.YELLOW}Đích: @{job['tiktok_username']}{Style.RESET_ALL}")
                    
                    self.countdown(delay_job, "Chờ làm job", thread_name)
                    
                    complete_res = requests.post(f"{self.base_url}/tiktok-jobs/complete", 
                                  json={"job_id": job['id'], "unique_id": u_id, "success": True},
                                  headers=self.get_headers())
                    
                    if complete_res.status_code == 200:
                        fail_count = 0
                        self.countdown(delay_complete, "Nghỉ sau job", thread_name)
                    else:
                        fail_count += 1
                        print(f"{Fore.RED}[!] {acc_name} thất bại lần {fail_count}/{max_fails}{Style.RESET_ALL}")
            except Exception as e:
                print(f"\n{Fore.RED}[!] Lỗi xử lý acc {acc_name}: {e}{Style.RESET_ALL}")
            
            self.task_queue.task_done()

    def start(self):
        accounts = self.get_accounts()
        
        num_threads = int(input(f"{Fore.YELLOW}Nhập số luồng chạy: {Style.RESET_ALL}"))
        delay_job = int(input(f"{Fore.YELLOW}Thời gian chờ trước khi làm job (s): {Style.RESET_ALL}"))
        delay_complete = int(input(f"{Fore.YELLOW}Thời gian nghỉ sau khi hoàn thành (s): {Style.RESET_ALL}"))
        max_fails = int(input(f"{Fore.YELLOW}Số lần thất bại liên tục để đổi acc: {Style.RESET_ALL}"))

        for i in range(num_threads):
            t = threading.Thread(target=self.worker, args=(delay_job, delay_complete, max_fails), name=str(i+1))
            t.daemon = True
            t.start()

        for acc in accounts:
            self.task_queue.put(acc)

        print(f"{Fore.GREEN}[*] Bot đã khởi động. Đang đợi luồng xử lý...{Style.RESET_ALL}")
        
        last_reset_date = None
        while True:
            now = datetime.now()
            if now.hour == 0 and now.day != last_reset_date:
                print(f"\n{Fore.MAGENTA}[!] Chuyển sang ngày mới, nạp lại danh sách...{Style.RESET_ALL}")
                accounts = self.get_accounts()
                for acc in accounts:
                    self.task_queue.put(acc)
                last_reset_date = now.day
            time.sleep(60)

if __name__ == "__main__":
    bot = ExTokBot()
    bot.start()
