import os
import yt_dlp
import re
import uuid
from django.conf import settings
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from threading import Lock

progress_data = {}
progress_lock = Lock()

def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*\n\r]', '_', filename)

def index(request):
    return render(request, 'downloader/index.html')

def download_progress_hook_factory(download_id):
    def hook(d):
        with progress_lock:
            if d['status'] == 'downloading':
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 1)
                progress_data[download_id] = {
                    'progress': int((downloaded / total) * 100),
                    'status': 'downloading'
                }
            elif d['status'] == 'finished':
                progress_data[download_id] = {
                    'progress': 100,
                    'status': 'finished',
                    'filename': d.get('filename')
                }
    return hook

def get_progress(request, download_id):
    with progress_lock:
        data = progress_data.get(download_id, {'progress': 0, 'status': 'pending'})
    return JsonResponse(data)

def download_video(request):
    if request.method == 'POST':
        video_url = request.POST.get('video_url')
        video_quality = request.POST.get('video_quality', '720p')

        if not video_url:
            return JsonResponse({'error': 'Please provide a video URL'}, status=400)

        download_id = str(uuid.uuid4())
        hook = download_progress_hook_factory(download_id)

        # Choose format
        ydl_opts = {
            'quiet': True,
            'progress_hooks': [hook],
            'outtmpl': os.path.join(settings.MEDIA_ROOT, '%(title)s.%(ext)s'),
             
        }

        if video_quality == 'audio':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            })
        else:
            ydl_opts.update({
                'format': f'bestvideo[height<={video_quality}]+bestaudio/best',
                'merge_output_format': 'mp4'
            })

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                filename = ydl.prepare_filename(info)

                # Handle postprocessing (e.g., mp3 conversion)
                if video_quality == 'audio':
                    filename = os.path.splitext(filename)[0] + '.mp3'

                safe_name = sanitize_filename(os.path.basename(filename))
                safe_path = os.path.join(settings.MEDIA_ROOT, safe_name)

                # Rename to safe filename
                if filename != safe_path:
                    os.rename(filename, safe_path)

                # Save filename for later streaming
                with progress_lock:
                    progress_data[download_id]['filename'] = safe_name

                return JsonResponse({
                    'download_id': download_id,
                    'filename': safe_name
                })

        except yt_dlp.utils.DownloadError as e:
            return JsonResponse({'error': f"Download error: {str(e)}"}, status=500)
        except Exception as e:
            return JsonResponse({'error': f"An error occurred: {str(e)}"}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=400)

def stream_download(request, download_id):
    with progress_lock:
        info = progress_data.get(download_id)

    if not info or info.get('status') != 'finished':
        return JsonResponse({'error': 'File not ready or not found'}, status=404)

    filepath = os.path.join(settings.MEDIA_ROOT, info['filename'])

    def file_stream(path):
        with open(path, 'rb') as f:
            yield from f
        os.remove(path)
        with progress_lock:
            progress_data.pop(download_id, None)

    response = StreamingHttpResponse(
        file_stream(filepath),
        content_type='application/octet-stream'
    )
    response['Content-Disposition'] = f'attachment; filename="{info["filename"]}"'
    return response
