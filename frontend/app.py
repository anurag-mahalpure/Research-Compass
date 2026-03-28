from flask import Flask, render_template
import os

app = Flask(__name__)

# Basic route to serve the single page application
@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    # Run the Flask app on port 5000
    app.run(host="0.0.0.0", port=5000, debug=True)
