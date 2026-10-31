from flask import jsonify


def error(msg, code=400):
    return jsonify({"error": msg}), code
