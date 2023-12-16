from flask import Flask
import competenssator as cs

app = Flask(__name__)


@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World MOtherfucker!  <a href="competenssator">ici</a>'

@app.route('/competenssator')
def foobar():
    file_path = '5N6.yaml'
    results = cs.yaml_to_svgs(file_path)
    return results[0]


if __name__ == '__main__':
    app.run(debug=True)
