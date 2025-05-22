from flask import Flask, render_template, abort
from pathlib import Path
import markdown

app = Flask(__name__)

STORIES = {
    'bosnian': Path('english_bosnian'),
    'german': Path('english_german'),
}

@app.route('/')
def index():
    story_map = {}
    for lang, path in STORIES.items():
        stories = [p.stem for p in path.glob('*.md')]
        story_map[lang] = stories
    return render_template('index.html', stories=story_map)

@app.route('/story/<lang>/<name>')
def show_story(lang: str, name: str):
    path = STORIES.get(lang)
    if not path:
        abort(404)
    file_path = path / f"{name}.md"
    if not file_path.exists():
        abort(404)
    md_content = file_path.read_text(encoding='utf-8')
    html_content = markdown.markdown(md_content)
    return render_template('story.html', content=html_content, title=name)

if __name__ == '__main__':
    app.run(debug=True)
