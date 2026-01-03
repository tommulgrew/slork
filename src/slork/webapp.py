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
    last_cmd: Optional[str] = None

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
            state.last_cmd = request.form["command"]
            print(f"(Http POST > {state.last_cmd})")

            app.base_engine.last_command = None
            engine_response = app.handle_raw_command(state.last_cmd)
        else:
            print("(Http GET)")
            engine_response = app.engine.get_intro()
        
        # Lookup image
        if engine_response.image_ref:
            image_path = app.get_image(engine_response.image_ref)
            state.image_url = fix_image_path(image_path)

        # Show last command
        # Use command passed to base engine, if available. Otherwise use command as keyed.
        text = engine_response.message
        last_cmd = app.base_engine.last_command.raw if app.base_engine.last_command else state.last_cmd
        if last_cmd:
            text = f"> {last_cmd}\n\n{text}"

        return render_template(
            "index.html",
            title=app.world.world.title,
            text=text,
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
