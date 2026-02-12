import requests
import re
import json

ffff = '001120'  # 替换为你想查询的基金代码
def get_fund_data(fund_code):
    url = f"http://fundgz.1234567.com.cn/js/{fund_code}.js"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        res = requests.get(url, headers=headers, timeout=5)
        matches = re.findall(r'jsonpgz\((.*)\)', res.text)
        
        if not matches:
            print(f"⚠️ 未找到基金 {fund_code} 的数据")
            return None
        
        # 正确位置：在 return 之前处理
        data = json.loads(matches[0])
        print(f"基金名称: {data['name']}")
        print(f"当前估值涨幅: {data['gszzl']}%")
        return data
        
    except Exception as e:
        print(f"❌ 获取基金 {fund_code} 发生错误: {e}")
        return None
    
# 测试一下
get_fund_data(ffff)

import requests
from bs4 import BeautifulSoup
import re

def get_top_10_holdings(fund_code):
    # 接口地址：获取前10大重仓股数据
    url = f"https://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code={fund_code}&topline=10"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    res = requests.get(url, headers=headers)
    
    # 提取 API 返回的 HTML 内容部分
    match = re.search(r'content:"(.*)"', res.text)
    if not match: return []
    html_content = match.group(1)
    
    soup = BeautifulSoup(html_content, 'html.parser')
    rows = soup.find_all('tr')[1:]  # 跳过表头
    
    holdings = []
    # 只需要前 10 行有效数据
    count = 0
    for row in rows:
        if count >= 10: break  # 拿到 10 个就停，防止抓到历史数据或市值数据
        
        cols = row.find_all('td')
        if len(cols) > 6:
            # 提取百分比文本
            raw_pct = cols[6].text.strip()
            # 判定：如果这一行没有百分号，说明可能是市值或者其他数据，跳过
            if '%' not in raw_pct:
                continue
                
            stock_code = cols[1].text.strip()
            stock_name = cols[2].text.strip()
            ratio = float(raw_pct.replace('%', '').replace(',', ''))
            
            holdings.append({'code': stock_code, 'name': stock_name, 'ratio': ratio})
            count += 1
            
    return holdings

# 执行获取并测试
print(get_top_10_holdings(ffff))
def compare_valuation(fund_code):
    # 1. 获取天天基金的官方估值 (gszzl)
    official_data = get_fund_data(fund_code)
    
    # 【核心防御代码加在这里】
    if official_data is None:
        print(f"🛑 任务终止：无法获取基金 {fund_code} 的官方数据。")
        return None 
    # -----------------------

    official_growth = float(official_data['gszzl'])
    
    # 2. 获取重仓股名单及比例
    holdings = get_top_10_holdings(fund_code)
    
    # 【第二次防御：如果没有持仓数据也要拦截】
    if not holdings:
        print(f"🛑 任务终止：无法获取基金 {fund_code} 的重仓股明细。")
        return None
    # -----------------------

    # 3. 获取这 10 只股票的实时涨幅 (腾讯接口)
    stock_queries = []
    for h in holdings:
        prefix = 'sh' if h['code'].startswith('6') else 'sz'
        stock_queries.append(f"s_{prefix}{h['code']}")
    
    stock_url = f"https://qt.gtimg.cn/q={','.join(stock_queries)}"
    stock_res = requests.get(stock_url)
    
    # 4. 计算理论加权涨幅
    theory_growth = 0
    lines = stock_res.text.strip().split(';')
    
    # 关键：由于腾讯返回的行数可能多于实际解析出的 holdings 数量，加个保护
    valid_lines = [l for l in lines if l.strip()]
    
    for i, line in enumerate(valid_lines):
        if i >= len(holdings): break # 防止索引越界
        parts = line.split('~')
        try:
            stock_growth = float(parts[5]) 
            theory_growth += stock_growth * (holdings[i]['ratio'] / 100)
        except (IndexError, ValueError):
            continue

    # 5. 输出对比结果
    deviation = official_growth - theory_growth
    print(f"\n--- {official_data['name']} ({fund_code}) 对比分析 ---")
    print(f"官方估值涨幅: {official_growth:.3f}%")
    print(f"重仓推算涨幅: {theory_growth:.3f}%")
    print(f"偏差值 (Alpha): {deviation:.3f}%")
    
    return {
        'date': official_data['gztime'],
        'official': official_growth,
        'theory': theory_growth,
        'deviation': deviation
    }

# 测试
compare_valuation(ffff)