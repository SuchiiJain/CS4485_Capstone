from flask import Flask, request, jsonify
from storage import init_db, save_scan

app = Flask(__name__)
init_db()


@app.route("/health")
def health():
    return {"status": "ok"}


@app.route("/api/scan", methods=["POST"])
def receive_scan():
    data = request.json

    repo = data.get("repo")
    commit = data.get("commit")
    report = data.get("report")

    save_scan(repo, commit, report)

    return jsonify({"message": "Scan stored"}), 200


if __name__ == "__main__":
    app.run(port=8000)
