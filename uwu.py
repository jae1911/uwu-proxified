from os import environ
from pickle import dumps, loads
from io import BytesIO
from json import loads

from flask import Flask, jsonify, send_file
from requests import get
from redis import Redis

# ENV
site_baseurl = environ.get("SITE_BASE_DOMAIN", "https://e621.net")
redis_host = environ.get("REDIS_HOST", "localhost")
redis_port = environ.get("REDIS_PORT", 6379)

app = Flask(__name__)
api_headers = {"User-Agent": "UwUProxy/1.0 (by jae1911 on GitHub)"}
redis = Redis(host=redis_host, port=redis_port)


def cache_val(key, val, expiration_secs=86400):
    if not key or not val:
        return None

    try:
        s = dumps(val)
        redis.set(key, s, expiration_secs or None)
    except:
        return None


def get_val(key, default=None):
    if not key:
        return None

    try:
        v = redis.get(key)
        if not v:
            return default

        return loads(v) or default
    except:
        return default


def hit_api_and_store(id):
    cache_key = f"post_{id}"

    cached_result = get_val(cache_key)
    if cached_result:
        return cached_result

    built_uri = f"{site_baseurl}/posts/{id}.json"

    post = get(built_uri, headers=api_headers)

    if post.status_code != 200:
        none_res = {"err": "none"}
        cache_val(cache_key, none_res)
        return none_res

    cache_val(cache_key, post.json())
    return post.json()


@app.route("/")
def index_route():
    return "ok", 200


@app.route("/proxy/api/post/<id>")
def proxy_api_route(id):
    if not id or not id.isnumeric():
        return jsonify({"err": "none"}), 404

    res = hit_api_and_store(id)

    return jsonify(res), 200


@app.route("/proxy/img/<id>")
def proxy_image_route(id):
    if not id or not id.isnumeric():
        return jsonify({"err": "none"}), 404

    post = hit_api_and_store(id)

    if not post["post"]["file"]["url"]:
        return jsonify({"err": "none"}), 404

    img = get(post["post"]["file"]["url"], headers=api_headers)
    buffer_image = BytesIO(img.content)
    buffer_image.seek(0)

    return send_file(buffer_image, mimetype="image/png")
