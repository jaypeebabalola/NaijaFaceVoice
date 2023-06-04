from flask import Blueprint, render_template, request, flash, redirect, url_for, Flask, send_file, make_response
from .models import User, get_token, verify_token, Video
from werkzeug.security import generate_password_hash, check_password_hash
from . import db, mail 
from flask_login import login_user, login_required, logout_user, current_user
from flask_mail import Message
from pytube import YouTube
import os
import cv2
import numpy as np
import zipfile
import shutil
import moviepy.editor as mp 


app = Flask(__name__)
auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email') 
        password = request.form.get('password')

        user = User.query.filter_by(email = email).first()
        if user:
            if check_password_hash(user.password, password):
                flash('Logged in succesfully', category='success')
                login_user(user, remember=True)
                return redirect(url_for('views.home'))
            else:
                flash('Incorrect password, try again', category='error')
        else:
            flash('Email does not exist', category='error')

    return render_template("login.html", user=current_user)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('firstName')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')

        user = User.query.filter_by(email = email).first()
        if user:
            flash('Email already exists.', category='error')
        elif len(email) < 4:
            flash('Email must be greater than 3 characters.', category = 'error')
        elif len(first_name) < 2:
            flash('First Name must be greater than 1 character.', category = 'error')
        elif password1 != password2:
            flash('Passswords don\'t match.', category = 'error')
        elif len(password1) < 7:
            flash('Password must be at least 7 characters.', category = 'error')
        else:
            new_user = User(email=email, first_name=first_name, password=generate_password_hash(password1, method='sha256'))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user, remember=True)
            flash('Account Created', category='success')
            return redirect(url_for('views.home'))
            

    return render_template("sign_up.html", user=current_user)

def send_mail(user):
    token = get_token(user)
    reset_url = {url_for('reset_token', token=token, _external=True)}
    msg = Message('Password Reset Request', recipients=[user.email], sender='noreply@naijafacevoice.com')
    msg.body=f''' To reset your password. Please follow the link below
    
     {reset_url}

    If you didn't send a password reset request. Please ignore this message

    '''
    mail.send(msg)
    
@auth.route('/reset_password', methods=['GET', 'POST'])
def reset_request():
    if request.method == 'POST':
        
        email = request.form.get('email')  
        user = User.query.filter_by(email=email).first()
        user=current_user
        if user:
            send_mail(user)
            flash('Reset request sent, check your mail', category='success')
            return redirect(url_for('auth.login'))

    return render_template('reset_request.html', user=current_user)

@auth.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = verify_token(token)
    
    if user is None:
        flash('Invalid or expired token. Please try again.', category='warning')
        return redirect(url_for('auth.reset_request'))
    
    if request.method == 'POST':
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        
        if password1 != password2:
            flash('Passwords do not match. Please try again.', category='error')
        else:
            #Update the user's password
            user.set_password(password=generate_password_hash(password1, method='sha256'))
            #Commit the changes to the database
            db.session.commit()
            
            flash('Your password has been reset successfully!', category='success')
            return redirect(url_for('auth.login'))
    
    return render_template('change_password.html', token=token)

@auth.route('/process_url', methods=['GET', 'POST'])
@login_required
def process_url():
    save_directory="C:\\Users\\DELL\\Desktop\\web_app\\website\\static\\save_directory"
    try:
        url = str(request.form.get('link'))
        print(url)
        # Create a YouTube object
        video = YouTube(url)
        
        # Get the highest resolution stream
        stream = video.streams.get_highest_resolution()
        
        # Download the video
        video_filename = f"{video.title}.mp4"
        video_path = os.path.join(save_directory, video_filename)
        stream.download(output_path=save_directory)

        

        # Save video information to the database
        new_video = Video(url=url, title=video.title, save_directory=video_path)
        db.session.add(new_video)
        db.session.commit()
        
        print("Video information saved successfully.")

        # video_path=os.path.join(save_directory, filename=video.save_directory) 

        return send_file(save_directory, filename=video_filename, as_attachment=True)

        # show_video = send_file(new_video.save_directory, as_attachment=True, attachment_filename=video.title+".mp4")
    
        # Pass the newly added video to the template
        # return render_template('result.html',  videos=[new_video], user=current_user)
    
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        new_video = None
    
    videos = Video.query.all()
    # Retrieve the latest video from the database or any other source
    video = Video.query.order_by(Video.id.desc()).first()

    email = request.form.get('email')
    user = User.query.filter_by(email=email).first()

    # print(f"URL: {url}")
    # print(f"Video Title: {video.title}")
    # print(f"Save Directory: {new_video.save_directory}")

    
    return render_template('result.html', video=video, user=current_user)

