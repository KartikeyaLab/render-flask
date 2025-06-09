import os
import zipfile
import shutil
import subprocess
import requests
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
EXTRACT_FOLDER = "site"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        zip_file = request.files['zipfile']
        github_username = request.form['username']
        github_token = request.form['token']
        repo_name = request.form['repo']
        branch = "gh-pages"

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
            return f"Failed to create GitHub repo: {response.text}"

        # Initialize git
        os.chdir(EXTRACT_FOLDER)
        subprocess.run(["git", "init"])
        subprocess.run(["git", "config", "user.name", github_username])
        subprocess.run(["git", "config", "user.email", f"{github_username}@users.noreply.github.com"])
        subprocess.run(["git", "add", "."])
        subprocess.run(["git", "commit", "-m", "Initial commit"])
        subprocess.run(["git", "branch", "-M", branch])
        subprocess.run(["git", "remote", "add", "origin",
                        f"https://{github_username}:{github_token}@github.com/{github_username}/{repo_name}.git"])
        subprocess.run(["git", "push", "-u", "origin", branch])

        # Enable GitHub Pages
        pages_data = {"source": {"branch": branch, "path": "/"}}
        pages_response = requests.post(f"https://api.github.com/repos/{github_username}/{repo_name}/pages",
                                       json=pages_data, headers=headers)

        if pages_response.status_code not in [201, 204]:
            return f"Failed to enable GitHub Pages: {pages_response.text}"

        url = f"https://{github_username}.github.io/{repo_name}/"
        return f"✅ Website published: <a href='{url}' target='_blank'>{url}</a>"

    return render_template("index.html")

if __name__ == '__main__':
    app.run()