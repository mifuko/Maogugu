import requests
import re
import json
from bs4 import BeautifulSoup

def get_fund_data(fund_code):
    """获取基金官方估值数据"""
    url = f"http://fundgz.1234567.com.cn/js/{fund_code}.js"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        matches = re.findall(r'jsonpgz\((.*)\)', res.text)
        if not matches:
            return None
        return json.loads(matches[0])
    except Exception:
        return None

def get_fund_history(fund_code):
    """
    备选方案：通过天天基金网页版接口获取历史净值
    """
    # 这个接口返回最近一个月的净值，通常用于绘制短期K线
    url = f"https://fund.eastmoney.com/f10/F10DataApi.aspx?type=lsjz&code={fund_code}&per=30&page=1"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        res = requests.get(url, headers=headers, timeout=5)
        # 网页返回的是一段 JS 赋值语句，包含 HTML 表格
        html_match = re.search(r'content:"(.*)"', res.text)
        if not html_match:
            return []
            
        html_content = html_match.group(1)
        soup = BeautifulSoup(html_content, 'html.parser')
        rows = soup.find_all('tr')[1:] # 跳过表头
        
        history = []
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 2:
                date = cols[0].text.strip()
                value = cols[1].text.strip() # 单位净值
                try:
                    history.append({
                        "date": date,
                        "value": float(value)
                    })
                except ValueError:
                    continue
        
        # 网页端是倒序的（最新在最前），绘图需要正序
        return history[::-1]
    except Exception as e:
        print(f"网页端历史数据抓取失败: {e}")
        return []

def get_top_10_holdings(fund_code):
    """获取基金前10大重仓股"""
    url = f"https://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code={fund_code}&topline=10"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        match = re.search(r'content:"(.*)"', res.text)
        if not match: return []
        
        html_content = match.group(1)
        soup = BeautifulSoup(html_content, 'html.parser')
        rows = soup.find_all('tr')[1:]
        
        holdings = []
        count = 0
        for row in rows:
            if count >= 10: break
            cols = row.find_all('td')
            if len(cols) > 6:
                raw_pct = cols[6].text.strip()
                if '%' not in raw_pct: continue
                holdings.append({
                    'code': cols[1].text.strip(),
                    'name': cols[2].text.strip(),
                    'ratio': float(raw_pct.replace('%', '').replace(',', ''))
                })
                count += 1
        return holdings
    except Exception:
        return []

def compare_valuation(fund_code):
    """综合查询：包含实时估值、历史走势和重仓对比"""
    official_data = get_fund_data(fund_code)
    if not official_data:
        return {'error': '无法获取基金数据'}

    holdings = get_top_10_holdings(fund_code)
    history_data = get_fund_history(fund_code)
    
    # 获取重仓股实时涨幅
    stock_queries = [f"{'sh' if h['code'].startswith('6') else 'sz'}{h['code']}" for h in holdings]
    stock_url = f"https://qt.gtimg.cn/q=s_{',s_'.join(stock_queries)}"
    
    theory_growth = 0
    try:
        stock_res = requests.get(stock_url, timeout=5)
        lines = [l for l in stock_res.text.split(';') if l.strip()]
        for i, line in enumerate(lines):
            if i < len(holdings):
                parts = line.split('~')
                theory_growth += float(parts[5]) * (holdings[i]['ratio'] / 100)
    except:
        pass

    official_growth = float(official_data['gszzl'])
    
    return {
        'success': True,
        'fund_name': official_data['name'],
        'fund_code': fund_code,
        'update_time': official_data['gztime'],
        'official_growth': round(official_growth, 3),
        'theory_growth': round(theory_growth, 3),
        'deviation': round(official_growth - theory_growth, 3),
        'history': history_data, # 传给前端完整数组
        'holdings': holdings
    }