@auth.route('/download/<path:filename>')
def download_video(filename):
    save_directory="C:\\Users\\DELL\\Desktop\\web_app\\website\\static\\save_directory"
    video_path=os.path.join(save_directory, filename) 
    print(filename)
    print(video_path)
    response = make_response(send_file(video_path))
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response

@auth.route('/extract_biometrics', methods=['GET', 'POST'])
@login_required
def extract_biometric():
    save_directory="C:\\Users\\DELL\\Desktop\\web_app\\website\\static\\save_directory"
    biometrics_directory = os.path.join(save_directory, "biometrics")
    # Define the path to the video 
    latest_video = Video.query.order_by(Video.id.desc()).first()
    video_path = latest_video.save_directory

    loading = True

    # Load the video from the file
    video = cv2.VideoCapture(video_path)
    frame_rate = video.get(cv2.CAP_PROP_FPS)
    print(frame_rate)
    frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    print(frame_count)
    if frame_rate!=0:
        video_duration = frame_count / frame_rate
    else:
        video_duration=0

    # Release the video capture object
    video.release()

    # Load the video again using MoviePy for audio extraction
    print(video_path)
    audio = mp.AudioFileClip(video_path)

    # Define the cascade classifier for face detection
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

    # Create a folder for saving the frames and voices
    output_directory_faces = os.path.join(biometrics_directory, 'face_frames')
    output_directory_voices = os.path.join(biometrics_directory, 'voice_segments')
    os.makedirs(output_directory_faces, exist_ok=True)
    os.makedirs(output_directory_voices, exist_ok=True)

    # Extract frames and voices from the video
    face_dataset = []
    voice_dataset = []

    # Enter the time ranges (in seconds) for face and voice segments
    time_ranges = [
        (0, video_duration),  # Extract the whole video duration for both face and voice
    ]

    for i, (start_time, end_time) in enumerate(time_ranges):
        # Extract face frames
        video = cv2.VideoCapture(video_path)
        for frame_num in range(int(start_time * frame_rate), int(end_time * frame_rate)):
            video.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = video.read()

            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Detect faces in the frame
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5, minSize=(64, 64))

            for (x, y, w, h) in faces:
                roi = frame[y:y+h, x:x+w]

                # Detect eyes in the face region
                eyes = eye_cascade.detectMultiScale(roi)

                # Save the face frame if eyes are detected
                if len(eyes) > 0:
                    face_dataset.append(roi)

                    # Save the face frame
                    filename = os.path.join(output_directory_faces, f'face_{len(face_dataset)}.jpg')
                    cv2.imwrite(filename, roi)

        video.release()

        # Extract voice segments
        voice_segment = audio.subclip(start_time, end_time)
        voice_filename = os.path.join(output_directory_voices, f'voice_{i+1}.wav')
        voice_segment.write_audiofile(voice_filename)

    # Create a zip file to store the face frames
    zip_filename_faces = os.path.join(biometrics_directory, 'face_frames.zip')
    with zipfile.ZipFile(zip_filename_faces, 'w') as zip_file_faces:
        # Write each face frame to the zip file
        for i, face in enumerate(face_dataset):
            filename = os.path.join(output_directory_faces, f'face_{i+1}.jpg')
            zip_file_faces.write(filename, arcname=os.path.basename(filename))

    # Create a zip file to store the voice segments
    zip_filename_voices = os.path.join(biometrics_directory, 'voice_segments.zip')
    with zipfile.ZipFile(zip_filename_voices, 'w') as zip_file_voices:
        # Write each voice segment to the zip file
        for i in range(len(time_ranges)):
            filename = os.path.join(output_directory_voices, f'voice_{i+1}.wav')
            zip_file_voices.write(filename, arcname=os.path.basename(filename))

    shutil.rmtree(output_directory_faces)
    shutil.rmtree(output_directory_voices)

    loading = False

    return render_template('biometric_result.html', loading=loading, face_biometrics=face_dataset, voice_biometrics=voice_dataset, face_zip=zip_filename_faces, voice_zip=zip_filename_voices, user=current_user, video=video)

@auth.route('/download_face_biometric/<path:filename>')
@login_required
def download_face_biometric(filename):
    biometric_directory="C:\\Users\\DELL\\Desktop\\web_app\\website\\static\\save_directory\\biometrics"
    face_path = os.path.join(biometric_directory, filename)
    print(face_path)
    response = make_response(send_file(face_path))
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response

@auth.route('/download_voice_biometric/<path:filename>')
@login_required
def download_voice_biometric(filename):
    biometric_directory="C:\\Users\\DELL\\Desktop\\web_app\\website\\static\\save_directory\\biometrics"
    voice_path = os.path.join(biometric_directory, filename)
    print(voice_path)
    response = make_response(send_file(voice_path))
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
    


app.register_blueprint(auth)
