_BUTTON_HEIGHT = 128
_BUTTON_WIDTH = 128
_BUTTON_OFFSET = 10

class Default:
    back_button = dict(image="themes/default/arrow-left.png",
                       over="themes/default/arrow-left.png",
                       down="themes/default/arrow-left-glow.png")
    @staticmethod
    def back_pos(width, height):
        return (_BUTTON_OFFSET,
                (height - _BUTTON_HEIGHT) / 2)

    forward_button = dict(image="themes/default/arrow-right.png",
                          over="themes/default/arrow-right.png",
                          down="themes/default/arrow-right-glow.png")
    @staticmethod
    def forward_pos(width, height):
        return (width - _BUTTON_WIDTH - _BUTTON_OFFSET,
                (height - _BUTTON_HEIGHT) / 2)

    unstarred_button = dict(image="themes/default/star-outline.png",
                            over="themes/default/star-outline.png",
                            down="themes/default/star-outline-glow.png")
    starred_button = dict(image="themes/default/star-fill.png",
                          over="themes/default/star-fill.png",
                          down="themes/default/star-fill-glow.png")
    @staticmethod
    def star_pos(width, height):
        return ((width - _BUTTON_WIDTH) / 2,
                _BUTTON_OFFSET)