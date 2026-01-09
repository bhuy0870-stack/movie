from django.apps import AppConfig

class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'

    def ready(self):
        # Dòng này là "công tắc" kích hoạt tặng huy hiệu
        import main.signals