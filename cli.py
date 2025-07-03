#!/usr/bin/env python3
import json
import base64
import hashlib
import time
import sys
import re
import random
import string
import os
import shutil
import asyncio
import aiohttp
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Tuple, List, Dict, Any
import nacl.signing
import textwrap

# Enhanced Color Palette
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'
    BLINK = '\033[5m'
    REVERSE = '\033[7m'
    
    # Foreground colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright foreground colors
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # Background colors
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'
    
    # Custom combinations
    SUCCESS = '\033[92m'
    ERROR = '\033[91m'
    WARNING = '\033[93m'
    INFO = '\033[96m'
    HEADER = '\033[95m'

# UI Elements and Symbols
class UI:
    # Box drawing
    BOX_HORIZONTAL = '─'
    BOX_VERTICAL = '│'
    BOX_TOP_LEFT = '┌'
    BOX_TOP_RIGHT = '┐'
    BOX_BOTTOM_LEFT = '└'
    BOX_BOTTOM_RIGHT = '┘'
    BOX_CROSS = '┼'
    BOX_T_DOWN = '┬'
    BOX_T_UP = '┴'
    BOX_T_RIGHT = '├'
    BOX_T_LEFT = '┤'
    
    # Double box drawing
    DBOX_HORIZONTAL = '═'
    DBOX_VERTICAL = '║'
    DBOX_TOP_LEFT = '╔'
    DBOX_TOP_RIGHT = '╗'
    DBOX_BOTTOM_LEFT = '╚'
    DBOX_BOTTOM_RIGHT = '╝'
    
    # Progress indicators
    PROGRESS_EMPTY = '░'
    PROGRESS_QUARTER = '▒'
    PROGRESS_HALF = '▓'
    PROGRESS_FULL = '█'
    
    # Arrows and symbols
    ARROW_RIGHT = '→'
    ARROW_LEFT = '←'
    ARROW_UP = '↑'
    ARROW_DOWN = '↓'
    BULLET = '•'
    CHECK = '✓'
    CROSS = '✗'
    STAR = '★'
    HEART = '♥'
    DIAMOND = '♦'
    
    # Spinners
    SPINNER_DOTS = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    SPINNER_LINE = ['|', '/', '─', '\\']
    SPINNER_ARROW = ['←', '↖', '↑', '↗', '→', '↘', '↓', '↙']
    SPINNER_CIRCLE = ['◐', '◓', '◑', '◒']
    SPINNER_BLOCK = ['▖', '▘', '▝', '▗']

# Constants
MICRO_UNIT = 1_000_000
ADDRESS_REGEX = re.compile(r"^oct[1-9A-HJ-NP-Za-km-z]{44}$")
AMOUNT_REGEX = re.compile(r"^\d+(\.\d+)?$")

class Theme:
    """Customizable color themes"""
    def __init__(self, name="default"):
        self.name = name
        self.primary = Colors.BRIGHT_CYAN
        self.secondary = Colors.BRIGHT_BLUE
        self.success = Colors.BRIGHT_GREEN
        self.error = Colors.BRIGHT_RED
        self.warning = Colors.BRIGHT_YELLOW
        self.info = Colors.BRIGHT_CYAN
        self.accent = Colors.BRIGHT_MAGENTA
        self.text = Colors.BRIGHT_WHITE
        self.text_dim = Colors.WHITE
        self.background = Colors.BG_BLACK
        self.box = Colors.WHITE
        self.header = Colors.BRIGHT_MAGENTA

