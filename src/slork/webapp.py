from flask import Flask, render_template
from .app import App
from .args import parse_main_args

def main() -> None:

    # Parse arguments
    args = parse_main_args()

    # Create application
    app = App(args)

    # Create web application
    web_app = create_web_app(app)
    web_app.run(debug=True)

def create_web_app(app: App) -> Flask:
    
    web_app = Flask(__name__)

    @web_app.route("/", methods=["GET", "POST"])
    def index():
        engine_response = app.engine.describe_current_location()
        return render_template(
            "index.html",
            text=engine_response.message,
            image=app.get_image(engine_response.image_ref)
        )

    return web_app