# Face template

Use `face_strip_template.svg` as an 8-frame horizontal strip template.

Specs:
- overall size: `1024x64`
- 8 frames
- each frame: `128x64`
- black background recommended
- draw face elements in white/grayscale

Workflow:
1. Edit `templates/face_strip_template.svg` in a vector editor, or export it and paint over it.
2. Keep each frame inside its `128x64` cell.
3. Export as PNG if needed.
4. Preview it:
   ```bash
   python scripts/preview_face_animation.py templates/your_face.png --mode strip --name your-face --open
   ```
5. Generate the device face:
   ```bash
   python scripts/make_face_animation.py templates/your_face.png --mode strip --name your_face --description "Describe when to use it."
   ```
6. Deploy:
   ```bash
   ./scripts/deploy.sh /dev/ttyACM0
   ```
