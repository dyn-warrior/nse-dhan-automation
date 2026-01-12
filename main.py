import time
import logging
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# --- Configuration ---
REFRESH_INTERVAL = 300  # seconds (5 minutes)
TOTAL_WINDOWS = 20
GRID_ROWS = 4
GRID_COLS = 5

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class NSEFetcher:
    def __init__(self):
        self.url = "https://www.nseindia.com/market-data/volume-gainers-spurts"
        self.options = Options()
        # self.options.add_argument("--headless")  # DISABLED to avoid detection
        self.options.add_argument("--disable-blink-features=AutomationControlled")
        self.options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.options.add_experimental_option('useAutomationExtension', False)
        self.options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        self.driver = None

    def start(self):
        logging.info("Starting NSE Fetcher (Headless Browser)...")
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=self.options)

    def stop(self):
        if self.driver:
            self.driver.quit()

    def get_top_symbols(self, limit=20):
        try:
            self.driver.get(self.url)
            time.sleep(3) # Wait for initial load
            
            # Direct URL used, no need to click tabs.
            
            # Now scrape table

            # Now scrape table
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            table = None
            
            # Find table with "Symbol" or "SYMBOL"
            for tbl in soup.find_all("table"):
                # Case insensitive check for Symbol
                if tbl.find("th", string=lambda x: x and "SYMBOL" in x.upper()):
                    table = tbl
                    break
            
            if not table:
                return self.get_fallback_symbols()
            
            symbols = []
            rows = table.find_all("tr")[1:] 
            for row in rows:
                cols = row.find_all("td")
                if cols and len(cols) > 0:
                    symbol = cols[0].get_text(strip=True).split()[0].strip()
                    # Filter out non-equity if needed. Volume Spurts usually are equities.
                    symbols.append(symbol)
                    if len(symbols) >= limit:
                        break
                        
            if not symbols: return self.get_fallback_symbols()
            return symbols

        except Exception as e:
            logging.error(f"Error fetching NSE: {e}")
            return self.get_fallback_symbols()

    def get_fallback_symbols(self):
        return ["RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "SBIN", "BHARTIARTL", "ITC", "KOTAKBANK", "LTIM", "LT", "AXISBANK", "HCLTECH", "ADANIENT", "MARUTI", "ASIANPAINT", "SUNPHARMA", "TITAN", "ULTRACEMCO", "TATASTEEL"]

class DhanGrid:
    def __init__(self):
        self.options = Options()
        self.options.add_argument("--start-maximized")
        # Enable Browser Logging
        self.options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
        self.driver = None

    def start(self):
        logging.info("Starting Dhan Grid Browser...")
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=self.options)
        self.driver.get("https://tv.dhan.co/")
        logging.info("Please log in to Dhan in the opened window.")

    def update_charts(self, symbols):
        logging.info(f"Updating dashboard with {len(symbols)} symbols...")
        logging.info(f"Fetched Symbols: {symbols}")
        
        # 1. GENERATE GRID (HTML/CSS ONLY)
        
        style = """
            body { margin: 0; overflow: hidden; background: #000; font-family: sans-serif; }
            .tab-bar { position: absolute; top: 0; left: 0; width: 100%; height: 35px; background: #222; display: flex; z-index: 100000; border-bottom: 2px solid #444; }
            .tab-btn { flex: 1; border: none; background: #333; color: #fff; cursor: pointer; border-right: 1px solid #444; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; }
            .tab-btn:hover { background: #444; }
            .tab-btn.active { background: #007bff; font-weight: bold; color: white; }
            .grid-page { display: none; width: 100vw; height: calc(100vh - 35px); margin-top: 35px; grid-template-columns: repeat(3, 1fr); grid-template-rows: repeat(2, 1fr); gap: 2px; background: #111; }
            .grid-page.active-page { display: grid; }
            iframe { width: 100%; height: 100%; border: none; background: #000; }
        """
        
        tab_script = """
        window.showTab = function(index) {
            document.querySelectorAll('.grid-page').forEach(el => el.classList.remove('active-page'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            document.getElementById('tab-' + index).classList.add('active-page');
            document.getElementById('btn-' + index).classList.add('active');
        };
        """
        
        html_content = '<div id="custom-ui" style="position:absolute; top:0; left:0; width:100%; height:100%; z-index:99999; background:#000;">'
        html_content += f'<style>{style}</style>'
        html_content += f'<script>{tab_script}</script>'
        
        # Tabs
        html_content += '<div class="tab-bar">'
        for i in range(4):
            active = "active" if i == 0 else ""
            html_content += f'<button id="btn-{i}" class="tab-btn {active}" onclick="showTab({i})">PAGE {i+1}</button>'
        html_content += '</div>'
        
        # Pages and Iframes
        chunks = [symbols[i:i + 6] for i in range(0, len(symbols), 6)]
        while len(chunks) < 4: chunks.append([])
        
        mapping_data = [] # Store (iframe_id, symbol, page_index) to process later
        
        for i in range(4):
            active_page = "active-page" if i == 0 else ""
            chunk = chunks[i]
            html_content += f'<div id="tab-{i}" class="grid-page {active_page}">'
            
            for slot_idx in range(6):
                if slot_idx < len(chunk):
                    s = chunk[slot_idx]
                    fid = f"chart-frame-{i}-{slot_idx}"
                    url = "https://tv.dhan.co/" # Clean URL
                    html_content += f'<iframe id="{fid}" src="{url}" allow="autoplay; encrypted-media"></iframe>'
                    mapping_data.append((fid, s, i)) 
                else:
                    html_content += '<div style="background:#111;"></div>' 
            html_content += '</div>'
        html_content += '</div>'
        
        # Inject HTML
        self.driver.execute_script(f"document.body.innerHTML = `{html_content}`;")
        self.driver.execute_script(f"var s = document.createElement('script'); s.text = `{tab_script}`; document.body.appendChild(s);")
        
        # 2. PYTHON-DRIVEN INTERACTION
        logging.info("Waiting 10s for charts to init...")
        time.sleep(10)
        
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        # Sort Data
        charts_by_page = {0: [], 1: [], 2: [], 3: []}
        for fid, symbol, page_idx in mapping_data:
            charts_by_page[page_idx].append((fid, symbol))
            
        # Interact
        for page_idx in range(4):
            charts = charts_by_page[page_idx]
            if not charts: continue
            
            logging.info(f"=== Processing Page {page_idx + 1} ===")
            self.driver.switch_to.default_content()
            
            # Switch Tab
            try:
                # Safety: ESC to close any open dialogs from previous tab interaction
                ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                
                btn = self.driver.find_element(By.ID, f"btn-{page_idx}")
                self.driver.execute_script("arguments[0].click();", btn)
                # Wait for display:block to take effect
                time.sleep(1.5)
            except Exception as e:
                logging.error(f"Tab switch error: {e}")
                continue
                
            for fid, symbol in charts:
                try:
                    self.driver.switch_to.default_content()
                    
                    # Wait for Frame
                    try:
                        iframe = WebDriverWait(self.driver, 3).until(EC.visibility_of_element_located((By.ID, fid)))
                        self.driver.switch_to.frame(iframe)
                    except:
                        logging.warning(f"Skipping invisible frame {fid}")
                        continue
                        
                    # STRATEGY: Center Click + Type (Canvas Interaction)
                    # This works by focusing the chart canvas directly
                    try:
                        body = self.driver.find_element(By.TAG_NAME, "body")
                        actions = ActionChains(self.driver)
                        
                        # 1. Click Center to Focus (Coordinates relative to element center if no offset? No, element top-left)
                        # move_to_element moves to center. click() clicks current pos.
                        # So move_to_element(body).click() clicks dead center of chart. Safe.
                        actions.move_to_element(body).click().perform()
                        # Short pause for focus
                        time.sleep(0.2)
                        
                        # 2. Type Symbol + Enter
                        actions.send_keys(symbol)
                        time.sleep(0.8) # Wait for TV search UI to appear/filter
                        actions.send_keys(Keys.ENTER)
                        actions.perform()
                        
                        logging.info(f"Injected {symbol} (Center-Click Strategy)")
                        
                        # Short pause to prevent overlapped inputs
                        time.sleep(0.3)
                        
                    except Exception as e:
                        logging.error(f"Interaction failed for {fid}: {e}")
                        
                except Exception as e:
                    logging.error(f"Frame error {fid}: {e}")
                    
        self.driver.switch_to.default_content()
        logging.info("Update Complete.")

    def check_console(self):
        if not self.driver: return
        try:
            logs = self.driver.get_log('browser')
            for entry in logs:
                # Filter for our own logs or errors
                msg = entry['message']
                if "Injecting" in msg or "Frame loaded" in msg or "Search button" in msg or "SEVERE" in str(entry['level']):
                    logging.info(f"JS CONSOLE: {msg}")
        except Exception:
            pass

    def close(self):
        if self.driver:
            self.driver.quit()

