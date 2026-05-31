from rest_framework.renderers import JSONRenderer


class EnvelopeJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get('response') if renderer_context else None
        if response is None:
            return super().render(data, accepted_media_type, renderer_context)

        if isinstance(data, dict) and data.get('success') is False:
            return super().render(data, accepted_media_type, renderer_context)

        if response.status_code == 204:
            return super().render(data, accepted_media_type, renderer_context)

        if isinstance(data, dict) and 'success' in data:
            return super().render(data, accepted_media_type, renderer_context)

        if isinstance(data, dict) and 'data' in data and 'meta' in data:
            envelope = {'success': True, 'data': data['data'], 'meta': data['meta']}
            return super().render(envelope, accepted_media_type, renderer_context)

        envelope = {'success': True, 'data': data}
        return super().render(envelope, accepted_media_type, renderer_context)
