from os import environ, path
import secrets, os
from PIL import Image
from flask import current_app, jsonify
from flask_login import current_user

from werkzeug.utils import secure_filename
from PIL import Image, UnidentifiedImageError
from flask import current_app, flash

regex = "([^\\s]+(\\.(?i)(jpe?g|png|gif|bmp))$)"

#as alternative to FileAllowed() I can also use this allowed_file()
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in environ.get('ALLOWED_EXTENSIONS')

def save_photo(form_file):
    try:
        if form_file:
            random_hex = secrets.token_hex(2)
            _, f_ext = path.splitext(form_file.filename) if form_file.filename else current_user.photo
            #fname = secure_filename(_ + random_hex + f_ext).lower()
            fname = secure_filename(current_user.username + '_'+ _ + random_hex + f_ext).lower() #->username+'underscore(_)+origial-file-name+file-extension
            photo_path = path.join(current_app.root_path,'static/images/user', fname)
            size = (320, 320)
            i = Image.open(form_file)
            i.thumbnail(size)
            i.save(photo_path)
            return fname
        pass
    except UnidentifiedImageError:
        return flash(f'Invalid File Type {form_file} ')


# def save_file(form_file, upload_path='uploads', username=None):
#     try:
#         if not form_file:
#             raise ValueError('No file provided')
        
#         # Generate a random hex and secure filename
#         random_hex = secrets.token_hex(8)
#         filename, file_extension = os.path.splitext(form_file.filename)
#         if username:
#             secure_name = secure_filename(f"{username}_{filename}_{random_hex}{file_extension}").lower()
#         else:
#             secure_name = secure_filename(f"{filename}_{random_hex}{file_extension}").lower()

#         # Define the file path dynamically
#         if not os.path.isabs(upload_path):
#             upload_path = os.path.join(current_app.root_path, upload_path)
#         os.makedirs(upload_path, exist_ok=True)
#         file_path = os.path.join(upload_path, secure_name)

#         # Handle different file types
#         if file_extension.lower() in ['.png', '.jpg', '.jpeg']:
#             size = (320, 320)
#             image = Image.open(form_file)
#             image.thumbnail(size)
#             image.save(file_path)
#         else:
#             form_file.save(file_path)

#         return secure_name

#     except UnidentifiedImageError:
#         # flash(f'Invalid Image File Type: {form_file.filename}')
#         return jsonify({"success":False, "error":f"Invalid Image File Type: {form_file.filename}"})
#     except ValueError as ve:
#         # flash(str(ve))
#         return jsonify({"success":False, "error": {str(ve)} })
#     except Exception as e:
#         return jsonify({"success":False, "error": {str(e)} })



from flask import url_for

def save_file(form_file, upload_path='uploads', username=None, return_url=True):
    try:
        if not form_file:
            raise ValueError('No file provided')
        
        random_hex = secrets.token_hex(8)
        filename, file_extension = os.path.splitext(form_file.filename)

        if username:
            secure_name = secure_filename(
                f"{username}_{filename}_{random_hex}{file_extension}"
            ).lower()
        else:
            secure_name = secure_filename(
                f"{filename}_{random_hex}{file_extension}"
            ).lower()

        # Ensure path is inside /static
        if not upload_path.startswith('static'):
            upload_path = os.path.join('static', upload_path)

        abs_upload_path = os.path.join(current_app.root_path, upload_path)
        os.makedirs(abs_upload_path, exist_ok=True)

        file_path = os.path.join(abs_upload_path, secure_name)

        # Save image or file
        if file_extension.lower() in ['.png', '.jpg', '.jpeg']:
            image = Image.open(form_file)
            image.thumbnail((320, 320))
            image.save(file_path)
        else:
            form_file.save(file_path)

        # RETURN FULL URL
        if return_url:
            return url_for(
                'static',
                filename=f"{upload_path.replace('static/', '')}/{secure_name}",
                _external=True  # VERY IMPORTANT → makes it full URL
            )

        return secure_name

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/utils/save_image.py: {e}")
        return jsonify({"success": False, "error": str(e)})

# Example usage
# save_file(form_file)
# save_file(form_file, 'custom_path')
# save_file(form_file, 'custom_path', current_user.username)

