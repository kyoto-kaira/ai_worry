"""Kaira君を探せ（YOLO をヒントにする版）のモックアプリ。問題を「作る」画面と「解く」画面がある

uv run python app/server.py   # リポジトリ直下の .env も読む（GEMINI_API_KEY は背景・偽物を Gemini で作るときに使う）
"""
import argparse
import json
import re
import threading
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import create
from config import (
    ANSWERS_PATH, APP_DIR, DETECTIONS_PATH, DEFAULT_WIDTH, FOOL_TOP, LEVELS, PLACE_GAP, PORT, QUESTION_IMAGE_DIR,
    THEME_EXAMPLE, USER_DETECTIONS_PATH, USER_QUESTION_DIR, WIDTH_RANGE,
)
from detect import Detector, load_detections, save_detections, seed_of
from gen_img.env import load_env

PAGES = {"/": "solve.html", "/create": "create.html"}


class Game:
    def __init__(self):
        if not ANSWERS_PATH.exists():
            raise SystemExit("用意した問題がない。先に uv run python app/build.py を実行する")
        # 問題の番号：用意した問題は "1"〜、お客様が作った問題は "u1"〜
        self.answers = {str(k): v for k, v in json.loads(ANSWERS_PATH.read_text(encoding="utf-8")).items()}
        self.answers.update(create.saved_questions())
        self.detector = Detector()
        self.lock = threading.Lock()
        # YOLO の検出結果は、用意した問題は build.py で、作った問題は登録したときに保存してあるので読むだけ。
        # モデルや推論の設定が変わって古くなっていたら、ここで検出し直して保存し直す
        builtin = [q for q in self.answers if not q.startswith("u")]
        made = [q for q in self.answers if q.startswith("u")]
        self.detections = {**self.cached(DETECTIONS_PATH, builtin), **self.cached(USER_DETECTIONS_PATH, made)}
        # 作ったが、まだ保存していない偽物（見分けるポイントを付けると保存する）
        self.fake_drafts: dict[str, tuple] = {}

    def image_path(self, question_id: str):
        return (USER_QUESTION_DIR if question_id.startswith("u") else QUESTION_IMAGE_DIR) / f"{question_id}.png"

    def detect(self, question_id: str) -> list[dict]:
        with self.lock:
            return self.detector.detect(self.image_path(question_id), self.answers[question_id], seed=seed_of(question_id))

    def cached(self, path, question_ids: list[str]) -> dict[str, list[dict]]:
        """保存した検出結果を読む。ない問題・古い結果だけ検出し直して保存する"""
        saved = load_detections(path, self.detector.key)
        missing = [q for q in question_ids if q not in saved]
        if missing:
            print(f"YOLO の検出結果がない・古い問題を検出し直します（{len(missing)} 問）", flush=True)
            saved.update({q: self.detect(q) for q in missing})
            save_detections(path, self.detector.key, saved)
        return {q: saved[q] for q in question_ids}

    def candidates(self, question_id: str) -> list[dict]:
        """ヒントに使う YOLO の候補（本物らしさの確信度が高い順）"""
        return [d for d in self.detections[question_id] if not d["fake"]]

    def real_rank(self, question_id: str) -> int | None:
        """YOLO の候補の中で本物が何番目か（1 始まり。候補に入っていなければ None）"""
        return next((k + 1 for k, d in enumerate(self.candidates(question_id)) if d["match"] == 0), None)

    def title(self, question_id: str) -> str:
        a = self.answers[question_id]
        return f"★ {a.get('title') or '無題'}（{a.get('author') or '名無し'}）" if question_id.startswith("u") else f"問題 {question_id}"

    def info(self) -> dict:
        ordered = sorted(self.answers, key=lambda q: (q.startswith("u"), int(q.lstrip("u"))))
        return {
            "questions": [{"id": q, "title": self.title(q), "real_rank": self.real_rank(q)} for q in ordered],
            "levels": LEVELS,
            "yolo": {"mode": self.detector.mode, "reason": self.detector.reason},
        }

    def question(self, question_id: str) -> dict:
        answer = self.answers[question_id]
        characters = [{**c, "feature": create.feature(c["image"]) if c["kind"] == "fake" else None} for c in answer["characters"]]
        return {**answer, "id": question_id, "characters": characters, "detections": self.detections[question_id]}

    # ---- 問題を作る ----
    def create_options(self) -> dict:
        return {
            "backgrounds": create.backgrounds(), "characters": create.characters(), "theme_example": THEME_EXAMPLE,
            "width_range": WIDTH_RANGE, "default_width": DEFAULT_WIDTH, "gap": PLACE_GAP,
        }

    def sprite(self, req: dict) -> dict:
        with self.lock:
            return create.sprite(req["background"], req["kind"], req["name"], int(req["width"]), bool(req["flip"]))

    def make_fake(self, req: dict) -> dict:
        """偽物を作って見せる（まだ保存しない）"""
        image = create.generate_fake(req["prompt"])
        draft_id = uuid.uuid4().hex
        self.fake_drafts = {draft_id: (image, req["prompt"])}
        return {"draft": draft_id, "preview": create.to_data_url(image)}

    def save_fake(self, req: dict) -> dict:
        """見分けるポイント（名前）を付けて、作った偽物を保存する"""
        if req["draft"] not in self.fake_drafts:
            raise ValueError("保存する偽物がない（もう一度作ってください）")
        image, prompt = self.fake_drafts[req["draft"]]
        made = create.save_fake(image, prompt, req.get("label", ""))
        del self.fake_drafts[req["draft"]]
        return made

    def register(self, req: dict) -> dict:
        if not req.get("title", "").strip():
            raise ValueError("問題の名前を書いてください（書かないと登録されません）")
        background = req["background"]
        with self.lock:
            image, answer = create.compose(background, req["placements"])
        meta = {"title": req["title"].strip()[:40], "author": req.get("author", "").strip()[:20], "background": background}
        question_id = create.save_question(image, answer, meta)
        self.answers[question_id] = {**answer, **meta}
        self.detections[question_id] = self.detect(question_id)
        made = {q: d for q, d in self.detections.items() if q.startswith("u")}
        save_detections(USER_DETECTIONS_PATH, self.detector.key, made)
        rank = self.real_rank(question_id)
        top = next(iter(self.candidates(question_id)), None)
        # YOLO が一番自信を持った候補が偽物なら、その偽物の特徴も返す（「AI が偽物に引っかかった」）
        fooled_by = None
        if top and top["match"] not in (None, 0):
            fooled_by = create.feature(answer["characters"][top["match"]]["image"])
        return {
            "id": question_id, "real_rank": rank, "fooled": rank is None or rank > FOOL_TOP, "fooled_by": fooled_by,
            "top_conf": top["conf"] if top else None, "fool_top": FOOL_TOP,
        }


