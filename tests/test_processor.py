from pathlib import Path
from text_to_image import ImageProcessor


def test_extract_json_from_markdown(tmp_path):
    md = tmp_path / 'sample.md'
    md.write_text('{"IMG": "a cat"}\nContent here', encoding='utf-8')
    processor = ImageProcessor()
    prompts = processor.extract_json_from_markdown(md)
    assert prompts == {"IMG": "a cat"}
    new_content = md.read_text(encoding='utf-8')
    assert 'Content here' in new_content

def test_replace_in_markdown():
    content = 'Look at (IMG1) and (IMG2).'
    replacements = {'IMG1': 'img1.png', 'IMG2': 'img2.png'}
    processor = ImageProcessor()
    result = processor.replace_in_markdown(content, replacements)
    assert '(img1.png)' in result
    assert '(img2.png)' in result
