import json, os, random, sys, time, zipfile
import requests

TOKEN = os.environ.get("RUBIKA_TOKEN", "")
CHAT = os.environ.get("RUBIKA_CHAT_ID", "")
BASE = "https://botapi.rubika.ir/v3/%s/" % TOKEN
FA = "۰۱۲۳۴۵۶۷۸۹"


def api(method, data=None):
    r = requests.post(BASE + method, json=data or {}, timeout=60)
    try:
        j = r.json()
    except Exception:
        raise SystemExit("پاسخ نامعتبر از روبیکا (%s): %s" % (r.status_code, r.text[:300]))
    if j.get("status") != "OK":
        raise SystemExit("خطای روبیکا در %s: %s" % (method, json.dumps(j, ensure_ascii=False)[:400]))
    return j.get("data", {})


def fa(s):
    return "".join(FA[int(c)] if c.isdigit() else c for c in str(s))


def money(v):
    return fa("{:,}".format(int(v)))


def load_cfg():
    with open("config.json", encoding="utf-8") as f:
        return json.load(f)


def make_text(p, cfg):
    cat = (p.get("cat") or "").strip()
    phrases = cfg["phrases"].get(cat) or cfg["phrases"]["default"]
    lines = [p["name"].strip(), "", random.choice(phrases), "",
             "💰 قیمت: %s %s" % (money(p["sell"]), cfg["unit"]),
             "✅ موجود در " + cfg["shop"]]
    if cfg.get("order_line"):
        lines.append(cfg["order_line"])
    tags = ["#" + cfg["shop"].replace(" ", "_")]
    if cat:
        tags.append("#" + cat.replace(" ", "_"))
    lines += ["", " ".join(tags)]
    return "\n".join(lines)


def upload_image(data, name):
    d = api("requestSendFile", {"type": "Image"})
    url = d["upload_url"]
    r = requests.post(url, files={"file": (name, data, "image/jpeg")}, timeout=120)
    j = r.json()
    fid = j.get("data", {}).get("file_id") or j.get("file_id")
    if not fid:
        raise SystemExit("آپلود عکس ناموفق: %s" % r.text[:300])
    return fid


def cmd_test():
    me = api("getMe")
    print("ربات:", json.dumps(me, ensure_ascii=False)[:300])
    if CHAT:
        api("sendMessage", {"chat_id": CHAT, "text": "✅ تست ربات آسیا"})
        print("پیام تست به کانال فرستاده شد")
    else:
        print("RUBIKA_CHAT_ID خالی است. در کانال یک پیام بنویسید و دوباره اجرا کنید.")
        up = api("getUpdates", {"limit": 20})
        print(json.dumps(up, ensure_ascii=False)[:1500])


def cmd_post(force):
    cfg = load_cfg()
    z = zipfile.ZipFile("catalog.zip")
    items = json.loads(z.read("catalog.json").decode("utf-8"))
    st = {"posted": []}
    if os.path.exists("state.json"):
        st = json.load(open("state.json", encoding="utf-8"))
    ids = {p["id"] for p in items}
    now = time.time()
    if not force:
        hour = time.gmtime(now + 12600).tm_hour
        if not (9 <= hour < 22):
            print("خارج از ساعت پست")
            return
        if now - st.get("last", 0) < 45 * 60:
            print("هنوز زود است، پست قبلی تازه رفته")
            return
    posted = [i for i in st["posted"] if i in ids]
    todo = [p for p in items if p["id"] not in posted and p.get("photo")]
    if not todo:
        posted = []
        todo = [p for p in items if p.get("photo")]
    if not todo:
        raise SystemExit("کالایی با عکس در کاتالوگ نیست")
    p = random.choice(todo)
    text = make_text(p, cfg)
    data = z.read("photos/" + p["photo"])
    fid = upload_image(data, p["photo"])
    api("sendFile", {"chat_id": CHAT, "file_id": fid, "text": text})
    posted.append(p["id"])
    json.dump({"posted": posted, "last": now}, open("state.json", "w", encoding="utf-8"), ensure_ascii=False)
    print("ارسال شد:", p["name"])


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("RUBIKA_TOKEN تنظیم نشده")
    mode = sys.argv[1] if len(sys.argv) > 1 else "post"
    if mode == "test":
        cmd_test()
    else:
        if not CHAT:
            raise SystemExit("RUBIKA_CHAT_ID تنظیم نشده")
        cmd_post(mode == "force")
