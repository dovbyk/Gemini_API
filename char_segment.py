import cv2
import os
import numpy as np
import base64
import itertools
import requests

OPENROUTER_KEYS = [
    os.getenv("OPENROUTER_KEY_1"),
    os.getenv("OPENROUTER_KEY_2"),
    os.getenv("OPENROUTER_KEY_3"),
]

key_cycle = itertools.cycle(OPENROUTER_KEYS)

def get_next_key():
    return next(key_cycle)

def recognize_characters_from_images(image_paths):
    api_key = get_next_key()

    images_payload = []
    for path in image_paths:
        with open(path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        images_payload.append({
            "type": "input_image",
            "image_url": f"data:image/png;base64,{encoded}"
        })

    prompt = (
        "You are given up to 6 images of individual handwritten characters, "
        "in order from left to right, top to bottom. "
        "Characters may be a-z, A-Z, or 0-9. "
        "Return ONLY the exact sequence of characters. "
        "Do NOT include spaces, explanations, or extra text. "
        "The length of the response MUST equal the number of images."
    )

    payload = {
        "model": "google/gemini-2.0-flash",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    *images_payload
                ]
            }
        ],
        "temperature": 0
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "handwritten-character-ocr"
    }

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=60
    )

    response.raise_for_status()
    result = response.json()

    characters = result["choices"][0]["message"]["content"].strip()

    # Defensive check
    if len(characters) != len(image_paths):
        print(f"Warning: Gemini returned '{characters}' for {len(image_paths)} images")
        characters = characters[:len(image_paths)]

    return characters


def process_uploaded_image(input_image_path):
    output_directory = "processed_characters"
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    
    image = cv2.imread(input_image_path)
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, binary_image = cv2.threshold(gray_image, 127, 255, cv2.THRESH_BINARY_INV)
    
    kernel = np.ones((3, 3), np.uint8)
    binary_image = cv2.morphologyEx(binary_image, cv2.MORPH_OPEN, kernel)
    binary_image = cv2.morphologyEx(binary_image, cv2.MORPH_CLOSE, kernel)
    
    contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    bounding_boxes = [cv2.boundingRect(c) for c in contours]
    
    def merge_close_boxes(boxes, threshold=20):
        merged_boxes = []
        for box in boxes:
            x, y, w, h = box
            merged = False
            for i in range(len(merged_boxes)):
                mx, my, mw, mh = merged_boxes[i]
                if not (x > mx + mw + threshold or mx > x + w + threshold or
                        y > my + mh + threshold or my > y + h + threshold):
                    nx, ny = min(x, mx), min(y, my)
                    nw, nh = max(x + w, mx + mw) - nx, max(y + h, my + mh) - ny
                    merged_boxes[i] = (nx, ny, nw, nh)
                    merged = True
                    break
            if not merged:
                merged_boxes.append(box)
        return merged_boxes
    
    merged_boxes = merge_close_boxes(bounding_boxes)
    sorted_boxes = sorted(merged_boxes, key=lambda b: (b[1], b[0]))
    extracted_images = []
    temp_image_paths = []
    batch_size = 6
    i = 0
    for i, (x, y, w, h) in enumerate(sorted_boxes):
        if w > 10 and h > 10:
            char_image = binary_image[y:y + h, x:x + w]
            temp_path = os.path.join(output_directory, f"temp_{i}.png")
            cv2.imwrite(temp_path, 255 - char_image)
            print(f"Before : {temp_path}")
            temp_image_paths.append(temp_path)

            # When batch is ready or last image, process batch
            if len(temp_image_paths) == batch_size or i == len(sorted_boxes) - 1:
                if i == len(sorted_boxes) - 1:
                    print("i has reached the final image")
                recognized_chars = recognize_characters_from_images(temp_image_paths)
                for img_path, char in zip(temp_image_paths, recognized_chars):
                    output_path = os.path.join(output_directory, f"{char}.png")    
                    counter = 1
                    while os.path.exists(output_path):
                        base_name = f"{char}_{counter}.png"
                        output_path = os.path.join(output_directory, base_name)
                        counter += 1
        
                    os.rename(img_path, output_path)
                    print(f"Saved: {output_path}")
                    extracted_images.append(output_path)
                temp_image_paths = []  # Reset for next batch

    
    print(f"Final value of i: {i}")    
    print(f"Length of extracted images: {len(extracted_images)}")
    return extracted_images

