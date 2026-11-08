"""Kaira君を探せ（YOLO をヒントにする版）のモックアプリ。問題を「作る」画面と「解く」画面がある

uv run python app/server.py   # YOLO なし（ヒントはモック）、背景の生成なしで動かす
YOLO（data/best.pt）や Gemini での背景の生成を使うときの起動方法は app/README.md
"""
import argparse
import json
import re
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import create
from config import (
    ANSWERS_PATH, APP_DIR, DEFAULT_WIDTH, FOOL_TOP, LEVELS, PLACE_GAP, PORT, QUESTION_IMAGE_DIR, THEME_EXAMPLE,
    USER_QUESTION_DIR, WIDTH_RANGE,
)
from detect import Detector

PAGES = {"/": "solve.html", "/create": "create.html"}


class Game:
    def __init__(self):
        if not ANSWERS_PATH.exists():
            raise SystemExit("answers.json がない。先に uv run python app/build_answers.py を実行する")
        # 問題の番号：用意した問題は "1"〜、お客さんが作った問題は "u1"〜
        self.answers = {str(k): v for k, v in json.loads(ANSWERS_PATH.read_text()).items()}
        self.answers.update(create.saved_questions())
        self.detector = Detector()
        self.lock = threading.Lock()
        # 問題の一覧に「AI も見つけられない問題」を出すため、起動時に全問を検出しておく
        self.detections = {q: self.detect(q) for q in self.answers}

    def image_path(self, question_id: str):
        return (USER_QUESTION_DIR if question_id.startswith("u") else QUESTION_IMAGE_DIR) / f"{question_id}.png"

    def detect(self, question_id: str) -> list[dict]:
        with self.lock:
            return self.detector.detect(self.image_path(question_id), self.answers[question_id], seed=hash(question_id) % 1000)

    def real_rank(self, question_id: str) -> int | None:
        """YOLO の推定（確信度の高い順）で本物が何番目か（1 始まり。見つけていなければ None）"""
        candidates = [d for d in self.detections[question_id] if not d["fake"]]
        return next((k + 1 for k, d in enumerate(candidates) if d["match"] == 0), None)

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

    def register(self, req: dict) -> dict:
        background = req["background"]
        with self.lock:
            image, answer = create.compose(background, req["placements"])
        meta = {"title": req.get("title", "")[:40], "author": req.get("author", "")[:20], "background": background}
        question_id = create.save_question(image, answer, meta)
        self.answers[question_id] = {**answer, **meta}
        self.detections[question_id] = self.detect(question_id)
        rank = self.real_rank(question_id)
        top = next((d for d in self.detections[question_id] if not d["fake"]), None)
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
                "/api/create/background": lambda req: create.generate_background(req["theme"]),
                "/api/create/kaira": lambda req: create.generate_kaira(req["kind"], req["prompt"], req.get("label", "")),
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
    game = Game()
    mode = "YOLO" if game.detector.mode == "yolo" else f"モック（{game.detector.reason}）"
    url = f"http://localhost:{args.port}/"
    print(f"Kaira君を探せ: 解く {url}  作る {url}create  ヒント: {mode}  （終了は Ctrl+C）", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    ThreadingHTTPServer(("localhost", args.port), handler(game)).serve_forever()


if __name__ == "__main__":
    main()
