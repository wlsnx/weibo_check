#!/usr/bin/env python
# encoding: utf-8


from weibo_login import WeiboLogin
from flask import request, Flask, render_template, redirect, url_for, make_response


import re
import json


import redis


db = redis.Redis()


uid_pat = re.compile(r"CONFIG\[[\"|\']uid[\"|\']\]=[\"|\'](\d+)[\"|\'];")
oid_pat = re.compile(r"CONFIG\[[\"|\']oid[\"|\']\]=[\"|\'](\d+)[\"|\'];")
user_pat = re.compile(ur"个性域名.*?>(\w+?)<")

def check_user(username):
    info = wb.get("http://weibo.com/{}".format(username)).content
    if "page_error" not in info:
        matched = oid_pat.search(info)
        if matched:
            return matched.group(1)

def check_uid(uid):
    info = wb.get("http://weibo.com/{}".format(uid)).content
    if "page_error" not in info:
        matched = user_pat.search(info.decode("utf-8"))
        if matched:
            return matched.group(1)
        else:
            return True


app = Flask(__name__)
app.config.from_pyfile("config.py")


wb = WeiboLogin(app.config["USERNAME"],
                app.config["PASSWORD"],
                app.config["COOKIE_FILE"])
wb.load_cookies()


@app.route("/weibo", methods=["POST", "GET"])
def weibo():
    wb.test_log_status()
    args = request.form or request.args
    user = args.get("user", "")
    uid = args.get("uid", "")
    action = args.get("action", "start")
    door = args.get("door", "")
    if request.method == "GET":
        base64_image = ""
        if not wb.logged:
            pin_image = wb.get_login_data()
            if pin_image:
                import base64
                base64_image = "data:image/png;base64,{}".format(base64.encodestring(pin_image))
        return render_template("weibo.html",
                               user=user,
                               uid=uid,
                               action=action,
                               uid_list=db.sscan(app.config["WEIBO_UID_KEY"], 0)[1],
                               image=base64_image)
    if not wb.logged and door:
        wb.login(door)
    if not wb.logged:
    #if True:
        pin_image = wb.get_login_data()
        if pin_image:
            import base64
            base64_image = "data:image/png;base64,{}".format(base64.encodestring(pin_image))
            return render_template("weibo.html",
                                   user=user,
                                   uid=uid,
                                   action=action,
                                   uid_list=db.sscan(app.config["WEIBO_UID_KEY"], 0)[1],
                                   image=base64_image)
        else:
            if not wb.login():
                return redirect(url_for("weibo"))

    user = user.split(",") if user else []
    uid = uid.split(",") if uid else []

    valid_user = []
    invalid_user = []
    valid_uid = []
    invalid_uid = []
    tmp_user = []
    tmp_uid = []

    for u in user:
        user_id = check_user(u)
        if user_id is True and user_id not in tmp_user:
            tmp_user.append(u)
        elif user_id and u not in valid_user:
                valid_user.append(u)
                valid_uid.append(user_id)
        elif u not in invalid_user:
            invalid_user.append(u)

    for i in uid:
        ym = check_uid(i)
        if ym is True and i not in tmp_uid:
            tmp_uid.append(i)
        elif ym and ym not in valid_user:
            valid_user.append(ym)
            valid_uid.append(i)
        elif i not in valid_uid:
            invalid_uid.append(i)

    valid_user.extend(tmp_user)
    valid_uid.extend(tmp_uid)

    r = wb.post("http://localhost:6800/schedule.json",
                data={"user": ",".join(valid_user),
                      "uid": ",".join(valid_uid),
                      "project": "weibo",
                      "spider": "wp",
                      "action": action,
                      }).content

    resp = json.loads(r)

    resp["user"] = valid_user
    resp["uid"] = valid_uid
    resp["invalid_user"] = invalid_user
    resp["invalid_uid"] = invalid_uid
    resp["action"] = action

    for key in resp.keys():
        if not resp[key]:
            resp.pop(key)

    resp = make_response(json.dumps(resp))
    resp.headers["Content-Type"] = "application/json"
    return resp


if __name__ == "__main__":
    app.run()

