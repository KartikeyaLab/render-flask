import os
import zipfile
import shutil
import subprocess
import requests
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from flask_cors import CORS

# Load environment variables
load_dotenv()

# Flask setup
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
UPLOAD_FOLDER = "uploads"
EXTRACT_FOLDER = "site"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Home route (optional form interface)
@app.route('/')
def index():
    return render_template("index.html")

# API Endpoint
@app.route('/api/deploy', methods=['POST'])
def api_deploy():
    zip_file = request.files.get('zipfile')
    github_username = request.form.get('username')
    repo_name = request.form.get('repo')
    github_token = os.getenv("GITHUB_TOKEN")
    branch = "gh-pages"

    if not zip_file or not github_username or not repo_name:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        # Ensure upload folder exists
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)

        # Save zip
        zip_path = os.path.join(UPLOAD_FOLDER, zip_file.filename)
        zip_file.save(zip_path)

        # Extract
        if os.path.exists(EXTRACT_FOLDER):
            shutil.rmtree(EXTRACT_FOLDER)
        os.makedirs(EXTRACT_FOLDER)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(EXTRACT_FOLDER)

        # Create GitHub repo
        headers = {"Authorization": f"token {github_token}"}
        data = {"name": repo_name, "auto_init": False, "private": False}
        response = requests.post("https://api.github.com/user/repos", json=data, headers=headers)
        if response.status_code != 201:
            return jsonify({"error": "Failed to create GitHub repo", "details": response.text}), 500

        # Git operations
        os.chdir(EXTRACT_FOLDER)
        subprocess.run(["git", "init"], check=True)
        subprocess.run(["git", "config", "user.name", github_username], check=True)
        subprocess.run(["git", "config", "user.email", f"{github_username}@users.noreply.github.com"], check=True)
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)
        subprocess.run(["git", "branch", "-M", branch], check=True)
        subprocess.run(["git", "remote", "add", "origin",
                        f"https://{github_username}:{github_token}@github.com/{github_username}/{repo_name}.git"],
                       check=True)
        subprocess.run(["git", "push", "-u", "origin", branch], check=True)

        # Enable GitHub Pages
        pages_data = {"source": {"branch": branch, "path": "/"}}
        pages_response = requests.post(
            f"https://api.github.com/repos/{github_username}/{repo_name}/pages",
            json=pages_data,
            headers=headers
        )

        if pages_response.status_code not in [201, 204]:
            return jsonify({"error": "Failed to enable GitHub Pages", "details": pages_response.text}), 500

        url = f"https://{github_username}.github.io/{repo_name}/"
        return jsonify({"message": "✅ Website published", "url": url}), 200

    except Exception as e:
        return jsonify({"error": "An error occurred", "details": str(e)}), 500

if __name__ == '__main__':
    app.run()
