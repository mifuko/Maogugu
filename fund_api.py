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

def get_top_10_holdings(fund_code):
    """获取基金前10大重仓股"""
    url = f"https://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code={fund_code}&topline=10"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        res = requests.get(url, headers=headers, timeout=5)
        match = re.search(r'content:"(.*)"', res.text)
        if not match:
            return []
        
        html_content = match.group(1)
        soup = BeautifulSoup(html_content, 'html.parser')
        rows = soup.find_all('tr')[1:]
        
        holdings = []
        count = 0
        for row in rows:
            if count >= 10:
                break
            
            cols = row.find_all('td')
            if len(cols) > 6:
                raw_pct = cols[6].text.strip()
                if '%' not in raw_pct:
                    continue
                
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
    """对比官方估值与重仓推算涨幅"""
    official_data = get_fund_data(fund_code)
    
    if official_data is None:
        return {'error': '无法获取基金数据，请检查代码是否正确'}
    
    holdings = get_top_10_holdings(fund_code)
    
    if not holdings:
        return {'error': '无法获取重仓股数据'}
    
    # 获取股票实时涨幅
    stock_queries = []
    for h in holdings:
        prefix = 'sh' if h['code'].startswith('6') else 'sz'
        stock_queries.append(f"s_{prefix}{h['code']}")
    
    stock_url = f"https://qt.gtimg.cn/q={','.join(stock_queries)}"
    stock_res = requests.get(stock_url, timeout=5)
    
    # 计算加权涨幅
    theory_growth = 0
    lines = stock_res.text.strip().split(';')
    valid_lines = [l for l in lines if l.strip()]
    
    for i, line in enumerate(valid_lines):
        if i >= len(holdings):
            break
        parts = line.split('~')
        try:
            stock_growth = float(parts[5])
            theory_growth += stock_growth * (holdings[i]['ratio'] / 100)
        except (IndexError, ValueError):
            continue
    
    official_growth = float(official_data['gszzl'])
    deviation = official_growth - theory_growth
    
    return {
        'success': True,
        'fund_name': official_data['name'],
        'fund_code': fund_code,
        'update_time': official_data['gztime'],
        'official_growth': round(official_growth, 3),
        'theory_growth': round(theory_growth, 3),
        'deviation': round(deviation, 3),
        'holdings': holdings[:10]  # 返回前10大重仓股
    }