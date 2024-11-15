from flask import Flask, request, jsonify
import os
import tempfile
from pdf2image import convert_from_path
from PIL import Image
import concurrent.futures
import logging
import google.generativeai as genai
import shutil

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/upload-pdf', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files:
        return "No file part", 400
    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400

    # Create unique directories for this request
    temp_dir = tempfile.mkdtemp()
    pdf_folder = os.path.join(temp_dir, 'pdf')
    output_folder = os.path.join(temp_dir, 'images')
    os.makedirs(pdf_folder, exist_ok=True)
    os.makedirs(output_folder, exist_ok=True)

    # Save the PDF file
    pdf_path = os.path.join(pdf_folder, file.filename)
    file.save(pdf_path)
    logging.info(f"PDF saved to {pdf_path}")

    def convert_pdf_to_images(pdf_file):
        try:
            if pdf_file.endswith(".pdf"):
                images = convert_from_path(pdf_file, poppler_path=r"C:\\Program Files\\poppler-24.07.0\\Library\\bin")
                image_paths = []
                for i, image in enumerate(images):
                    output_path = os.path.join(output_folder, f"page_{i+1}.jpeg")
                    image.save(output_path, "JPEG")
                    image_paths.append(output_path)
                logging.info(f"Conversion completed for {pdf_file}")
                return image_paths
        except Exception as e:
            logging.error(f"Error converting {pdf_file} to images: {e}")
            return []

    def process_image(image_path):
        try:
            # Configure Google Generative AI API
            genai.configure(api_key="AIzaSyA2wiv-c9dmm5uOJ0vXAtrMbGqNDRsjLsc")

            # Open the image
            with open(image_path, "rb") as img_file:
                img_data = img_file.read()

            # Send the image to the Gemini API
            response = genai.generate_content(
                model_name="gemini-1.5-flash",
                inputs=[{"image": img_data}],
                prompt="Extract Father and Mother Name"
            )
            print(response)
            return {"image": image_path, "response": response}
        except Exception as e:
            logging.error(f"Error processing image {image_path}: {e}")
            return {"image": image_path, "error": str(e)}

    # Convert PDF to images
    try:
        image_paths = convert_pdf_to_images(pdf_path)
        if not image_paths:
            return "Failed to convert PDF to images", 500
    except Exception as e:
        logging.error(f"Error converting PDF to images: {e}")
        return "Conversion process failed", 500

    # Process images using multithreading
    responses = []
    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = executor.map(process_image, image_paths)
            responses = list(results)
    except Exception as e:
        logging.error(f"Error processing images: {e}")
        return "Image processing failed", 500

    # Clean up images and PDFs
    try:
        shutil.rmtree(temp_dir)
    except Exception as e:
        logging.error(f"Error cleaning up temporary directories: {e}")

    # Return the API responses
    return jsonify(responses), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