def main():
    fetcher = NSEFetcher()
    grid = DhanGrid()
    
    try:
        fetcher.start()
        grid.start()
        
        print("")
        print(">>> ------------------------------------------------ <<<")
        print(">>> PLEASE LOG IN TO DHAN IN THE NEW CHROME WINDOW <<<")
        print(">>> ------------------------------------------------ <<<")
        print("")
        input("Press Enter here AFTER you are fully logged in and see the chart...")
        
        while True:
            # Fetch 30 to ensure we have enough after skipping
            symbols = fetcher.get_top_symbols(limit=30)
            
            if symbols:
                # User Request: Skip top symbol, show next 24 (4 tabs * 6 charts)
                if len(symbols) > 1:
                    symbols = symbols[1:25]
                    
                grid.update_charts(symbols)
            else:
                logging.warning("No symbols fetched.")
                
            logging.info(f"Sleeping for {REFRESH_INTERVAL} seconds...")
            # Sleep in chunks to check logs
            for _ in range(30): # Check logs for first 30 seconds
                time.sleep(1)
                grid.check_console()
            
            time.sleep(REFRESH_INTERVAL - 30)
            
    except KeyboardInterrupt:
        logging.info("Stopping...")
    finally:
        fetcher.stop()
        grid.close()

if __name__ == "__main__":
    main()
