import os
import zipfile
import shutil
import subprocess
import requests
import time
from flask import Flask, render_template, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
EXTRACT_FOLDER = "site"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        zip_file = request.files['zipfile']
        github_username = request.form['username']
        github_token = os.getenv("GITHUB_TOKEN")
        repo_name = request.form['repo']
        branch = "gh-pages"

        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)

        zip_path = os.path.join(UPLOAD_FOLDER, zip_file.filename)
        zip_file.save(zip_path)

        if os.path.exists(EXTRACT_FOLDER):
            shutil.rmtree(EXTRACT_FOLDER)
        os.makedirs(EXTRACT_FOLDER)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(EXTRACT_FOLDER)

        headers = {"Authorization": f"token {github_token}"}
        data = {"name": repo_name, "auto_init": False, "private": False}
        response = requests.post("https://api.github.com/user/repos", json=data, headers=headers)
        if response.status_code != 201:
            return f"Failed to create GitHub repo: {response.text}"

        os.chdir(EXTRACT_FOLDER)
        subprocess.run(["git", "init"])
        subprocess.run(["git", "config", "user.name", github_username])
        subprocess.run(["git", "config", "user.email", f"{github_username}@users.noreply.github.com"])

        open('.nojekyll', 'w').close()

        subprocess.run(["git", "add", "."])
        subprocess.run(["git", "commit", "-m", "Initial commit"])
        subprocess.run(["git", "branch", "-M", branch])
        subprocess.run([
            "git", "remote", "add", "origin",
            f"https://{github_username}:{github_token}@github.com/{github_username}/{repo_name}.git"
        ])
        subprocess.run(["git", "push", "-u", "origin", branch])

        time.sleep(5)

        pages_data = {"source": {"branch": branch, "path": "/"}}
        pages_response = requests.put(
            f"https://api.github.com/repos/{github_username}/{repo_name}/pages",
            json=pages_data,
            headers=headers
        )

        if pages_response.status_code not in [201, 204]:
            return f"Failed to enable GitHub Pages: {pages_response.text}"
        url = f"https://{github_username}.github.io/{repo_name}/"

        for attempt in range(20):  # Try for about 60 seconds
            try:
                site_response = requests.get(url, timeout=5)
                if site_response.status_code == 200:
                    return f"""<!DOCTYPE html>
<html lang="en" class="bg-[#10121b] text-white font-[Inter]">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Website Published · Kartikeya’s Lab</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet" />
    <script src="https://cdn.tailwindcss.com"></script>
  
  </head>
  <body class="min-h-screen flex items-center justify-center px-4">
    <div class="max-w-xl w-full bg-white/5 backdrop-blur-md border border-white/10 rounded-2xl shadow-xl p-8 text-center space-y-6 animate-fade-in">
      <h1 class="text-4xl sm:text-5xl font-semibold tracking-tight">🎉 Website Published</h1>
      <p class="text-white/70 text-lg">Your website is now live on the internet.</p>

      <div>
        <p class="text-white/50 text-sm mb-1">Your website URL</p>
        <a href="{url}" target="_blank" class="inline-block text-sky-400 text-base sm:text-lg underline hover:text-sky-300 transition">
          {url}
        </a>
      </div>

      <p class="text-sm text-white/40 leading-relaxed">
        Please allow a few moments for changes to reflect. Thank you for publishing with <span class="font-semibold text-white/60">Kartikeya’s Lab</span>.
      </p>
    </div>
  </body>
</html>"""
            except requests.RequestException:
                pass
            time.sleep(3)

        return f"Website created, but GitHub Pages is still provisioning. Please check <a href='{url}' target='_blank'>{url}</a> after a few moments."
    
    return render_template("index.html")

if __name__ == '__main__':
    app.run(debug=True)
