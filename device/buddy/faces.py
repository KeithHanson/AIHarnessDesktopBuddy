from buddy.generated_faces import GENERATED_FACES


def list_faces():
    return [
        {
            "name": name,
            "description": meta["description"],
        }
        for name, meta in sorted(GENERATED_FACES.items())
    ]


def is_generated_face(name):
    return name in GENERATED_FACES


def get_generated_frames(name):
    return GENERATED_FACES[name]["frames"]


def draw_face(display, name):
    if name not in GENERATED_FACES:
        raise ValueError("unknown face: %s" % name)
    display.render_buffer(GENERATED_FACES[name]["frames"][0])
