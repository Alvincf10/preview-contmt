"""Render every page of the built HMI, so the result can be compared with the design."""

import nextion_tools.hmi as H

_orig = H.decode


def _decode(name, raw):
    try:
        return _orig(name, raw)
    except UnicodeDecodeError:
        return raw.split(b"\0")[0].decode("latin1")


H.decode = _decode

from nextion_tools.hmi import Project  # noqa: E402
from nextion_tools.render import Renderer, save_png  # noqa: E402

project = Project.load(r"d:\coding\preview-contmt\nextion\conmt.HMI")
renderer = Renderer(project)
out = r"C:\Users\Alvin\AppData\Local\Temp\pages"
import os  # noqa: E402

os.makedirs(out, exist_ok=True)
for page in project.pages:
    image = renderer.render(page.name)
    path = os.path.join(out, f"{page.id:02d}_{page.name}.png")
    save_png(image, path)
    print(page.name, image.size)
print("done", out)
