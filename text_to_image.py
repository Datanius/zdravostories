import json
import os
import time
import hashlib
from pathlib import Path
from typing import Dict, Optional

import requests
from dotenv import load_dotenv
from PIL import Image
import io

load_dotenv()

# Image generation settings
IMAGE_WIDTH = 640  # Multiple of 32
IMAGE_HEIGHT = 352  # Multiple of 32, 16:9 ratio
ASPECT_RATIO = "16:9"

class ImageGenerationError(Exception):
    pass

class ImageGenerator:
    def __init__(self):
        self.api_key = os.getenv('API_KEY')
        if not self.api_key:
            raise ValueError("API_KEY environment variable not set")
            
        self.api_urls = {
            'dev': "https://api.us1.bfl.ai/v1/flux-dev",
            'pro': "https://api.us1.bfl.ai/v1/flux-pro-1.1", 
            'ultra': "https://api.us1.bfl.ai/v1/flux-pro-1.1-ultra",
            'status': "https://api.us1.bfl.ai/v1/get_result"
        }
        
        # Polling configuration
        self.max_retries = 6
        self.initial_delay = 2  # seconds
        self.backoff_factor = 2

    def generate(self, prompt: str, model: str = 'pro') -> Optional[str]:
        headers = {
            "Content-Type": "application/json",
            "X-Key": self.api_key
        }
        
        data = {
            "prompt": f"Generate in a cartoonish style: {prompt}",
            "output_format": "png"
        }

        if model == 'ultra':
            data["aspect_ratio"] = ASPECT_RATIO
        else:
            data["width"] = str(IMAGE_WIDTH)
            data["height"] = str(IMAGE_HEIGHT)
        
        try:
            response = requests.post(self.api_urls[model], headers=headers, json=data)
            response.raise_for_status()
            return response.json().get('id')
        except requests.exceptions.RequestException as e:
            raise ImageGenerationError(f"Failed to generate image: {str(e)}") from e

    def check_status(self, task_id: str) -> Optional[str]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        delay = self.initial_delay
        
        for attempt in range(self.max_retries):
            try:
                response = requests.get(f"{self.api_urls['status']}?id={task_id}", headers=headers)
                response.raise_for_status()
                status_data = response.json()
                
                if status_data.get('status') == 'Ready':
                    return status_data.get('result', {}).get('sample')
                if status_data.get('status') == 'failed':
                    return None
                    
                print(f"Task {task_id} processing, attempt {attempt + 1}/{self.max_retries}...")
                time.sleep(delay)
                delay *= self.backoff_factor
                
            except requests.exceptions.RequestException:
                continue
                
        return None

class ImageProcessor:
    def __init__(self, image_dir: str = "images"):
        self.image_dir = image_dir

    def download_image(self, image_url: str, save_path: Path, model: str = 'pro') -> bool:
        try:
            response = requests.get(image_url)
            response.raise_for_status()
            
            if model == 'ultra':
                # Process ultra model images to correct size
                image = Image.open(io.BytesIO(response.content))
                image = image.resize((IMAGE_WIDTH, IMAGE_HEIGHT), Image.Resampling.LANCZOS)
                image.save(save_path, 'PNG', quality=95)
            else:
                save_path.write_bytes(response.content)
            return True
        except requests.exceptions.RequestException:
            return False

    def extract_json_from_markdown(self, markdown_file: Path) -> Optional[Dict]:
        content = markdown_file.read_text(encoding='utf-8')
        
        try:
            start = content.find("{")
            end = content.find("}") + 1
            if start == -1 or end == 0:
                return None
                
            json_str = content[start:end]
            json_data = json.loads(json_str)
            
            # Remove JSON from markdown
            new_content = content[:start].rstrip() + content[end:].lstrip()
            markdown_file.write_text(new_content, encoding='utf-8')
            
            return json_data
        except (json.JSONDecodeError, IOError):
            return None

    def replace_in_markdown(self, content: str, replacements: Dict[str, str]) -> str:
        for placeholder, image_path in replacements.items():
            content = content.replace(
                f"({placeholder})",
                f"({image_path})      "
            )
        return content

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Generate images from markdown file prompts')
    parser.add_argument('markdown_file', type=Path, help='Path to markdown file containing image prompts')
    parser.add_argument('--model', choices=['pro', 'ultra'], default='pro', help='Model version to use')
    args = parser.parse_args()

    markdown_dir = args.markdown_file.parent
    image_dir = markdown_dir / "images"
    image_dir.mkdir(exist_ok=True)
    
    generator = ImageGenerator()
    processor = ImageProcessor()
    
    prompts = processor.extract_json_from_markdown(args.markdown_file)
    if not prompts:
        print("No valid prompts found in markdown file")
        return
    replacements = {}
    for placeholder, prompt in prompts.items():
        try:
            # Generate unique hash from prompt
            hash_obj = hashlib.md5(prompt.encode())
            unique_hash = f"Img_{hash_obj.hexdigest()[:6]}"
            
            task_id = generator.generate(prompt, model=args.model)
            if not task_id:
                continue
                
            image_url = generator.check_status(task_id)
            if not image_url:
                continue
                
            image_path = image_dir / f"{unique_hash}.png"
            if processor.download_image(image_url, image_path, model=args.model):
                # Force forward slash in path
                replacements[placeholder] = f"images/{unique_hash}.png"
                
        except ImageGenerationError as e:
            print(f"Failed to generate image for {placeholder}: {e}")
            continue
    
    content = args.markdown_file.read_text(encoding='utf-8')
    new_content = processor.replace_in_markdown(content, replacements)
    args.markdown_file.write_text(new_content, encoding='utf-8')

if __name__ == "__main__":
    main()