from django.shortcuts import render
from .forms import PowerPointForm
from .models import PowerPoint
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account
from PIL import Image
from django.conf import settings
from PIL import Image
import io
import os
import requests

# Define SCOPES and credentials for Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = os.path.join(settings.BASE_DIR, 'serviceaccount.json')

# Authorization with service account
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)


def upload_ppt(request):
    if request.method == 'POST':
        form = PowerPointForm(request.POST, request.FILES)
        if form.is_valid():
            ppt = form.save()
            # Convert to Google Slides and generate thumbnails
            convert_to_slides_and_save_thumbnails(ppt)
    else:
        form = PowerPointForm()
    return render(request, 'convertor/upload.html', {'form': form})
import urllib.request

def download_image(url, save_path):
    response = requests.get(url)
    if response.status_code == 200:
        with open(save_path, 'wb') as f:
            f.write(response.content)
    else:
        raise Exception(f"Failed to download image from {url}")
def create_combined_thumbnail(image_paths, output_filename):
    # Open all the images
    images = [Image.open(path) for path in image_paths]

    # Optionally resize all images to the same size (this is useful if they differ)
    thumbnail_size = (400, 400)  # You can change this size
    images = [img.resize(thumbnail_size) for img in images]

    # Calculate the grid size based on the number of images
    grid_size = (min(3, len(images)), (len(images) + 2) // 3)  # 3 columns per row

    # Create a blank canvas for the combined thumbnail (white background)
    combined_width = grid_size[0] * thumbnail_size[0]
    combined_height = grid_size[1] * thumbnail_size[1]
    combined_image = Image.new('RGB', (combined_width, combined_height), 'white')

    # Paste each image into the combined canvas
    for idx, img in enumerate(images):
        x_offset = (idx % grid_size[0]) * thumbnail_size[0]
        y_offset = (idx // grid_size[0]) * thumbnail_size[1]
        combined_image.paste(img, (x_offset, y_offset))

    # Save the combined image in the media folder
    output_path = os.path.join(settings.MEDIA_ROOT, 'thumbnails', output_filename)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    combined_image.save(output_path)

    return os.path.join(settings.MEDIA_URL, 'thumbnails', output_filename)
def convert_to_slides_and_save_thumbnails(ppt):
    drive_service = build('drive', 'v3', credentials=credentials)
    slides_service = build('slides', 'v1', credentials=credentials)

    # Upload the file to Google Drive
    file_metadata = {'name': ppt.name, 'mimeType': 'application/vnd.google-apps.presentation'}
    media = MediaFileUpload(ppt.file.path,
                            mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation')

    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    presentation_id = file.get('id')

    # Export each slide as an image
    presentation = slides_service.presentations().get(presentationId=presentation_id).execute()
    slides = presentation.get('slides', [])
    image_urls=[]
    for index, slide in enumerate(slides, start=1):
        slide_id = slide.get('objectId')
        slide_img_url=slides_service.presentations().pages().getThumbnail(presentationId=presentation_id, pageObjectId=slide_id, thumbnailProperties_mimeType='PNG', thumbnailProperties_thumbnailSize='LARGE', x__xgafv=None).execute()["contentUrl"]
        filename = f"{ppt.name}_slide_{index}.png"
        media_path = os.path.join(settings.MEDIA_ROOT, 'thumbnails', filename)
        os.makedirs(os.path.dirname(media_path), exist_ok=True)
        download_image(slide_img_url, media_path)
        image_urls.append(media_path)

    # Optionally, delete the uploaded presentation from Google Drive
    path="combined.png"
    create_combined_thumbnail(image_urls, path)
    drive_service.files().delete(fileId=presentation_id).execute()

