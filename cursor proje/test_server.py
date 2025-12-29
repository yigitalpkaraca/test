from flask import Flask, render_template_string

app = Flask(__name__)

@app.route('/')
def test():
    return '''
    <h1>✅ Sunucu Çalışıyor!</h1>
    <p>Eğer bu mesajı görüyorsan, Flask sunucusu başarıyla çalışıyor.</p>
    <p><a href="/test">Test Sayfası</a></p>
    '''

@app.route('/test')
def test_page():
    return '<h2>Test sayfası çalışıyor!</h2>'

if __name__ == '__main__':
    print("=" * 50)
    print("TEST SUNUCUSU BAŞLATILIYOR...")
    print("=" * 50)
    print("Tarayıcıda şu adresi aç: http://localhost:5000")
    print("Sunucuyu durdurmak için: CTRL+C")
    print("=" * 50)
    app.run(debug=True, port=5000)

