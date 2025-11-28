from flask import Flask, render_template

app = Flask(__name__)


@app.route('/')
def upload():
    return render_template('upload.html')


@app.route('/chat')
def chat():
    return render_template('chat.html')



if __name__ == '__main__':
    app.run(debug=True)