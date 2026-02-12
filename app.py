from flask import Flask, render_template, jsonify, request
from fund_api import compare_valuation

app = Flask(__name__)

@app.route('/')
def index():
    """渲染主页"""
    return render_template('index.html')

@app.route('/test')
def test():
    """测试路由"""
    return '<h1>Flask 正常工作！</h1><p>如果你能看到这个，说明 Flask 正常</p>'

@app.route('/api/query', methods=['POST'])
def query_fund():
    """API 接口：查询基金数据"""
    data = request.get_json()
    fund_code = data.get('fund_code', '').strip()
    
    if not fund_code:
        return jsonify({'error': '请输入基金代码'}), 400
    
    result = compare_valuation(fund_code)
    return jsonify(result)

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)