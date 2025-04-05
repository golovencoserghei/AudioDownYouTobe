import os
import yt_dlp
import ffmpeg
from flask import Flask, render_template, request, send_file, flash
from flask_bootstrap import Bootstrap
import uuid

app = Flask(__name__)
app.secret_key = 'supersecretkey'
Bootstrap(app)

# Абсолютный путь к папке временных файлов
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TEMP_DIR = os.path.join(BASE_DIR, 'temp_audio')

# Создание временной папки при старте
os.makedirs(TEMP_DIR, exist_ok=True)

# Функция для скачивания аудио с YouTube
def download_audio(url):
    filename_uuid = str(uuid.uuid4())  # Уникальное имя файла
    outtmpl = os.path.join(TEMP_DIR, f'{filename_uuid}.%(ext)s')

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': outtmpl,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            downloaded_path = ydl.prepare_filename(info_dict)
            return downloaded_path
    except Exception as e:
        return f'Ошибка при скачивании: {str(e)}'

# Конвертация в MP3 с максимальным битрейтом
def convert_audio(input_file, output_format='mp3'):
    output_file = os.path.splitext(input_file)[0] + f'.{output_format}'

    if not os.path.exists(input_file):
        return f'Ошибка: Файл {input_file} не найден.'

    try:
        ffmpeg.input(input_file).output(output_file, audio_bitrate='320k').run(overwrite_output=True)
    except ffmpeg._run.Error as e:
        error_message = e.stderr.decode('utf-8') if e.stderr else 'Неизвестная ошибка'
        return f'Ошибка при конвертации: {error_message}'

    return output_file

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']

        if not url:
            flash('Введите ссылку на YouTube!', 'danger')
            return render_template('index.html')

        downloaded_file = download_audio(url)

        if downloaded_file is None or downloaded_file.startswith('Ошибка'):
            flash(downloaded_file, 'danger')
            return render_template('index.html')

        output_file = convert_audio(downloaded_file, 'mp3')

        if output_file.startswith('Ошибка'):
            flash(output_file, 'danger')
            return render_template('index.html')

        # Отправка файла пользователю
        try:
            response = send_file(output_file, as_attachment=True)

            @response.call_on_close
            def cleanup():
                try:
                    if os.path.exists(downloaded_file):
                        os.remove(downloaded_file)
                    if os.path.exists(output_file):
                        os.remove(output_file)
                except Exception as e:
                    print(f'Ошибка при удалении файлов: {e}')

            return response

        except Exception as e:
            flash(f'Ошибка при отправке файла: {str(e)}', 'danger')

    return render_template('index.html')
