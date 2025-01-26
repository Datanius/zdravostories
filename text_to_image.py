import json
import os
import time
import requests
import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Configuration
DEV_API_URL = "https://api.us1.bfl.ai/v1/flux-dev"
API_URL = "https://api.us1.bfl.ai/v1/flux-pro-1.1"
STATUS_URL = "https://api.us1.bfl.ai/v1/get_result"
API_KEY = os.getenv('API_KEY')
IMAGE_DIR = "images"  # Default image directory name

# Polling parameters
MAX_RETRIES = 6              # Maximum polling attempts
INITIAL_DELAY = 2            # Initial wait time in seconds
BACKOFF_FACTOR = 2           # Exponential backoff factor

def generate_image(prompt):
    """Generate image using BFL API"""
    # Add cartoon style prefix to prompt
    cartoon_prompt = f"Generate in a cartoonish style: {prompt}"
    
    headers = {
        "Content-Type": "application/json",
        "X-Key": API_KEY
    }
    data = {
        "prompt": cartoon_prompt,
        "width": "640",  # Multiple of 32
        "height": "352", # Multiple of 32, maintains 16:9 ratio (640/352 ≈ 16/9)
        "output_format": "png"  # Adjust as needed
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=data)
        response.raise_for_status()
        return response.json().get('id')
    except requests.exceptions.RequestException as e:
        print(e.response.text)
        print(f"Error generating image: {e}")
        return None

def replace_in_markdown(markdown_content, replacements):
    """Replace placeholders in markdown content"""
    for placeholder, image_path in replacements.items():
        markdown_content = markdown_content.replace(
            f"({placeholder})",        # Looks for (PLACEHOLDER) in markdown
            f"({image_path})      "    # Replaces with markdown image syntax
        )
    return markdown_content

def check_image_status(task_id):
    """Check generation status with exponential backoff"""
    headers = {"Authorization": f"Bearer {API_KEY}"}
    delay = INITIAL_DELAY
    attempts = 0
    
    while attempts < MAX_RETRIES:
        try:
            response = requests.get(f"{STATUS_URL}?id={task_id}", headers=headers)
            response.raise_for_status()
            status_data = response.json()
            
            if status_data.get('status') == 'Ready':
                return status_data.get('result').get('sample')
            elif status_data.get('status') == 'failed':
                print(f"Generation failed for task {task_id}")
                return None
            else:
                print(f"Task {task_id} still processing, waiting {delay}s...")
                time.sleep(delay)
                delay *= BACKOFF_FACTOR
                attempts += 1
                
        except requests.exceptions.RequestException as e:
            print(f"Status check failed: {e}")
            return None
    
    print(f"Timeout reached for task {task_id}")
    return None

def download_image(image_url, save_path):
    """Download final image from URL"""
    try:
        response = requests.get(image_url)
        response.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(response.content)
        return True
    except requests.exceptions.RequestException as e:
        print(f"Download failed: {e}")
        return False

def extract_json_from_markdown(markdown_file):
    """Extract JSON from markdown file"""
    with open(markdown_file, "r", encoding='utf-8') as f:
        content = f.read()
    
    start = content.find("{")
    if start == -1:
        return None
    
    end = content.find("}", start) + 1
    if end == -1:
        return None
        
    json_str = content[start:end].strip()
    
    try:
        json_data = json.loads(json_str)
        
        # Remove the JSON from the markdown file
        new_content = content[:start].rstrip() + content[end:].lstrip()
        with open(markdown_file, "w", encoding='utf-8') as f:
            f.write(new_content)
            
        return json_data
    except json.JSONDecodeError:
        return None

def main():
    parser = argparse.ArgumentParser(description='Generate images from markdown file prompts')
    parser.add_argument('markdown_file', help='Path to markdown file containing image prompts')
    args = parser.parse_args()

    # Get markdown file directory to make image dir relative to it
    markdown_dir = Path(args.markdown_file).parent
    image_dir = markdown_dir / IMAGE_DIR
    image_dir.mkdir(exist_ok=True)
    
    prompts = extract_json_from_markdown(args.markdown_file)
    if not prompts:
        print("Could not extract prompts from markdown file")
        return
    
    replacements = {}
    
    for placeholder, prompt in prompts.items():
        task_id = generate_image(prompt)
        if not task_id:
            continue
            
        image_url = check_image_status(task_id)
        if not image_url:
            continue
            
        image_path = image_dir / f"{placeholder}.png"
        if download_image(image_url, image_path):
            # Store relative path from markdown file to image
            replacements[placeholder] = str(Path(IMAGE_DIR) / f"{placeholder}.png")
    
    # Update markdown file
    with open(args.markdown_file, "r", encoding='utf-8') as f:
        content = f.read()
    
    new_content = replace_in_markdown(content, replacements)
    
    with open(args.markdown_file, "w", encoding='utf-8') as f:
        f.write(new_content)

if __name__ == "__main__":
    main()