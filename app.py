from flask import Flask, render_template, abort, send_from_directory
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
    md_content = md_content.replace('images/', f'/story/{lang}/images/')
    html_content = markdown.markdown(md_content)
    return render_template('story.html', content=html_content, title=name)


@app.route('/story/<lang>/images/<path:filename>')
def story_image(lang: str, filename: str):
    path = STORIES.get(lang)
    if not path:
        abort(404)
    image_dir = path / 'images'
    return send_from_directory(image_dir, filename)

if __name__ == '__main__':
    app.run(debug=True)
