from os import environ, path
from pickle import dumps, loads
from io import BytesIO
from json import loads

from flask import Flask, jsonify, stream_with_context, Response, render_template
from requests import get
from redis import Redis

# ENV
site_baseurl = environ.get("SITE_BASE_DOMAIN", "https://e621.net")
redis_host = environ.get("REDIS_HOST", "localhost")
redis_port = environ.get("REDIS_PORT", 6379)

# Random unoptimized stuff
img_exts = ["jpeg", "jpg", "png", "gif"]
vid_exts = ["mp4", "webm"]
accepted_types = ["posts", "pools", "blips", "post_sets", "artists"]

# App
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


def hit_api_and_store(id, type="posts"):
    cache_key = f"{type}_{id}"

    cached_result = get_val(cache_key)
    if cached_result:
        return cached_result

    built_uri = f"{site_baseurl}/{type}/{id}.json"

    post = get(built_uri, headers=api_headers)

    if post.status_code != 200:
        none_res = {"err": "none"}
        cache_val(cache_key, none_res)
        return none_res

    cache_val(cache_key, post.json())
    return post.json()


@app.route("/")
def index_route():
    return (
        f"ok; powered by https://github.com/jae1911/uwu-proxified<br>currently proxying: {site_baseurl}",
        200,
    )


@app.route("/proxy/img/<id>")
def proxy_image_route(id):
    if not id or not id.isnumeric():
        return jsonify({"err": "none"}), 404

    post = hit_api_and_store(id)

    if not post["post"]["file"]["url"]:
        return jsonify({"err": "none"}), 404

    content = get(post["post"]["file"]["url"], headers=api_headers, stream=True)

    return Response(
        stream_with_context(content.iter_content(chunk_size=1024)),
        content_type=content.headers["content-type"],
    )


@app.route("/<type>/<id>")  # E6 Parity
def proxy_post_route(type, id):
    if not id or not type in accepted_types:
        return render_template("404.html")
    elif not id.isnumeric():
        # For E6-like API URIs
        if ".json" in id and id.replace(".json", "").isnumeric():
            res = hit_api_and_store(id.replace(".json", ""), type)
            return jsonify(res), 200

        return render_template("404.html")

    if type != "posts":
        return "Display not implemented yet", 501

    post_data = hit_api_and_store(id, type)["post"]

    post_content_ext = post_data["file"]["ext"]

    kind = "image"
    if post_content_ext in vid_exts:
        kind = "video"

    return render_template(
        "post.html", id=id, description=post_data["description"], kind=kind
    )
