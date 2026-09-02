from web import create_app

app = create_app()

from flask import jsonify
@app.route("/routes")
def site_map():
    links = []
    # for rule in app.url_map.iter_rules():
    for rule in app.url_map._rules:
        # Filter out rules we can't navigate to in a browser
        # and rules that require parameters
        links.append({'url': rule.rule, 'view': rule.endpoint})
    return jsonify(links), 200

if __name__ == '__main__':
    # app.run(debug=True, port=8000, host='localhost')
    app.run(host='0.0.0.0', port=5000, debug=True)
    # app.run("localhost", 8000, True, True)