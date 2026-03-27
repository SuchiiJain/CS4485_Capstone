from flask import Flask, request, jsonify
from storage import init_db, save_scan
from auth import auth_bp, require_auth

app = Flask(__name__)
app.register_blueprint(auth_bp)
init_db()


@app.route("/health")
def health():
    return {"status": "ok"}


@app.route("/api/scan", methods=["POST"])
@require_auth
def receive_scan():
    data = request.json

    repo = data.get("repo")
    commit = data.get("commit")
    report = data.get("report")

    save_scan(repo, commit, report)

    return jsonify({"message": "Scan stored"}), 200


if __name__ == "__main__":
    app.run(port=8000)
