from . import confused as _confused
from . import excited as _excited
from . import happy as _happy
from . import love as _love
from . import neutral as _neutral
from . import sad as _sad
from . import sleepy as _sleepy

GENERATED_FACES = {
    'confused': {'name': _confused.NAME, 'description': _confused.DESCRIPTION, 'frames': _confused.FRAMES, 'width': _confused.WIDTH, 'height': _confused.HEIGHT},
    'excited': {'name': _excited.NAME, 'description': _excited.DESCRIPTION, 'frames': _excited.FRAMES, 'width': _excited.WIDTH, 'height': _excited.HEIGHT},
    'happy': {'name': _happy.NAME, 'description': _happy.DESCRIPTION, 'frames': _happy.FRAMES, 'width': _happy.WIDTH, 'height': _happy.HEIGHT},
    'love': {'name': _love.NAME, 'description': _love.DESCRIPTION, 'frames': _love.FRAMES, 'width': _love.WIDTH, 'height': _love.HEIGHT},
    'neutral': {'name': _neutral.NAME, 'description': _neutral.DESCRIPTION, 'frames': _neutral.FRAMES, 'width': _neutral.WIDTH, 'height': _neutral.HEIGHT},
    'sad': {'name': _sad.NAME, 'description': _sad.DESCRIPTION, 'frames': _sad.FRAMES, 'width': _sad.WIDTH, 'height': _sad.HEIGHT},
    'sleepy': {'name': _sleepy.NAME, 'description': _sleepy.DESCRIPTION, 'frames': _sleepy.FRAMES, 'width': _sleepy.WIDTH, 'height': _sleepy.HEIGHT},
}
