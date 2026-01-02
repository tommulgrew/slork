from flask import Flask, render_template, request
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from .app import App
from .args import parse_main_args
from .engine import ActionResult

@dataclass
class WebAppState:
    image_url: Optional[str] = None

def main() -> None:

    # Parse arguments
    args = parse_main_args()

    # Create application
    app = App(args)

    # Create web application
    web_app = create_web_app(app, WebAppState())
    web_app.run(debug=True)

def create_web_app(app: App, state: WebAppState) -> Flask:
    
    BASE_DIR = Path(__file__).resolve().parents[2]
    ASSETS_DIR = BASE_DIR / "assets"

    web_app = Flask(
        __name__,
        static_folder=str(ASSETS_DIR),
        static_url_path="/assets"
    )

    @web_app.route("/", methods=["GET", "POST"])
    def index():
        # Perform command or display current location info
        engine_response: ActionResult
        if request.method == "POST":
            engine_response = app.engine.handle_raw_command(request.form["command"])
        else:
            engine_response = app.engine.describe_current_location()
        
        # Lookup image
        if engine_response.image_ref:
            image_path = app.get_image(engine_response.image_ref)
            state.image_url = fix_image_path(image_path)

        return render_template(
            "index.html",
            title=app.world.world.title,
            text=engine_response.message,
            image=state.image_url
        )

    return web_app

def fix_image_path(path: Optional[Path]) -> Optional[str]:
    if not path:
        return None
    
    s = str(path).replace("\\", "/")

    return s    

if __name__ == "__main__":
    main()
