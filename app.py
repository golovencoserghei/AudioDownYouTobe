import os
import yt_dlp
import ffmpeg
from flask import Flask, render_template, request, send_file, flash
from flask_bootstrap import Bootstrap

app = Flask(__name__)
app.secret_key = 'supersecretkey'
Bootstrap(app)

TEMP_DIR = 'temp_audio'

def download_audio(url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'outtmpl': f'{TEMP_DIR}/%(title)s.%(ext)s',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info_dict)
            return filename
    except Exception as e:
        return f'ERRaOR:{str(e)}'

def convert_audio(input_file, output_format='mp3'):
    output_file = input_file.rsplit('.', 1)[0] + f'.{output_format}'

    if not os.path.exists(input_file):
        return f'Ошибка: Файл {input_file} не найден.'

    try:
        ffmpeg.input(input_file).output(output_file, audio_bitrate='320k').run()
    except ffmpeg._run.Error as e:
        error_message = e.stderr.decode('utf-8') if e.stderr else 'Неизвестная ошибка'
        return f'Ошибка при конвертации: {error_message}'

    return output_file

def cleanup(files):
    try:
        for file in files:
            file_path = os.path.join(TEMP_DIR, file)
            print(f"Пытаемся удалить: {file_path}")
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Удалён файл: {file_path}")
            else:
                print(f"Файл не найден: {file_path}")
    except Exception as e:
        print(f'Ошибка при удалении файлов: {e}')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']

        if not url:
            flash('Введите ссылку на YouTube!', 'danger')
            return render_template('index.html')

        if not os.path.exists(TEMP_DIR):
            os.makedirs(TEMP_DIR)

        downloaded_file = download_audio(url)

        if downloaded_file is None:
            flash('Произошла ошибка при скачивании. Проверьте ссылку и попробуйте снова.', 'danger')
            return render_template('index.html')
        elif downloaded_file.startswith('ERRaOR:'):
            flash(f'Ошибка при скачивании: {downloaded_file}', 'danger')
            return render_template('index.html')

        output_file = convert_audio(downloaded_file, 'mp3')

        if output_file.startswith('Ошибка'):
            flash(output_file, 'danger')
            return render_template('index.html')

        try:
            response = send_file(output_file, as_attachment=True)

            @response.call_on_close
            def cleanup_files():
                cleanup([downloaded_file, output_file])

            return response

        except Exception as e:
            flash(f'Ошибка при отправке файла: {str(e)}', 'danger')

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
