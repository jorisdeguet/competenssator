import yaml
from flask import Flask, request, render_template
import competenssator as cs

app = Flask(__name__)


@app.route('/')
def hello_world():  # put application's code
    data = cs.yaml_from_filepath('5N6.yaml')
    user = "Joris"
    return render_template("test.html", name=user, yaml= yaml.dump(data))

@app.route('/competenssator')
def foobar():
    yaml = request.args.get('yaml')
    if yaml == None or yaml == "":
        file_path = '5N6.yaml'
        results = cs.file_to_svgs(file_path)
        return results[0]
    else:
        print("yaml from request " + yaml)
        results = cs.string_to_svgs(yaml)
        return results[0]



if __name__ == '__main__':
    app.run(debug=True)
