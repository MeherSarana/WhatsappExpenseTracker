from fastapi.staticfiles import StaticFiles

def add_static(app):
    # serve files from the ./static folder
    app.mount("/static", StaticFiles(directory="static"), name="static")
