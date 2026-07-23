from django.apps import AppConfig


class BcseAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bcse_app'

    def ready(self):
        from django.contrib.auth.models import User
        from simple_history import register

        register(
            User,
            app = 'bcse_app',
            excluded_fields=[
                "password",
                "last_login",
                "is_superuser",
                "username",
                "is_staff",
                "date_joined",
                "groups",
                "user_permissions",
            ]
        )