def handler(game: Game):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, body: bytes, content_type: str, status: int = 200):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, data, status: int = 200):
            self._send(json.dumps(data, ensure_ascii=False).encode(), "application/json; charset=utf-8", status)

        def _png(self, path):
            self._send(path.read_bytes(), "image/png") if path.exists() else self._send(b"", "text/plain", 404)

        def do_GET(self):
            path = self.path.split("?")[0]
            if path in PAGES:
                self._send((APP_DIR / "static" / PAGES[path]).read_bytes(), "text/html; charset=utf-8")
            elif path == "/api/info":
                self._json(game.info())
            elif path == "/api/create/options":
                self._json(game.create_options())
            elif m := re.fullmatch(r"/api/questions/(u?\d+)", path):
                self._json(game.question(m.group(1))) if m.group(1) in game.answers else self._send(b"", "text/plain", 404)
            elif m := re.fullmatch(r"/img/(u?\d+)\.png", path):
                self._png(game.image_path(m.group(1)))
            elif m := re.fullmatch(r"/chara/(real|fake)/(k?\d+\.png)", path):
                self._png(create.character_path(m.group(1), m.group(2)))
            elif m := re.fullmatch(r"/background/([bg]\d+)\.png", path):
                self._png(create.background_path(m.group(1)))
            else:
                self._send(b"", "text/plain", 404)

        def do_POST(self):
            routes = {
                "/api/create/scene": lambda req: {"scene": create.describe_scene(req["theme"])},
                "/api/create/background": lambda req: create.generate_background(req["theme"], req["scene"]),
                "/api/create/fake": game.make_fake,
                "/api/create/fake/save": game.save_fake,
                "/api/create/sprite": game.sprite,
                "/api/create/register": game.register,
            }
            route = routes.get(self.path)
            if route is None:
                self._send(b"", "text/plain", 404)
                return
            req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            try:
                self._json(route(req))
            except Exception as e:  # 画面にエラーの内容を出す
                self._json({"error": str(e)}, 500)

        def log_message(self, *args):
            pass

    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    load_env()  # .env の GEMINI_API_KEY（背景・偽物を Gemini で作るときに使う）
    game = Game()
    mode = "YOLO" if game.detector.mode == "yolo" else f"モック（{game.detector.reason}）"
    url = f"http://localhost:{args.port}/"
    print(f"Kaira君を探せ: 解く {url}  作る {url}create  ヒント: {mode}  （終了は Ctrl+C）", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    ThreadingHTTPServer(("localhost", args.port), handler(game)).serve_forever()


if __name__ == "__main__":
    main()