class WalletClient:
    def __init__(self):
        self.priv_key: Optional[str] = None
        self.address: Optional[str] = None
        self.rpc_url: Optional[str] = None
        self.signing_key: Optional[nacl.signing.SigningKey] = None
        self.public_key: Optional[str] = None
        
        self.current_balance: Optional[float] = None
        self.current_nonce: Optional[int] = None
        self.last_update: float = 0
        self.last_history_update: float = 0
        
        self.transaction_history: List[Dict[str, Any]] = []
        self.session: Optional[aiohttp.ClientSession] = None
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.stop_flag = threading.Event()
        
        # UI State
        self.theme = Theme()
        self.spinner_idx = 0
        self.current_spinner = UI.SPINNER_DOTS
        self.animation_speed = 0.1
        self.show_animations = True
        self.terminal_width = 80
        self.terminal_height = 25
        self.refresh_rate = 30  # seconds
        
        # Auto-refresh task
        self.auto_refresh_task: Optional[asyncio.Task] = None
        
    def __del__(self):
        if self.session and not self.session.closed:
            asyncio.create_task(self.session.close())
        self.executor.shutdown(wait=False)

    # Terminal utilities
    @staticmethod
    def clear_screen():
        os.system('cls' if os.name == 'nt' else 'clear')

    def get_terminal_size(self) -> Tuple[int, int]:
        size = shutil.get_terminal_size((80, 25))
        self.terminal_width, self.terminal_height = size
        return size

    def move_cursor(self, x: int, y: int, text: str = "", color: str = ''):
        """Move cursor and optionally print text"""
        if text:
            print(f"\033[{y};{x}H{color}{text}{Colors.RESET}", end='')
        else:
            print(f"\033[{y};{x}H", end='')

    def hide_cursor(self):
        print('\033[?25l', end='')

    def show_cursor(self):
        print('\033[?25h', end='')

    def clear_line(self, y: int):
        self.move_cursor(1, y)
        print('\033[K', end='')

    def input_at(self, x: int, y: int, prompt: str = "", color: str = '') -> str:
        self.move_cursor(x, y, prompt, color)
        self.show_cursor()
        result = input()
        self.hide_cursor()
        return result

    async def async_input(self, x: int, y: int, prompt: str = "", color: str = '', 
                         placeholder: str = "", max_length: Optional[int] = None) -> str:
        """Enhanced async input with placeholder and max length"""
        self.move_cursor(x, y, prompt, color)
        if placeholder:
            self.move_cursor(x + len(prompt), y, placeholder, Colors.DIM)
        self.move_cursor(x + len(prompt), y)
        self.show_cursor()
        
        try:
            result = await asyncio.get_event_loop().run_in_executor(self.executor, input)
            if max_length and len(result) > max_length:
                result = result[:max_length]
            return result
        except:
            self.stop_flag.set()
            return ''
        finally:
            self.hide_cursor()

    def center_text(self, text: str, width: Optional[int] = None) -> int:
        """Calculate x position to center text"""
        if width is None:
            width = self.terminal_width
        return max(1, (width - len(text)) // 2)

    def wrap_text(self, text: str, width: int) -> List[str]:
        """Wrap text to fit within specified width"""
        return textwrap.wrap(text, width=width, break_long_words=False, break_on_hyphens=False)

    def draw_progress_bar(self, x: int, y: int, width: int, progress: float, 
                         show_percentage: bool = True, color: str = ''):
        """Draw a progress bar"""
        if not color:
            color = self.theme.success
            
        filled = int(width * progress)
        empty = width - filled
        
        bar = UI.PROGRESS_FULL * filled + UI.PROGRESS_EMPTY * empty
        self.move_cursor(x, y, f"[{bar}]", color)
        
        if show_percentage:
            percentage = f" {int(progress * 100)}%"
            self.move_cursor(x + width + 2, y, percentage, color)

    def draw_box(self, x: int, y: int, width: int, height: int, 
                 title: str = "", style: str = "single", color: str = ''):
        """Draw a box with customizable style"""
        if not color:
            color = self.theme.box
            
        if style == "double":
            h, v = UI.DBOX_HORIZONTAL, UI.DBOX_VERTICAL
            tl, tr = UI.DBOX_TOP_LEFT, UI.DBOX_TOP_RIGHT
            bl, br = UI.DBOX_BOTTOM_LEFT, UI.DBOX_BOTTOM_RIGHT
        else:
            h, v = UI.BOX_HORIZONTAL, UI.BOX_VERTICAL
            tl, tr = UI.BOX_TOP_LEFT, UI.BOX_TOP_RIGHT
            bl, br = UI.BOX_BOTTOM_LEFT, UI.BOX_BOTTOM_RIGHT
        
        # Top line
        self.move_cursor(x, y, f"{tl}{h * (width - 2)}{tr}", color)
        
        # Title
        if title:
            title_text = f" {title} "
            title_x = x + 2
            self.move_cursor(title_x, y, title_text, self.theme.header + Colors.BOLD)
        
        # Sides
        for i in range(1, height - 1):
            self.move_cursor(x, y + i, v, color)
            self.move_cursor(x + width - 1, y + i, v, color)
        
        # Bottom line
        self.move_cursor(x, y + height - 1, f"{bl}{h * (width - 2)}{br}", color)

    def draw_divider(self, x: int, y: int, width: int, style: str = "single", color: str = ''):
        """Draw a horizontal divider"""
        if not color:
            color = self.theme.box
            
        char = UI.DBOX_HORIZONTAL if style == "double" else UI.BOX_HORIZONTAL
        self.move_cursor(x, y, char * width, color)

    async def animated_text(self, x: int, y: int, text: str, color: str = '', 
                           delay: float = 0.02):
        """Display text with typewriter effect"""
        for i, char in enumerate(text):
            self.move_cursor(x + i, y, char, color)
            await asyncio.sleep(delay)

    async def flash_text(self, x: int, y: int, text: str, color: str = '', 
                        times: int = 3, delay: float = 0.2):
        """Flash text for emphasis"""
        for _ in range(times):
            self.move_cursor(x, y, text, color)
            await asyncio.sleep(delay)
            self.move_cursor(x, y, " " * len(text))
            await asyncio.sleep(delay)
        self.move_cursor(x, y, text, color)

    def load_wallet(self) -> bool:
        """Load wallet configuration from JSON file"""
        try:
            with open('wallet.json', 'r') as f:
                data = json.load(f)
            
            self.priv_key = data.get('priv')
            self.address = data.get('addr')
            self.rpc_url = data.get('rpc', 'https://octra.network')
            
            if not self.priv_key or not self.address:
                return False
                
            self.signing_key = nacl.signing.SigningKey(base64.b64decode(self.priv_key))
            self.public_key = base64.b64encode(self.signing_key.verify_key.encode()).decode()
            return True
        except Exception as e:
            print(f"{Colors.ERROR}Error loading wallet: {e}{Colors.RESET}")
            return False

    def fill_background(self):
        """Fill terminal with themed background"""
        self.clear_screen()
        print(self.theme.background, end='')
        cols, rows = self.get_terminal_size()
        for _ in range(rows):
            print(" " * cols)
        print("\033[H", end='')

    async def spinner_animation(self, x: int, y: int, message: str, spinner_type: List[str] = None):
        """Display customizable spinning animation"""
        if spinner_type is None:
            spinner_type = self.current_spinner
            
        try:
            while True:
                frame = spinner_type[self.spinner_idx % len(spinner_type)]
                self.move_cursor(x, y, f"{frame} {message}", self.theme.info)
                self.spinner_idx = (self.spinner_idx + 1) % len(spinner_type)
                await asyncio.sleep(self.animation_speed)
        except asyncio.CancelledError:
            self.clear_line(y)

    async def http_request(self, method: str, path: str, data: Optional[Dict] = None, 
                          timeout: int = 10) -> Tuple[int, str, Optional[Dict]]:
        """Make HTTP request to RPC endpoint"""
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout))
        
        try:
            url = f"{self.rpc_url}{path}"
            async with getattr(self.session, method.lower())(url, json=data if method == 'POST' else None) as resp:
                text = await resp.text()
                try:
                    json_data = json.loads(text) if text else None
                except:
                    json_data = None
                return resp.status, text, json_data
        except asyncio.TimeoutError:
            return 0, "timeout", None
        except Exception as e:
            return 0, str(e), None

    async def get_status(self) -> Tuple[Optional[int], Optional[float]]:
        """Get current nonce and balance with caching"""
        now = time.time()
        if self.current_balance is not None and (now - self.last_update) < self.refresh_rate:
            return self.current_nonce, self.current_balance
        
        # Parallel requests for efficiency
        results = await asyncio.gather(
            self.http_request('GET', f'/balance/{self.address}'),
            self.http_request('GET', '/staging', 5),
            return_exceptions=True
        )
        
        status, text, json_data = results[0] if not isinstance(results[0], Exception) else (0, str(results[0]), None)
        staging_status, _, staging_data = results[1] if not isinstance(results[1], Exception) else (0, None, None)
        
        if status == 200 and json_data:
            self.current_nonce = int(json_data.get('nonce', 0))
            self.current_balance = float(json_data.get('balance', 0))
            self.last_update = now
            
            # Check staging for pending transactions
            if staging_status == 200 and staging_data:
                our_txs = [tx for tx in staging_data.get('staged_transactions', []) if tx.get('from') == self.address]
                if our_txs:
                    self.current_nonce = max(self.current_nonce, max(int(tx.get('nonce', 0)) for tx in our_txs))
        elif status == 404:
            self.current_nonce, self.current_balance, self.last_update = 0, 0.0, now
        elif status == 200 and text and not json_data:
            # Parse text response
            try:
                parts = text.strip().split()
                if len(parts) >= 2:
                    self.current_balance = float(parts[0]) if parts[0].replace('.', '').isdigit() else 0.0
                    self.current_nonce = int(parts[1]) if parts[1].isdigit() else 0
                    self.last_update = now
            except:
                pass
                
        return self.current_nonce, self.current_balance

    async def get_history(self):
        """Fetch transaction history with improved caching"""
        now = time.time()
        if now - self.last_history_update < 60 and self.transaction_history:
            return
        
        status, text, json_data = await self.http_request('GET', f'/address/{self.address}?limit=20')
        if status != 200 or (not json_data and not text):
            return
        
        if json_data and 'recent_transactions' in json_data:
            tx_hashes = [ref["hash"] for ref in json_data.get('recent_transactions', [])]
            tx_results = await asyncio.gather(
                *[self.http_request('GET', f'/tx/{hash}', 5) for hash in tx_hashes],
                return_exceptions=True
            )
            
            existing_hashes = {tx['hash'] for tx in self.transaction_history}
            new_history = []
            
            for ref, result in zip(json_data.get('recent_transactions', []), tx_results):
                if isinstance(result, Exception):
                    continue
                    
                tx_status, _, tx_data = result
                if tx_status == 200 and tx_data and 'parsed_tx' in tx_data:
                    parsed = tx_data['parsed_tx']
                    tx_hash = ref['hash']
                    
                    if tx_hash in existing_hashes:
                        continue
                    
                    is_incoming = parsed.get('to') == self.address
                    amount_raw = parsed.get('amount_raw', parsed.get('amount', '0'))
                    amount = float(amount_raw) if '.' in str(amount_raw) else int(amount_raw) / MICRO_UNIT
                    
                    new_history.append({
                        'time': datetime.fromtimestamp(parsed.get('timestamp', 0)),
                        'hash': tx_hash,
                        'amt': amount,
                        'to': parsed.get('to') if not is_incoming else parsed.get('from'),
                        'type': 'in' if is_incoming else 'out',
                        'ok': True,
                        'nonce': parsed.get('nonce', 0),
                        'epoch': ref.get('epoch', 0)
                    })
            
            # Keep only recent transactions
            one_hour_ago = datetime.now() - timedelta(hours=1)
            self.transaction_history[:] = sorted(
                new_history + [tx for tx in self.transaction_history if tx.get('time', datetime.now()) > one_hour_ago],
                key=lambda x: x['time'],
                reverse=True
            )[:50]
            self.last_history_update = now
        elif status == 404 or (status == 200 and text and 'no transactions' in text.lower()):
            self.transaction_history.clear()
            self.last_history_update = now

    def create_transaction(self, to_address: str, amount: float, nonce: int) -> Tuple[Dict, str]:
        """Create and sign a transaction"""
        tx = {
            "from": self.address,
            "to_": to_address,
            "amount": str(int(amount * MICRO_UNIT)),
            "nonce": int(nonce),
            "ou": "1" if amount < 1000 else "3",
            "timestamp": time.time() + random.random() * 0.01
        }
        
        # Sign transaction
        tx_bytes = json.dumps(tx, separators=(",", ":")).encode()
        signature = base64.b64encode(self.signing_key.sign(tx_bytes).signature).decode()
        tx.update(signature=signature, public_key=self.public_key)
        
        # Calculate hash
        tx_hash = hashlib.sha256(tx_bytes).hexdigest()
        
        return tx, tx_hash

    async def send_transaction(self, tx: Dict) -> Tuple[bool, str, float, Optional[Dict]]:
        """Send transaction to network"""
        start_time = time.time()
        status, text, json_data = await self.http_request('POST', '/send-tx', tx)
        elapsed = time.time() - start_time
        
        if status == 200:
            if json_data and json_data.get('status') == 'accepted':
                return True, json_data.get('tx_hash', ''), elapsed, json_data
            elif text.lower().startswith('ok'):
                return True, text.split()[-1], elapsed, None
                
        return False, json.dumps(json_data) if json_data else text, elapsed, json_data

    async def display_wallet_info(self, x: int, y: int, width: int):
        """Display wallet information widget"""
        # Header
        self.draw_box(x, y, width, 8, "Wallet Info", "double")
        
        # Content
        content_x = x + 2
        
        # Address (shortened with ellipsis)
        self.move_cursor(content_x, y + 2, "Address:", self.theme.text_dim)
        addr_display = f"{self.address[:12]}...{self.address[-8:]}" if len(self.address) > 24 else self.address
        self.move_cursor(content_x + 10, y + 2, addr_display, self.theme.primary)
        
        # Balance with animation
        self.move_cursor(content_x, y + 3, "Balance:", self.theme.text_dim)
        if self.current_balance is not None:
            balance_str = f"{self.current_balance:,.6f} OCT"
            color = self.theme.success if self.current_balance > 0 else self.theme.text
            self.move_cursor(content_x + 10, y + 3, balance_str, color + Colors.BOLD)
        else:
            self.move_cursor(content_x + 10, y + 3, "Loading...", self.theme.warning)
        
        # Nonce
        self.move_cursor(content_x, y + 4, "Nonce:", self.theme.text_dim)
        nonce_str = str(self.current_nonce) if self.current_nonce is not None else "---"
        self.move_cursor(content_x + 10, y + 4, nonce_str, self.theme.text)
        
        # Public key (shortened)
        self.move_cursor(content_x, y + 5, "Public:", self.theme.text_dim)
        pub_display = f"{self.public_key[:20]}..." if len(self.public_key) > 20 else self.public_key
        self.move_cursor(content_x + 10, y + 5, pub_display, self.theme.secondary)
        
        # Network status indicator
        self.move_cursor(content_x, y + 6, "Network:", self.theme.text_dim)
        self.move_cursor(content_x + 10, y + 6, f"{UI.CHECK} Connected", self.theme.success)

    async def display_transaction_list(self, x: int, y: int, width: int, height: int):
        """Display transaction history with improved formatting"""
        self.draw_box(x, y, width, height, "Transaction History")
        
        content_x = x + 2
        header_y = y + 2
        
        if not self.transaction_history:
            # No transactions message
            no_tx_msg = "No transactions yet"
            msg_x = x + self.center_text(no_tx_msg, width)
            self.move_cursor(msg_x, y + height // 2, no_tx_msg, self.theme.text_dim)
            
            # Helpful hint
            hint = "Send your first transaction to get started!"
            hint_x = x + self.center_text(hint, width)
            self.move_cursor(hint_x, y + height // 2 + 2, hint, self.theme.info)
        else:
            # Header
            headers = [
                ("Time", 10),
                ("Type", 6),
                ("Amount", 14),
                ("Address", width - 38),
                ("Status", 8)
            ]
            
            header_x = content_x
            for header, w in headers:
                self.move_cursor(header_x, header_y, header, self.theme.header + Colors.BOLD)
                header_x += w
            
            # Divider
            self.draw_divider(content_x, header_y + 1, width - 4)
            
            # Transactions
            list_start = header_y + 2
            max_items = height - 6
            
            for idx, tx in enumerate(self.transaction_history[:max_items]):
                if idx >= max_items:
                    break
                
                row_y = list_start + idx
                col_x = content_x
                
                # Time
                time_str = tx['time'].strftime('%H:%M:%S')
                self.move_cursor(col_x, row_y, time_str, self.theme.text_dim)
                col_x += 10
                
                # Type with icon
                if tx['type'] == 'in':
                    type_str = f"{UI.ARROW_DOWN} IN "
                    type_color = self.theme.success
                else:
                    type_str = f"{UI.ARROW_UP} OUT"
                    type_color = self.theme.error
                self.move_cursor(col_x, row_y, type_str, type_color)
                col_x += 6
                
                # Amount
                amount_str = f"{tx['amt']:>12.6f}"
                amount_color = self.theme.success if tx['type'] == 'in' else self.theme.text
                self.move_cursor(col_x, row_y, amount_str, amount_color)
                col_x += 14
                
                # Address (truncated)
                addr = tx.get('to', '---')
                max_addr_len = width - 42
                if len(addr) > max_addr_len:
                    addr_display = f"{addr[:max_addr_len-3]}..."
                else:
                    addr_display = addr
                self.move_cursor(col_x, row_y, addr_display, self.theme.secondary)
                col_x = content_x + width - 10
                
                # Status
                is_pending = not tx.get('epoch')
                if is_pending:
                    status_str = "PENDING"
                    status_color = self.theme.warning + Colors.BLINK
                else:
                    status_str = f"#{tx.get('epoch', 0)}"
                    status_color = self.theme.text_dim
                self.move_cursor(col_x, row_y, status_str, status_color)

    async def display_menu(self, x: int, y: int, width: int, height: int):
        """Display enhanced command menu"""
        self.draw_box(x, y, width, height, "Commands", "double")
        
        menu_items = [
            ("1", "Send Transaction", "Transfer OCT to another address"),
            ("2", "Refresh", "Update balance and transactions"),
            ("3", "Multi Send", "Send to multiple addresses"),
            ("4", "Export Keys", "Backup wallet information"),
            ("5", "Clear History", "Remove transaction display"),
            ("6", "Settings", "Configure client options"),
            ("0", "Exit", "Close the application")
        ]
        
        item_y = y + 2
        for key, title, desc in menu_items:
            # Key in box
            self.move_cursor(x + 2, item_y, f"[{key}]", self.theme.accent + Colors.BOLD)
            
            # Title
            self.move_cursor(x + 7, item_y, title, self.theme.text)
            
            # Description on next line
            self.move_cursor(x + 7, item_y + 1, desc, self.theme.text_dim)
            
            item_y += 3
            
            # Divider between items (except last)
            if key != "0":
                self.draw_divider(x + 2, item_y - 1, width - 4, color=Colors.DIM)

    async def display_status_bar(self, y: int):
        """Display status bar at bottom of screen"""
        cols, _ = self.get_terminal_size()
        
        # Clear line
        self.clear_line(y)
        
        # Background
        self.move_cursor(1, y, " " * cols, self.theme.background)
        
        # Status sections
        sections = []
        
        # Connection status
        sections.append((f"{UI.CHECK} Connected", self.theme.success))
        
        # Last update
        if self.last_update > 0:
            time_since = int(time.time() - self.last_update)
            if time_since < 60:
                update_str = f"Updated {time_since}s ago"
            else:
                update_str = f"Updated {time_since // 60}m ago"
            sections.append((update_str, self.theme.text_dim))
        
        # Staging count
        _, _, staging_data = await self.http_request('GET', '/staging', 2)
        if staging_data:
            staging_count = len([tx for tx in staging_data.get('staged_transactions', []) 
                               if tx.get('from') == self.address])
            if staging_count > 0:
                sections.append((f"{staging_count} pending", self.theme.warning))
        
        # Time
        time_str = datetime.now().strftime('%H:%M:%S')
        sections.append((time_str, self.theme.text))
        
        # Draw sections
        x = 2
        for text, color in sections:
            self.move_cursor(x, y, text, color)
            x += len(text) + 3

    async def display_main_screen(self) -> str:
        """Display enhanced main screen"""
        self.hide_cursor()
        cols, rows = self.get_terminal_size()
        self.fill_background()
        
        # Animated header
        header_text = "OCTRA WALLET CLIENT"
        header_x = self.center_text(header_text)
        if self.show_animations:
            await self.animated_text(header_x, 2, header_text, self.theme.header + Colors.BOLD)
        else:
            self.move_cursor(header_x, 2, header_text, self.theme.header + Colors.BOLD)
        
        # Version info
        version = "v0.1.0"
        version_x = self.center_text(version)
        self.move_cursor(version_x, 3, version, self.theme.text_dim)
        
        # Layout calculations
        left_panel_width = min(35, cols // 3)
        right_panel_width = cols - left_panel_width - 3
        content_height = rows - 8
        
        # Left panel - Menu
        menu_height = min(22, content_height)
        await self.display_menu(2, 5, left_panel_width, menu_height)
        
        # Wallet info below menu
        if content_height > menu_height + 9:
            await self.display_wallet_info(2, 5 + menu_height + 1, left_panel_width)
        
        # Right panel - Transaction history
        await self.display_transaction_list(
            left_panel_width + 3, 5, 
            right_panel_width, content_height
        )
        
        # Status bar
        await self.display_status_bar(rows - 2)
        
        # Command prompt
        prompt = "Enter command: "
        prompt_x = 2
        prompt_y = rows - 1
        self.move_cursor(prompt_x, prompt_y, prompt, self.theme.accent + Colors.BOLD)
        
        # Get input
        self.show_cursor()
        command = await self.async_input(prompt_x + len(prompt), prompt_y, 
                                        color=self.theme.text + Colors.BOLD)
        self.hide_cursor()
        
        return command

    async def send_single_transaction(self):
        """Enhanced single transaction interface"""
        cols, rows = self.get_terminal_size()
        self.fill_background()
        
        # Calculate centered box dimensions
        box_width = min(80, cols - 4)
        box_height = min(24, rows - 4)
        box_x = (cols - box_width) // 2
        box_y = (rows - box_height) // 2
        
        self.draw_box(box_x, box_y, box_width, box_height, "Send Transaction", "double")
        
        # Progress indicator
        steps = ["Address", "Amount", "Confirm", "Send"]
        current_step = 0
        
        def draw_progress():
            progress_y = box_y + 2
            step_width = (box_width - 4) // len(steps)
            for i, step in enumerate(steps):
                step_x = box_x + 2 + (i * step_width)
                if i < current_step:
                    color = self.theme.success
                    symbol = UI.CHECK
                elif i == current_step:
                    color = self.theme.accent + Colors.BOLD
                    symbol = UI.ARROW_RIGHT
                else:
                    color = self.theme.text_dim
                    symbol = UI.BULLET
                
                self.move_cursor(step_x, progress_y, f"{symbol} {step}", color)
        
        # Step 1: Address
        draw_progress()
        
        # Address input section
        input_y = box_y + 5
        self.move_cursor(box_x + 2, input_y, "Recipient Address", self.theme.header)
        self.move_cursor(box_x + 2, input_y + 1, 
                        "Enter a valid OCT address (oct followed by 44 characters)", 
                        self.theme.text_dim)
        
        # Input field with border
        field_y = input_y + 3
        field_width = box_width - 6
        self.draw_box(box_x + 2, field_y, field_width, 3)
        
        to_address = await self.async_input(
            box_x + 4, field_y + 1,
            placeholder="oct...",
            color=self.theme.text
        )
        
        if not to_address or to_address.lower() == 'esc':
            return
        
        # Validate with visual feedback
        validation_y = field_y + 4
        if not ADDRESS_REGEX.match(to_address):
            await self.flash_text(box_x + 2, validation_y, 
                                f"{UI.CROSS} Invalid address format!", 
                                self.theme.error)
            
            # Show example
            self.move_cursor(box_x + 2, validation_y + 1, 
                           "Example: oct1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t", 
                           self.theme.info)
            await self.wait_for_key()
            return
        else:
            self.move_cursor(box_x + 2, validation_y, 
                           f"{UI.CHECK} Valid address", 
                           self.theme.success)
        
        # Step 2: Amount
        current_step = 1
        draw_progress()
        
        amount_y = validation_y + 3
        self.move_cursor(box_x + 2, amount_y, "Amount to Send", self.theme.header)
        
        # Show balance
        nonce, balance = await self.get_status()
        if balance is not None:
            self.move_cursor(box_x + 2, amount_y + 1, 
                           f"Available balance: {balance:,.6f} OCT", 
                           self.theme.info)
        
        # Amount input field
        amount_field_y = amount_y + 3
        self.draw_box(box_x + 2, amount_field_y, 30, 3)
        
        amount_str = await self.async_input(
            box_x + 4, amount_field_y + 1,
            placeholder="0.000000",
            color=self.theme.text
        )
        
        if not amount_str or amount_str.lower() == 'esc':
            return
        
        # Validate amount
        if not AMOUNT_REGEX.match(amount_str) or float(amount_str) <= 0:
            await self.flash_text(box_x + 2, amount_field_y + 4, 
                                f"{UI.CROSS} Invalid amount!", 
                                self.theme.error)
            await self.wait_for_key()
            return
        
        amount = float(amount_str)
        
        # Check balance
        if not balance or balance < amount:
            self.move_cursor(box_x + 2, amount_field_y + 4, 
                           f"{UI.CROSS} Insufficient balance! ({balance:.6f} < {amount:.6f})", 
                           self.theme.error)
            await self.wait_for_key()
            return
        
        # Step 3: Confirm
        current_step = 2
        draw_progress()
        
        # Clear previous content
        for i in range(5, box_height - 6):
            self.clear_line(box_y + i)
        
        # Transaction summary
        summary_y = box_y + 6
        self.draw_box(box_x + 4, summary_y, box_width - 8, 10, "Transaction Summary")
        
        details = [
            ("To:", f"{to_address[:20]}...{to_address[-10:]}"),
            ("Amount:", f"{amount:,.6f} OCT"),
            ("Fee:", f"{'0.001' if amount < 1000 else '0.003'} OCT"),
            ("Total:", f"{amount + (0.001 if amount < 1000 else 0.003):,.6f} OCT"),
            ("Nonce:", str(nonce + 1) if nonce is not None else "---")
        ]
        
        detail_y = summary_y + 2
        for label, value in details:
            self.move_cursor(box_x + 6, detail_y, label, self.theme.text_dim)
            self.move_cursor(box_x + 16, detail_y, value, self.theme.text + Colors.BOLD)
            detail_y += 1
        
        # Confirmation
        confirm_y = summary_y + 8
        self.move_cursor(box_x + 6, confirm_y, 
                        "Confirm transaction? [Y/N]: ", 
                        self.theme.accent + Colors.BOLD)
        
        confirm = await self.async_input(box_x + 34, confirm_y, color=self.theme.text)
        
        if confirm.strip().lower() != 'y':
            self.move_cursor(box_x + 6, confirm_y + 2, "Transaction cancelled", self.theme.warning)
            await self.wait_for_key()
            return
        
        # Step 4: Send
        current_step = 3
        draw_progress()
        
        # Sending animation
        send_y = box_y + box_height - 5
        spin_task = asyncio.create_task(
            self.spinner_animation(box_x + 6, send_y, "Sending transaction...", UI.SPINNER_CIRCLE)
        )
        
        # Create and send transaction
        tx, _ = self.create_transaction(to_address, amount, nonce + 1)
        success, tx_hash, elapsed, response = await self.send_transaction(tx)
        
        # Stop animation
        spin_task.cancel()
        try:
            await spin_task
        except asyncio.CancelledError:
            pass
        
        # Display result
        self.clear_line(send_y)
        
        if success:
            # Success animation
            await self.flash_text(box_x + 6, send_y, 
                                f"{UI.CHECK} Transaction sent successfully!", 
                                self.theme.success + Colors.BOLD)
            
            # Transaction details
            self.move_cursor(box_x + 6, send_y + 1, 
                           f"Hash: {tx_hash[:32]}...", 
                           self.theme.text_dim)
            self.move_cursor(box_x + 6, send_y + 2, 
                           f"Time: {elapsed:.2f}s", 
                           self.theme.text_dim)
            
            # Add to history
            self.transaction_history.append({
                'time': datetime.now(),
                'hash': tx_hash,
                'amt': amount,
                'to': to_address,
                'type': 'out',
                'ok': True
            })
            self.last_update = 0  # Force refresh
        else:
            # Error display
            self.move_cursor(box_x + 6, send_y, 
                           f"{UI.CROSS} Transaction failed!", 
                           self.theme.error + Colors.BOLD)
            
            # Error details
            error_msg = str(tx_hash)[:box_width - 12]
            self.move_cursor(box_x + 6, send_y + 1, 
                           f"Error: {error_msg}", 
                           self.theme.error)
        
        await self.wait_for_key()

    async def send_multi_transaction(self):
        """Enhanced multi-send interface with better UX"""
        cols, rows = self.get_terminal_size()
        self.fill_background()
        
        # Adaptive layout
        box_width = min(90, cols - 4)
        box_height = rows - 4
        box_x = (cols - box_width) // 2
        box_y = 2
        
        self.draw_box(box_x, box_y, box_width, box_height, "Multi-Send Transaction", "double")
        
        # Instructions panel
        inst_y = box_y + 2
        instructions = [
            "Enter recipients one per line in format: address amount",
            f"Example: oct{'x' * 44} 10.5",
            "Press Enter on empty line to finish, or type 'esc' to cancel"
        ]
        
        for i, inst in enumerate(instructions):
            self.move_cursor(box_x + 2, inst_y + i, inst, 
                           self.theme.info if i == 0 else self.theme.text_dim)
        
        self.draw_divider(box_x + 2, inst_y + 4, box_width - 4)
        
        # Recipients list
        recipients = []
        total_amount = 0.0
        input_start_y = inst_y + 6
        max_recipients = (box_height - 16) // 2
        current_line = 0
        
        # Table header
        self.move_cursor(box_x + 2, input_start_y - 1, "# ", self.theme.header)
        self.move_cursor(box_x + 5, input_start_y - 1, "Address", self.theme.header)
        self.move_cursor(box_x + 55, input_start_y - 1, "Amount", self.theme.header)
        self.move_cursor(box_x + 70, input_start_y - 1, "Status", self.theme.header)
        
        while current_line < max_recipients:
            line_y = input_start_y + (current_line * 2)
            
            # Line number
            self.move_cursor(box_x + 2, line_y, f"{len(recipients) + 1:>2}", self.theme.text_dim)
            
            # Input prompt
            self.move_cursor(box_x + 5, line_y, UI.ARROW_RIGHT, self.theme.accent)
            
            # Get input
            user_input = await self.async_input(box_x + 7, line_y, color=self.theme.text)
            
            if user_input.lower() == 'esc':
                return
            
            if not user_input:
                break
            
            # Parse input
            parts = user_input.strip().split()
            
            # Clear line for feedback
            self.clear_line(line_y)
            self.move_cursor(box_x + 2, line_y, f"{len(recipients) + 1:>2}", self.theme.text_dim)
            
            # Validation
            if len(parts) != 2:
                self.move_cursor(box_x + 5, line_y, user_input[:40], self.theme.text_dim)
                self.move_cursor(box_x + 70, line_y, f"{UI.CROSS} Need address & amount", 
                               self.theme.error)
                current_line += 1
                continue
            
            address, amount_str = parts
            
            # Validate address
            if not ADDRESS_REGEX.match(address):
                self.move_cursor(box_x + 5, line_y, f"{address[:40]}...", self.theme.text_dim)
                self.move_cursor(box_x + 70, line_y, f"{UI.CROSS} Invalid address", 
                               self.theme.error)
                current_line += 1
                continue
            
            # Validate amount
            if not AMOUNT_REGEX.match(amount_str) or float(amount_str) <= 0:
                self.move_cursor(box_x + 5, line_y, f"{address[:20]}...{address[-10:]}", 
                               self.theme.text_dim)
                self.move_cursor(box_x + 55, line_y, amount_str, self.theme.text_dim)
                self.move_cursor(box_x + 70, line_y, f"{UI.CROSS} Invalid amount", 
                               self.theme.error)
                current_line += 1
                continue
            
            # Valid entry
            amount = float(amount_str)
            recipients.append((address, amount))
            total_amount += amount
            
            # Display confirmed entry
            self.move_cursor(box_x + 5, line_y, f"{address[:20]}...{address[-10:]}", 
                           self.theme.secondary)
            self.move_cursor(box_x + 55, line_y, f"{amount:>12.6f}", self.theme.success)
            self.move_cursor(box_x + 70, line_y, f"{UI.CHECK} Valid", self.theme.success)
            
            current_line += 1
        
        if not recipients:
            return
        
        # Summary section
        summary_y = box_y + box_height - 8
        self.draw_divider(box_x + 2, summary_y - 1, box_width - 4)
        
        # Display totals
        self.move_cursor(box_x + 2, summary_y, "Summary:", self.theme.header)
        self.move_cursor(box_x + 2, summary_y + 1, 
                        f"Recipients: {len(recipients)}", self.theme.text)
        self.move_cursor(box_x + 20, summary_y + 1, 
                        f"Total Amount: {total_amount:,.6f} OCT", 
                        self.theme.accent + Colors.BOLD)
        
        # Check balance
        self.last_update = 0
        nonce, balance = await self.get_status()
        
        balance_color = self.theme.success if balance and balance >= total_amount else self.theme.error
        self.move_cursor(box_x + 55, summary_y + 1, 
                        f"Balance: {balance:,.6f} OCT", balance_color)
        
        if not balance or balance < total_amount:
            self.move_cursor(box_x + 2, summary_y + 2, 
                           f"{UI.CROSS} Insufficient balance!", 
                           self.theme.error + Colors.BOLD)
            await self.wait_for_key()
            return
        
        # Confirmation
        self.move_cursor(box_x + 2, summary_y + 3, 
                        "Send all transactions? [Y/N]: ", 
                        self.theme.accent + Colors.BOLD)
        
        confirm = await self.async_input(box_x + 32, summary_y + 3, color=self.theme.text)
        
        if confirm.strip().lower() != 'y':
            return
        
        # Sending process with progress bar
        progress_y = summary_y + 5
        self.move_cursor(box_x + 2, progress_y, "Sending transactions:", self.theme.header)
        
        # Progress bar
        progress_bar_y = progress_y + 1
        progress_width = box_width - 20
        
        batch_size = 5
        batches = [recipients[i:i+batch_size] for i in range(0, len(recipients), batch_size)]
        success_count = 0
        fail_count = 0
        
        for batch_idx, batch in enumerate(batches):
            # Update progress
            progress = (batch_idx * batch_size) / len(recipients)
            self.draw_progress_bar(box_x + 2, progress_bar_y, progress_width, progress)
            
            # Process batch
            tasks = []
            for i, (to_address, amount) in enumerate(batch):
                idx = batch_idx * batch_size + i
                tx, _ = self.create_transaction(to_address, amount, nonce + 1 + idx)
                tasks.append(self.send_transaction(tx))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, (result, (to_address, amount)) in enumerate(zip(results, batch)):
                idx = batch_idx * batch_size + i
                
                if isinstance(result, Exception):
                    fail_count += 1
                else:
                    success, tx_hash, _, _ = result
                    if success:
                        success_count += 1
                        # Add to history
                        self.transaction_history.append({
                            'time': datetime.now(),
                            'hash': tx_hash,
                            'amt': amount,
                            'to': to_address,
                            'type': 'out',
                            'ok': True
                        })
                    else:
                        fail_count += 1
                
                # Update progress
                progress = (idx + 1) / len(recipients)
                self.draw_progress_bar(box_x + 2, progress_bar_y, progress_width, progress)
                
                # Status update
                status_text = f"[{idx + 1}/{len(recipients)}] "
                if success_count > 0:
                    status_text += f"{UI.CHECK} {success_count} sent "
                if fail_count > 0:
                    status_text += f"{UI.CROSS} {fail_count} failed"
                
                self.move_cursor(box_x + progress_width + 5, progress_bar_y, 
                               status_text, self.theme.text)
                
                await asyncio.sleep(0.05)  # Small delay for visual effect
        
        # Final result
        self.last_update = 0
        result_color = self.theme.success if fail_count == 0 else self.theme.warning
        result_text = f"Complete: {success_count} successful, {fail_count} failed"
        
        await self.flash_text(box_x + 2, progress_bar_y + 2, result_text, result_color + Colors.BOLD)
        
        await self.wait_for_key()

    async def show_settings(self):
        """Display settings menu"""
        cols, rows = self.get_terminal_size()
        self.fill_background()
        
        box_width = min(60, cols - 4)
        box_height = min(20, rows - 4)
        box_x = (cols - box_width) // 2
        box_y = (rows - box_height) // 2
        
        self.draw_box(box_x, box_y, box_width, box_height, "Settings", "double")
        
        settings = [
            ("1", "Animations", self.show_animations, "Enable/disable UI animations"),
            ("2", "Refresh Rate", f"{self.refresh_rate}s", "Auto-refresh interval"),
            ("3", "Theme", self.theme.name, "Color theme selection"),
            ("0", "Back", "", "Return to main menu")
        ]
        
        setting_y = box_y + 3
        for key, name, value, desc in settings:
            # Key
            self.move_cursor(box_x + 2, setting_y, f"[{key}]", self.theme.accent)
            
            # Name
            self.move_cursor(box_x + 7, setting_y, name, self.theme.text)
            
            # Value
            if isinstance(value, bool):
                value_str = "ON" if value else "OFF"
                value_color = self.theme.success if value else self.theme.error
            else:
                value_str = str(value)
                value_color = self.theme.info
            
            if value_str:
                self.move_cursor(box_x + 25, setting_y, value_str, value_color)
            
            # Description
            self.move_cursor(box_x + 7, setting_y + 1, desc, self.theme.text_dim)
            
            setting_y += 3
        
        # Get choice
        self.move_cursor(box_x + 2, box_y + box_height - 3, "Choice: ", self.theme.accent)
        choice = await self.async_input(box_x + 10, box_y + box_height - 3, color=self.theme.text)
        
        if choice == "1":
            self.show_animations = not self.show_animations
            status = "enabled" if self.show_animations else "disabled"
            self.move_cursor(box_x + 2, box_y + box_height - 2, 
                           f"Animations {status}", self.theme.info)
            await asyncio.sleep(1)
        elif choice == "2":
            self.move_cursor(box_x + 2, box_y + box_height - 2, 
                           "Enter refresh rate (10-300): ", self.theme.accent)
            rate = await self.async_input(box_x + 30, box_y + box_height - 2, color=self.theme.text)
            try:
                rate_int = int(rate)
                if 10 <= rate_int <= 300:
                    self.refresh_rate = rate_int
                    self.move_cursor(box_x + 2, box_y + box_height - 2, 
                                   f"Refresh rate set to {rate_int}s", self.theme.success)
                else:
                    self.move_cursor(box_x + 2, box_y + box_height - 2, 
                                   "Invalid rate (must be 10-300)", self.theme.error)
            except:
                self.move_cursor(box_x + 2, box_y + box_height - 2, 
                               "Invalid input", self.theme.error)
            await asyncio.sleep(1)

    async def export_keys(self):
        """Enhanced export keys interface"""
        cols, rows = self.get_terminal_size()
        self.fill_background()
        
        box_width = min(70, cols - 4)
        box_height = min(18, rows - 4)
        box_x = (cols - box_width) // 2
        box_y = (rows - box_height) // 2
        
        self.draw_box(box_x, box_y, box_width, box_height, "Export Wallet", "double")
        
        # Warning
        warning_y = box_y + 2
        warning = f"{UI.CROSS} WARNING: Keep your private key secure! {UI.CROSS}"
        warning_x = box_x + self.center_text(warning, box_width)
        await self.flash_text(warning_x, warning_y, warning, self.theme.error + Colors.BOLD, times=2)
        
        # Options
        options = [
            ("1", "View Private Key", "Display private key on screen"),
            ("2", "Save to File", "Export wallet to JSON file"),
            ("3", "Copy Address", "Copy address to clipboard"),
            ("0", "Cancel", "Return without exporting")
        ]
        
        option_y = warning_y + 3
        for key, title, desc in options:
            self.move_cursor(box_x + 2, option_y, f"[{key}]", self.theme.accent)
            self.move_cursor(box_x + 7, option_y, title, self.theme.text)
            self.move_cursor(box_x + 7, option_y + 1, desc, self.theme.text_dim)
            option_y += 3
        
        # Choice
        self.move_cursor(box_x + 2, box_y + box_height - 3, "Choice: ", self.theme.accent)
        choice = await self.async_input(box_x + 10, box_y + box_height - 3, color=self.theme.text)
        
        # Clear options area
        for i in range(5, box_height - 3):
            self.clear_line(box_y + i)
        
        result_y = box_y + 6
        
        if choice == "1":
            # Show keys with masking option
            self.draw_box(box_x + 2, result_y, box_width - 4, 8, "Wallet Keys")
            
            self.move_cursor(box_x + 4, result_y + 2, "Private Key:", self.theme.error)
            self.move_cursor(box_x + 4, result_y + 3, self.priv_key[:32], self.theme.error + Colors.BOLD)
            self.move_cursor(box_x + 4, result_y + 4, self.priv_key[32:], self.theme.error + Colors.BOLD)
            
            self.move_cursor(box_x + 4, result_y + 6, "Public Key:", self.theme.success)
            self.move_cursor(box_x + 4, result_y + 7, self.public_key, self.theme.success)
            
        elif choice == "2":
            # Save to file with timestamp
            filename = f"octra_wallet_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            wallet_data = {
                'priv': self.priv_key,
                'addr': self.address,
                'rpc': self.rpc_url,
                'exported': datetime.now().isoformat()
            }
            
            try:
                with open(filename, 'w') as f:
                    json.dump(wallet_data, f, indent=2)
                
                self.move_cursor(box_x + 4, result_y, f"{UI.CHECK} Saved successfully!", 
                               self.theme.success + Colors.BOLD)
                self.move_cursor(box_x + 4, result_y + 1, f"File: {filename}", self.theme.info)
                self.move_cursor(box_x + 4, result_y + 3, 
                               "⚠️  This file contains your private key!", self.theme.error)
                self.move_cursor(box_x + 4, result_y + 4, 
                               "Keep it secure and never share it!", self.theme.error)
            except Exception as e:
                self.move_cursor(box_x + 4, result_y, f"{UI.CROSS} Export failed!", self.theme.error)
                self.move_cursor(box_x + 4, result_y + 1, f"Error: {str(e)}", self.theme.error)
                
        elif choice == "3":
            # Copy address
            try:
                import pyperclip
                pyperclip.copy(self.address)
                self.move_cursor(box_x + 4, result_y, f"{UI.CHECK} Address copied!", 
                               self.theme.success + Colors.BOLD)
                self.move_cursor(box_x + 4, result_y + 1, self.address, self.theme.info)
            except:
                self.move_cursor(box_x + 4, result_y, "Clipboard not available", self.theme.warning)
                self.move_cursor(box_x + 4, result_y + 1, "Address:", self.theme.text)
                self.move_cursor(box_x + 4, result_y + 2, self.address, self.theme.info)
        else:
            return
        
        await self.wait_for_key()

    async def wait_for_key(self):
        """Enhanced wait for key with visual feedback"""
        cols, rows = self.get_terminal_size()
        message = "Press ENTER to continue"
        
        # Animated prompt
        msg_y = rows - 2
        msg_x = self.center_text(message)
        
        if self.show_animations:
            # Pulsing effect
            for _ in range(3):
                self.move_cursor(msg_x, msg_y, message, self.theme.accent + Colors.BOLD)
                await asyncio.sleep(0.3)
                self.move_cursor(msg_x, msg_y, message, self.theme.accent + Colors.DIM)
                await asyncio.sleep(0.3)
        
        self.move_cursor(msg_x, msg_y, message, self.theme.accent + Colors.BOLD)
        
        try:
            await asyncio.get_event_loop().run_in_executor(self.executor, input)
        except:
            self.stop_flag.set()

    async def auto_refresh(self):
        """Background task for auto-refreshing data"""
        while not self.stop_flag.is_set():
            try:
                await asyncio.sleep(self.refresh_rate)
                await self.get_status()
                await self.get_history()
            except:
                pass

    async def run(self):
        """Main application loop with enhanced features"""
        if not self.load_wallet():
            print(f"{Colors.ERROR}Error: Failed to load wallet.json{Colors.RESET}")
            print(f"{Colors.INFO}Make sure wallet.json exists and contains valid data{Colors.RESET}")
            sys.exit(1)
        
        if not self.address:
            print(f"{Colors.ERROR}Error: Wallet not configured{Colors.RESET}")
            sys.exit(1)
        
        try:
            # Start auto-refresh
            self.auto_refresh_task = asyncio.create_task(self.auto_refresh())
            
            # Initial data load with loading screen
            self.fill_background()
            loading_text = "Loading wallet data..."
            loading_x = self.center_text(loading_text)
            loading_y = self.terminal_height // 2
            
            spin_task = asyncio.create_task(
                self.spinner_animation(loading_x - 3, loading_y, loading_text, UI.SPINNER_CIRCLE)
            )
            
            await self.get_status()
            await self.get_history()
            
            spin_task.cancel()
            try:
                await spin_task
            except asyncio.CancelledError:
                pass
            
            # Main loop
            while not self.stop_flag.is_set():
                command = await self.display_main_screen()
                
                if command == '1':
                    await self.send_single_transaction()
                elif command == '2':
                    # Force refresh with animation
                    self.last_update = 0
                    self.last_history_update = 0
                    
                    refresh_y = self.terminal_height // 2
                    refresh_text = "Refreshing..."
                    refresh_x = self.center_text(refresh_text)
                    
                    spin_task = asyncio.create_task(
                        self.spinner_animation(refresh_x - 3, refresh_y, refresh_text)
                    )
                    
                    await self.get_status()
                    await self.get_history()
                    
                    spin_task.cancel()
                    try:
                        await spin_task
                    except asyncio.CancelledError:
                        pass
                        
                elif command == '3':
                    await self.send_multi_transaction()
                elif command == '4':
                    await self.export_keys()
                elif command == '5':
                    # Clear history with confirmation
                    self.transaction_history.clear()
                    self.last_history_update = 0
                elif command == '6':
                    await self.show_settings()
                elif command in ['0', 'q', '']:
                    # Exit animation
                    if self.show_animations:
                        exit_text = "Goodbye!"
                        exit_x = self.center_text(exit_text)
                        exit_y = self.terminal_height // 2
                        self.fill_background()
                        await self.animated_text(exit_x, exit_y, exit_text, 
                                               self.theme.header + Colors.BOLD)
                        await asyncio.sleep(0.5)
                    break
                    
        except Exception as e:
            print(f"{Colors.ERROR}Fatal error: {e}{Colors.RESET}")
        finally:
            # Cleanup
            if self.auto_refresh_task:
                self.auto_refresh_task.cancel()
            
            if self.session and not self.session.closed:
                await self.session.close()
                
            self.executor.shutdown(wait=False)
            self.show_cursor()


async def main():
    """Entry point with error handling"""
    client = WalletClient()
    await client.run()


if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore", category=ResourceWarning)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"{Colors.ERROR}Fatal error: {e}{Colors.RESET}")
    finally:
        # Clean exit
        print(Colors.RESET)
        print('\033[?25h')  # Show cursor
        os.system('cls' if os.name == 'nt' else 'clear')
        os._exit(0)
