from rest_framework.renderers import BaseRenderer


class BinaryFileRenderer(BaseRenderer):
    """
    Return binary file for download.
    """
    media_type = 'application/octet-stream'
    format = ''
    charset = None
    render_style = 'binary'

    def render(self, data, media_type=None, renderer_context=None):
        return data
