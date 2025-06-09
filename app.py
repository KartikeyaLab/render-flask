import os
import zipfile
import shutil
import subprocess
import requests
from flask import Flask, render_template, request
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = "uploads"
EXTRACT_FOLDER = "site"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/', methods=['GET', 'POST'])
def index():
    message = None

    if request.method == 'POST':
        try:
            zip_file = request.files['zipfile']
            github_username = request.form['username']
            repo_name = request.form['repo']
            github_token = os.getenv("GITHUB_TOKEN")
            branch = "gh-pages"

            if not github_token:
                message = "❌ GitHub token not found in environment. Please check your .env file."
                return render_template("index.html", message=message)

            # Ensure upload folder exists
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)

            # Save uploaded ZIP file
            zip_path = os.path.join(UPLOAD_FOLDER, zip_file.filename)
            zip_file.save(zip_path)

            # Extract ZIP contents
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
                error_detail = response.json().get('message', 'Unknown error')
                message = f"❌ Failed to create GitHub repo: {error_detail}"
                return render_template("index.html", message=message)

            # Initialize Git and push to GitHub
            original_cwd = os.getcwd()
            os.chdir(EXTRACT_FOLDER)

            subprocess.run(["git", "init"], check=True)
            subprocess.run(["git", "config", "user.name", github_username], check=True)
            subprocess.run(["git", "config", "user.email", f"{github_username}@users.noreply.github.com"], check=True)
            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)
            subprocess.run(["git", "branch", "-M", branch], check=True)
            subprocess.run(["git", "remote", "add", "origin",
                            f"https://{github_username}:{github_token}@github.com/{github_username}/{repo_name}.git"], check=True)
            subprocess.run(["git", "push", "-u", "origin", branch], check=True)

            os.chdir(original_cwd)

            # Enable GitHub Pages
            pages_data = {"source": {"branch": branch, "path": "/"}}
            pages_response = requests.post(
                f"https://api.github.com/repos/{github_username}/{repo_name}/pages",
                json=pages_data, headers=headers)

            if pages_response.status_code not in [201, 204]:
                message = f"⚠️ Repo created and pushed, but GitHub Pages could not be enabled: {pages_response.text}"
            else:
                url = f"https://{github_username}.github.io/{repo_name}/"
                message = f"✅ Your website has been published: <a href='{url}' target='_blank'>{url}</a>"

        except Exception as e:
            message = f"❌ An unexpected error occurred: {str(e)}"

    return render_template("index.html", message=message)

if __name__ == '__main__':
    app.run(debug=True)
