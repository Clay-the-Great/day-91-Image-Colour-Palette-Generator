from flask import Flask, flash, request, redirect, url_for, render_template
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import matplotlib.patches as patches
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import pandas as pd
from PIL import Image
import cv2
import extcolors
from colormap import rgb2hex
from werkzeug.utils import secure_filename
import os
from datetime import datetime

UPLOAD_FOLDER = 'static/uploads/'
app = Flask(__name__)
app.secret_key = "secret key"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 4096 * 4096
matplotlib.use('Agg')
ALLOWED_EXTENSIONS = ['png', 'jpg', 'jpeg', 'gif']


@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_color(img_url, output_width=900, tolerance=10, limit=10, zoom=2.7):
    # resize the image
    image = Image.open(img_url)
    if image.size[0] >= output_width:
        compression_rate = output_width / float(image.size[0])
        output_height = int(float(image.size[1]) * float(compression_rate))
        resized_image = image.resize((output_width, output_height), Image.ANTIALIAS)
        resized_url = img_url.rsplit(".", 1)[0] + "_resized." + img_url.rsplit(".", 1)[1]
        resized_image.save(resized_url)
    else:
        resized_url = img_url

    # extract colors in RGB code
    colors = extcolors.extract_from_path(resized_url, tolerance=tolerance, limit=limit)
    rgb_list = [color[0] for color in colors[0]]
    occurrences = [color[1] for color in colors[0]]
    hex_list = [rgb2hex(rgb[0], rgb[1], rgb[2]) for rgb in rgb_list]
    df_hex = pd.DataFrame(zip(hex_list, occurrences), columns=["color", "occurrence"])

    # background
    fig, ax = plt.subplots(figsize=(192, 108), dpi=10)
    fig.set_facecolor('white')
    plt.savefig('static/output_charts/background.png')
    plt.close(fig)
    # the figure
    figure, (axis1, axis2) = plt.subplots(1, 2, figsize=(160, 120), dpi=10)

    # donut chart
    labels = [color + " " + str(round(occurrence * 100 / sum(occurrences), 1)) + "%"
              for color, occurrence in zip(hex_list, occurrences)]
    wedges, text = axis1.pie(occurrences, labels=labels, labeldistance=1.05, colors=hex_list,
                             textprops={'fontsize': 120, 'color': 'black'})
    plt.setp(wedges, width=0.3)
    axis1.set_aspect("equal")
    thumb_nail = plt.imread(resized_url)
    image_box = OffsetImage(thumb_nail, zoom=zoom)
    album = AnnotationBbox(image_box, (0, 0))
    axis1.add_artist(album)

    # create color palette
    x_origin = 160
    y_origin_1 = 110
    y_origin_2 = 110
    for color, label in zip(hex_list, labels):
        if hex_list.index(color) < 5:
            patch = patches.Rectangle((x_origin, y_origin_1), 360, 160, facecolor=color)
            axis2.add_patch(patch)
            axis2.text(x=x_origin + 400, y=y_origin_1 + 100, s=label, fontdict={'fontsize': 120})
            y_origin_1 += 180
        else:
            patch = patches.Rectangle((x_origin + 1000, y_origin_2), 360, 160, facecolor=color)
            axis2.add_patch(patch)
            axis2.text(x=x_origin + 1400, y=y_origin_2 + 100, s=label, fontdict={'fontsize': 120})
            y_origin_2 += 180
    background = plt.imread('static/output_charts/background.png')
    plt.imshow(background)
    plt.tight_layout()
    axis2.axis('off')
    # plt.show()
    output_path = "static/output_charts/" + "color_extraction_" + resized_url.rsplit("/", 1)[1]
    plt.savefig(output_path)
    return output_path


print(extract_color("static/uploads/comic.jpg"))


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        if 'file' not in request.files:
            flash('No file part')
            return redirect(url_for("home"))
        file = request.files['file']
        if file.filename == "":
            flash("No image selected for uploading")
            return redirect(url_for("home"))
        if file and allowed_file(file.filename):
            file_name = secure_filename(file.filename)
            if request.form["color_number"]:
                color_number = int(request.form["color_number"])
            else:
                color_number = 10
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], file_name))
            # flash('Image successfully uploaded and displayed below')
            output_path = extract_color(img_url="static/uploads/" + file_name, limit=color_number)
            return render_template("index.html", file_name=file_name, output_path=output_path)
        else:
            flash("Allowed image formats are: png, jpg, jpeg and gif")
            return redirect(url_for("home"))
    return render_template("index.html")


if __name__ == "__main__":
    app.run()
